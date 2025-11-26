```# normalized.py
import os
import json
import logging
import base64
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Body, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import PlainTextResponse, Response
from openai import AzureOpenAI
from azure.identity import CertificateCredential
import google.generativeai as genai

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI()

# -------------------------------------------------
# CONFIG (from .env)
# -------------------------------------------------
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cert path (same as your original logic)
CERT_DIR = Path(__file__).resolve().parent.parent / "JPMC1||certs"
CERT_PATH = CERT_DIR / "uatagent.azure.jpmchase.new.pem"

# -------------------------------------------------
# GEMINI SETUP
# -------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-pro")

# -------------------------------------------------
# AZURE OPENAI TOKEN + CLIENT (inline)
# -------------------------------------------------
def get_azure_openai_client():
    if not CERT_PATH.exists():
        raise RuntimeError(f"Cert not found: {CERT_PATH}")

    scope = "https://cognitiveservices.azure.com/.default"
    try:
        credential = CertificateCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            certificate_path=str(CERT_PATH)
        )
        token = credential.get_token(scope).token
        logging.info(f"SPN Token: {token[:20]}...")
    except Exception as e:
        logging.warning(f"SPN failed: {e}, falling back to API key")
        token = AZURE_OPENAI_API_KEY

    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        default_headers={
            "Authorization": f"Bearer {token}",
            "user_sid": "NORMALIZE_USER"
        },
        timeout=300
    )
    return client

# -------------------------------------------------
# AUTH DEPENDENCY (keep your existing)
# -------------------------------------------------
async def get_current_any_user():
    # Replace with real JWT logic
    return {"userid": "system", "role": "role-1"}

# ================================================
# 1. NORMALIZE-UPLOADED (Azure OpenAI)
# ================================================
@app.post("/normalize-uploaded")
async def normalize_uploaded(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_any_user)
):
    try:
        testcase_id = payload.get("testcaseid")
        original_steps = payload.get("original_steps", [])

        if not testcase_id:
            raise HTTPException(status_code=400, detail="testcaseid is required")
        if not original_steps:
            raise HTTPException(status_code=400, detail="original_steps cannot be empty")

        steps_input = []
        for i, step in enumerate(original_steps):
            idx = step.get("Index", i + 1)
            step_text = str(step.get("Step", "") or "").strip()
            data_text = str(step.get("TestDataText", "") or "").strip()
            steps_input.append({"Index": idx, "Step": step_text, "TestDataText": data_text})

        prompt = f"""You are an expert QA automation engineer.
Normalize the following test steps into clean, atomic, BDD-style format (Given/When/Then).

Rules:
1. Rewrite each Step clearly and action-oriented
2. Keep TestDataText as human-readable
3. Infer structured TestData JSON:
   - email + password → {{"username": "...", "password": "..."}}
   - URL → {{"url": "..."}}
   - single value → {{"value": "..."}}}
   - empty → {{}}
4. Return ONLY a valid JSON array. No markdown, no code blocks, no explanations.

Input:
{json.dumps(steps_input, indent=2)}

Output format:
[
  {{
    "Index": 1,
    "Step": "When the user enters valid credentials",
    "TestDataText": "user@example.com, pass123",
    "TestData": {{"username": "user@example.com", "password": "pass123"}}
  }}
]
"""

        client = get_azure_openai_client()

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000,
            top_p=0.9,
            timeout=300
        )

        raw_output = response.choices[0].message.content.strip()
        start = raw_output.find("[")
        end = raw_output.rfind("]") + 1
        if start == -1 or end == 0:
            raise HTTPException(status_code=500, detail=f"AI did not return JSON: {raw_output[:200]}")

        try:
            normalized_data = json.loads(raw_output[start:end])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")

        normalized_steps = []
        for i, item in enumerate(normalized_data):
            test_data = item.get("TestData", {})
            if not isinstance(test_data, dict):
                test_data = {"value": str(test_data)} if test_data else {}
            normalized_steps.append({
                "Index": item.get("Index", i + 1),
                "Step": str(item.get("Step", "") or "").strip(),
                "TestDataText": str(item.get("TestDataText", "") or "").strip(),
                "TestData": test_data
            })

        return {
            "testcaseid": testcase_id,
            "original_steps_count": len(original_steps),
            "normalized_steps": normalized_steps,
            "message": "Test steps successfully normalized by Azure OpenAI",
            "model_used": AZURE_OPENAI_DEPLOYMENT,
            "auth_method": "SPN" if token != AZURE_OPENAI_API_KEY else "API Key"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[NORMALIZE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {e}")


# ================================================
# 2. GEMINI: /self-heal
# ================================================
@app.post("/self-heal")
async def self_heal(
    testplan_output: str = Form(...),
    generated_script: str = Form(...),
    execution_logs: str = Form(...),
    screenshot: UploadFile = File(None),
    dom_snapshot: UploadFile = File(None)
):
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

        parts = [{"text": prompt}]
        if screenshot_b64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": screenshot_b64
                }
            })

        response = gemini_model.generate_content(parts)
        healed_code = response.text.strip()

        cleaned = healed_code.replace("```python", "").replace("```", "").strip()

        return Response(content=cleaned, media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-heal failed: {str(e)}")


# ================================================
# 3. GEMINI: /ai-execution
# ================================================
@app.post("/ai-execution")
async def ai_execution(
    testcase_id: str = Form(...),
    script_type: str = Form(...),
    script_lang: str = Form(...),
    testplan_output: str = Form(...)
):
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

        resp = gemini_model.generate_content([{"text": prompt}])
        script = (resp.text or "").replace("```python", "").replace("```", "").strip()

        if not script:
            raise HTTPException(status_code=500, detail="Gemini returned empty script.")

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

        for line in process.stdout.readline, "":
            if line:
                logs.append(f"[{now()}] {line.strip()}")

        for line in process.stderr.readline, "":
            if line:
                logs.append(f"[{now()}] ERROR: {line.strip()}")

        process.wait()

        if process.returncode != 0:
            status = "FAILED"

        ss_log = dom_log = ""
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


# ================================================
# 4. GEMINI: /self-healing-execution
# ================================================
@app.post("/self-healing-execution")
async def self_healing_execution(
    testplan_output: str = Form(...),
    generated_script: str = Form(...),
    execution_logs: str = Form(...),
    screenshot: UploadFile = File(None),
    dom_snapshot: UploadFile = File(None)
):
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

        parts = [{"text": prompt}]
        if screenshot_b64:
            parts.append({"inline_data": {"mime_type": "image/png", "data": screenshot_b64}})

        response = gemini_model.generate_content(parts)
        healed_code = (response.text or "").replace("```python", "").replace("```", "").strip()

        if not healed_code:
            raise HTTPException(status_code=500, detail="Gemini returned empty healed script.")

        temp_path = f"temp_healed_{uuid.uuid4().hex}.py"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(healed_code)

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

        for line in process.stdout.readline, "":
            if line:
                logs.append(f"[{now()}] {line.strip()}")

        for line in process.stderr.readline, "":
            if line:
                logs.append(f"[{now()}] ERROR: {line.strip()}")

        process.wait()

        if process.returncode != 0:
            status = "FAILED"

        ss_log = dom_log = ""
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

        os.unlink(temp_path)

        output = (
            "================ TEST PLAN ================\n"
            f"{testplan_output}\n\n"
            "================ HEALED SCRIPT ================\n"
            f"{healed_code}\n\n"
            "================ EXECUTION LOGS ================\n"
            + "\n".join(logs) +
            f"\n\n================ STATUS ================\n{status}\n"
        )

        return PlainTextResponse(content=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing execution failed: {e}")```
