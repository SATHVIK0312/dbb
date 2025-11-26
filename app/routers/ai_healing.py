from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, Response

import base64
import json
import subprocess
import tempfile
import os
import uuid
from datetime import datetime

from azure_openai_client import call_openai_api, call_openai_with_images


router = APIRouter()


@router.post("/self-heal")
async def self_heal(
    testplan_output: str = Form(...),
    generated_script: str = Form(...),
    execution_logs: str = Form(...),
    screenshot: UploadFile = File(None),
    dom_snapshot: UploadFile = File(None)
):
    """
    Self-heals a failing test script using Azure OpenAI API.
    Returns the corrected Python script as plain text.
    """
    try:
        screenshot_b64 = None
        if screenshot:
            screenshot_bytes = await screenshot.read()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        dom_html = None
        if dom_snapshot:
            dom_html = (await dom_snapshot.read()).decode("utf-8")

        prompt = f"""
You are an expert test automation engineer.
Self-heal the failing script using all the provided data.

============================================================
TEST PLAN (BDD)
{testplan_output}
============================================================

============================================================
ORIGINAL GENERATED SCRIPT
{generated_script}
============================================================

============================================================
EXECUTION LOGS (THE FAILURE)
{execution_logs}
============================================================

============================================================
DOM SNAPSHOT
{dom_html if dom_html else "No DOM snapshot provided"}
============================================================

============================================================
SCREENSHOT
{"Provided" if screenshot_b64 else "No screenshot provided"}
============================================================

RULES:
1. Identify the root cause of failure.
2. Fix incorrect selectors / waits / navigation / logic.
3. Maintain SAME LOG FORMAT:
- "Running action:"
- "Action runned:"
- "failed due to:"
4. Follow all BDD steps from the test plan.
5. Output ONLY the corrected final Python script.
6. NO markdown, NO code fences, ONLY raw Python code.
"""

        if screenshot_b64:
            healed_code = call_openai_with_images(
                prompt=prompt,
                image_b64=screenshot_b64,
                max_tokens=4000,
                system_message="You are an expert test automation engineer. Return only valid Python code."
            )
        else:
            healed_code = call_openai_api(
                prompt=prompt,
                max_tokens=4000,
                system_message="You are an expert test automation engineer. Return only valid Python code."
            )

        cleaned = (
            healed_code
            .replace("```python", "")
            .replace("```", "")
            .strip()
        )

        return Response(
            content=cleaned,
            media_type="text/plain"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Self-heal failed: {str(e)}"
        )


