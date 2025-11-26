# ==============================
# BDD JSON Validator Router
# ==============================
"""
BDD JSON Validator API
Validates BDD-style JSON test case files for sequence, structure, format, and test data completeness.
Uses Azure OpenAI for intelligent validation suggestions.
"""
from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from fastapi.responses import JSONResponse, FileResponse
import os
import re
import json
import requests
import tempfile
from typing import Dict, List

import config
from .users import get_current_any_user
import utils
from azure_openai_client import call_openai_api

router = APIRouter()

# ==============================
# Azure OpenAI Helper Function
# ==============================
def call_gemini(prompt: str) -> str:
    """
    Sends a prompt to Azure OpenAI model and returns text response.
    """
    try:
        response = call_openai_api(
            prompt=prompt,
            max_tokens=500,
            system_message="You are a QA automation expert. Provide concise, practical suggestions."
        )
        return response
    except Exception as e:
        utils.logger.error(f"[Azure OpenAI Exception] {e}")
    return ""


# ==============================
# Helper Functions
# ==============================
def is_input_step(step_text: str) -> bool:
    """
    Identifies whether a step likely requires input/test data.
    """
    keywords = ["enter", "input", "type", "fill", "select", "provide", "choose", "upload"]
    return any(k in step_text.lower() for k in keywords)


# ==============================
# Validation Rules
# ==============================
def rule_step_sequence(scenario, issues):
    """Ensure step indexes are sequential (1,2,3,...)."""
    steps = scenario.get("Steps", [])
    prev = 0
    for step in steps:
        idx = step.get("Index")
        if idx != prev + 1:
            issues["errors"].append(f"Step index {idx} is not sequential (expected {prev + 1}).")
        prev = idx


def rule_blank_steps(scenario, issues):
    """Ensure each step with an index has text content."""
    for step in scenario.get("Steps", []):
        if step.get("Index") and not step.get("Step"):
            issues["errors"].append(f"Step {step['Index']} has index but no text.")


def rule_prefix_validation(scenario, issues):
    """Validate that each step starts with Given/When/Then/And."""
    for step in scenario.get("Steps", []):
        text = step.get("Step", "")
        s_no = step.get("Index")
        if text and not re.match(r"^(Given|When|Then|And)\b", text, re.IGNORECASE):
            issues["errors"].append(f"Step {s_no} must start with Given/When/Then/And → '{text}'.")


def rule_missing_input_data(scenario, issues):
    """Identify input-related steps missing test data and use Azure OpenAI to suggest data."""
    for step in scenario.get("Steps", []):
        s_text = step.get("Step", "")
        s_no = step.get("Index")
        t_data = step.get("TestData", {})
        if is_input_step(s_text) and not t_data:
            suggestion = call_gemini(f"Suggest key:value test data for this step: {s_text}")
            issues["errors"].append(
                f"Step {s_no} has input action but missing TestData. Suggestion: {suggestion}"
            )


def rule_id_format(scenario, issues):
    """Validate that ScenarioId follows PREFIX-001 format."""
    sid = scenario.get("ScenarioId", "")
    pattern = re.compile(r"^[A-Z-]+-\d{3,}$")
    if not pattern.match(sid):
        issues["errors"].append(f"Invalid ScenarioId format '{sid}' (expected PREFIX-001).")


def rule_prerequisite_check(all_ids, scenario, issues):
    """Ensure all prerequisite ScenarioIds exist."""
    prereqs = scenario.get("Prerequisites", [])
    for pre in prereqs:
        pid = pre.get("PrerequisiteID", "")
        if pid and pid not in all_ids:
            issues["warnings"].append(f"Prerequisite '{pid}' not found in Scenarios list.")


def rule_duplicate_titles(all_titles, scenario, issues):
    """Detect scenarios with duplicate names."""
    name = scenario.get("Name", "").strip()
    all_titles.setdefault(name, []).append(scenario.get("ScenarioId", ""))


# ==============================
# Core Validation Logic
# ==============================
def run_validations(data: Dict) -> Dict:
    """
    Executes all validation rules and returns structured results.
    """
    scenarios = data.get("Scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("Invalid JSON format — 'Scenarios' should be a list.")

    all_ids = [s.get("ScenarioId") for s in scenarios if isinstance(s, dict)]
    all_titles = {}
    results = {}

    # Pass 1: collect duplicates
    for sc in scenarios:
        if isinstance(sc, dict):
            rule_duplicate_titles(all_titles, sc, {"errors": [], "warnings": []})

    # Pass 2: run validations per scenario
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        sid = sc.get("ScenarioId", "UNKNOWN_ID")
        results[sid] = {"errors": [], "warnings": []}

        rule_id_format(sc, results[sid])
        rule_step_sequence(sc, results[sid])
        rule_blank_steps(sc, results[sid])
        rule_prefix_validation(sc, results[sid])
        rule_missing_input_data(sc, results[sid])
        rule_prerequisite_check(all_ids, sc, results[sid])

    # Mark duplicates
    for title, ids in all_titles.items():
        if len(ids) > 1:
            msg = f"Duplicate scenario name '{title}' in: {', '.join(ids)}"
            for sid in ids:
                if sid in results:
                    results[sid]["warnings"].append(msg)

    return results


# ==============================
# API Endpoints
# ==============================

@router.post("/bdd/validate")
async def validate_bdd_json(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_any_user)
):
    """
    Validates a BDD-style JSON test case file.
    Returns validation results with errors and warnings.
    """
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File read error: {str(e)}")

    try:
        results = run_validations(data)
        return JSONResponse({
            "status": "completed",
            "results": results,
            "file_name": file.filename
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        utils.logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/bdd/validate-and-download")
async def validate_and_download_bdd(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_any_user)
):
    """
    Validates BDD JSON and returns results as a downloadable file.
    """
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File read error: {str(e)}")

    try:
        results = run_validations(data)
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            json.dump(results, temp_file, indent=2)
            temp_path = temp_file.name
        
        return FileResponse(
            temp_path,
            filename=f"validation_result_{file.filename.replace('.json', '')}.json",
            media_type="application/json"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        utils.logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/bdd/status")
async def bdd_validator_status(current_user: dict = Depends(get_current_any_user)):
    """
    Returns the status of the BDD validator service.
    """
    return {
        "status": "operational",
        "service": "BDD JSON Validator",
        "version": "1.0.0",
        "validations": [
            "step_sequence",
            "blank_steps",
            "prefix_validation",
            "missing_input_data",
            "id_format",
            "prerequisite_check",
            "duplicate_titles"
        ]
    }