@router.post("/ai-execution")
async def ai_execution(
    testcase_id: str = Form(...),
    script_type: str = Form(...),
    script_lang: str = Form(...),
    testplan_output: str = Form(...)
):
    """
    1. Generates a test script from Azure OpenAI
    2. Executes it locally
    3. Returns formatted output with test plan, script, logs, and status
    """
    try:
        if script_type.lower() not in ["playwright", "selenium"]:
            raise HTTPException(status_code=400, detail="Invalid script_type. Use 'playwright' or 'selenium'.")
        if script_lang.lower() != "python":
            raise HTTPException(status_code=400, detail="Only Python scripts are supported.")

        prompt = f"""
        Generate a FULLY EXECUTABLE Python test script for the test case {testcase_id}.
        Follow this TEST PLAN (JSON):
        {testplan_output}

        FRAMEWORK: {script_type.lower()} (use sync playwright if playwright, selenium if selenium)

        REQUIRED LOGGING FORMAT (for every step):
        - Before step:  print("Running action: <STEP> at <timestamp>")
        - After step:   print("Action runned: <STEP> at <timestamp>")
        - On failure:   print("Action <STEP> failed at <timestamp> due to: <error>")

        FAILURE CAPTURE:
        - Screenshot: save as 'error_screenshot.png'
        - DOM dump: save as 'page_dom_dump.txt'
        - Then re-raise the exception

        PLAYWRIGHT RULES:
        - from playwright.sync_api import sync_playwright
        - Use headless=True
        - page.screenshot(path="error_screenshot.png")
        - with open("page_dom_dump.txt","w",encoding="utf-8") as f: f.write(page.content())

        SELENIUM RULES:
        - from selenium import webdriver
        - driver.save_screenshot("error_screenshot.png")
        - with open("page_dom_dump.txt","w",encoding="utf-8") as f: f.write(driver.page_source)

        GENERAL RULES:
        - Implement get_timestamp()
        - Wrap EVERY step in try/except
        - End with: if __name__ == "__main__": run_test_{testcase_id.lower()}
        - Output ONLY raw Python code
        """

        script = call_openai_api(
            prompt=prompt,
            max_tokens=4000,
            system_message="You are a test automation expert. Generate only executable Python code with no markdown or explanations."
        )

        if not script:
            raise HTTPException(status_code=500, detail="Azure OpenAI returned empty script.")

        temp_path = f"temp_{uuid.uuid4().hex}.py"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(script)

        os.makedirs("artifacts", exist_ok=True)
        logs, status = [], "PASSED"

        def now(): 
            return datetime.now().strftime("%H:%M:%S")

        process = subprocess.Popen(
            ["python", temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ""):
            if line:
                logs.append(f"[{now()}] {line.strip()}")

        for line in iter(process.stderr.readline, ""):
            if line:
                logs.append(f"[{now()}] ERROR: {line.strip()}")

        process.wait()

        if process.returncode != 0:
            status = "FAILED"

        ss_log, dom_log = "", ""
        if os.path.exists("error_screenshot.png"):
            ss_path = f"artifacts/screenshot_{uuid.uuid4().hex}.png"
            os.replace("error_screenshot.png", ss_path)
            ss_log = f"Screenshot saved at {ss_path}"

        if os.path.exists("page_dom_dump.txt"):
            dom_path = f"artifacts/dom_{uuid.uuid4().hex}.html"
            os.replace("page_dom_dump.txt", dom_path)
            dom_log = f"DOM snapshot saved at {dom_path}"

        if ss_log: logs.append(ss_log)
        if dom_log: logs.append(dom_log)

        # Clean up
        os.unlink(temp_path)

        output = (
            "================ TEST PLAN ================\n"
            f"{testplan_output}\n\n"
            "================ GENERATED SCRIPT ================\n"
            f"{script}\n\n"
            "================ EXECUTION LOGS ================\n"
            + "\n".join(logs) +
            f"\n\n================ STATUS ================\n{status}\n"
        )

        return PlainTextResponse(content=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Execution failed: {e}")


@router.post("/self-healing-execution")
async def self_healing_execution(
    testplan_output: str = Form(...),
    generated_script: str = Form(...),
    execution_logs: str = Form(...),
    screenshot: UploadFile = File(None),
    dom_snapshot: UploadFile = File(None)
):
    """
    1. Self-heals the failed code
    2. Executes the healed code
    3. Returns formatted output with plan, script, logs, and status
    """
    try:
        screenshot_b64 = None
        if screenshot:
            screenshot_b64 = base64.b64encode(await screenshot.read()).decode("utf-8")

        dom_html = None
        if dom_snapshot:
            dom_html = (await dom_snapshot.read()).decode("utf-8")

        prompt = f"""
        You are an expert test automation engineer.
        Self-heal the failing script using all the provided data.

        TEST PLAN:
        {testplan_output}

        ORIGINAL SCRIPT:
        {generated_script}

        EXECUTION LOGS:
        {execution_logs}

        DOM SNAPSHOT:
        {dom_html or 'No DOM snapshot provided'}

        SCREENSHOT:
        {'Provided' if screenshot_b64 else 'No screenshot provided'}

        RULES:
        1. Fix incorrect selectors / waits / logic
        2. Maintain same log format
        3. Output only raw Python code (no markdown)
        """

        if screenshot_b64:
            healed_code = call_openai_with_images(
                prompt=prompt,
                image_b64=screenshot_b64,
                max_tokens=4000,
                system_message="You are an expert test automation engineer. Return only valid Python code."
            )
        else:
            healed_code = call_openai_api(
                prompt=prompt,
                max_tokens=4000,
                system_message="You are an expert test automation engineer. Return only valid Python code."
            )

        cleaned = healed_code.replace("```python", "").replace("```", "").strip()

        if not cleaned:
            raise HTTPException(status_code=500, detail="Azure OpenAI returned empty healed script.")

        temp_path = f"temp_healed_{uuid.uuid4().hex}.py"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        os.makedirs("artifacts", exist_ok=True)
        logs, status = [], "PASSED"

        def now(): 
            return datetime.now().strftime("%H:%M:%S")

        process = subprocess.Popen(
            ["python", temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ""):
            if line:
                logs.append(f"[{now()}] {line.strip()}")

        for line in iter(process.stderr.readline, ""):
            if line:
                logs.append(f"[{now()}] ERROR: {line.strip()}")

        process.wait()

        if process.returncode != 0:
            status = "FAILED"

        ss_log, dom_log = "", ""
        if os.path.exists("error_screenshot.png"):
            ss_path = f"artifacts/screenshot_{uuid.uuid4().hex}.png"
            os.replace("error_screenshot.png", ss_path)
            ss_log = f"Screenshot saved at {ss_path}"

        if os.path.exists("page_dom_dump.txt"):
            dom_path = f"artifacts/dom_{uuid.uuid4().hex}.html"
            os.replace("page_dom_dump.txt", dom_path)
            dom_log = f"DOM snapshot saved at {dom_path}"

        if ss_log: logs.append(ss_log)
        if dom_log: logs.append(dom_log)

        # Clean up
        os.unlink(temp_path)

        output = (
            "================ TEST PLAN ================\n"
            f"{testplan_output}\n\n"
            "================ HEALED SCRIPT ================\n"
            f"{cleaned}\n\n"
            "================ EXECUTION LOGS ================\n"
            + "\n".join(logs) +
            f"\n\n================ STATUS ================\n{status}\n"
        )

        return PlainTextResponse(content=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing execution failed: {e}")
