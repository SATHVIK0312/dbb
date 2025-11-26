# normalized.py
import os
import json
import logging
import base64
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Body, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import PlainTextResponse, Response
from openai import AzureOpenAI
from azure.identity import CertificateCredential

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

# Cert path
CERT_DIR = Path(__file__).resolve().parent.parent / "JPMC1||certs"
CERT_PATH = CERT_DIR / "uatagent.azure.jpmchase.new.pem"

# -------------------------------------------------
# AZURE OPENAI CLIENT (inline, SPN + cert + fallback)
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
        logging.warning(f"SPN failed: {e}, using API key")
        token = AZURE_OPENAI_API_KEY

    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        default_headers={
            "Authorization": f"Bearer {token}",
            "user_sid": "AI_USER"
        },
        timeout=300
    )
    return client

# -------------------------------------------------
# AUTH DEPENDENCY
# -------------------------------------------------
async def get_current_any_user():
    return {"userid": "system", "role": "role-1"}


# ================================================
# 1. /normalize-uploaded
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
4. Return ONLY a valid JSON array. No markdown, no code blocks.

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
            raise HTTPException(status_code=500, detail=f"Invalid AI output: {raw_output[:200]}")

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
            "message": "Normalized by Azure OpenAI",
            "model_used": AZURE_OPENAI_DEPLOYMENT
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[NORMALIZE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {e}")


# ================================================
# 2. /self-heal (Azure OpenAI)
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

TEST PLAN (BDD):
{testplan_output}

ORIGINAL SCRIPT:
{generated_script}

EXECUTION LOGS:
{execution_logs}

DOM SNAPSHOT:
{dom_html or "No DOM snapshot"}

SCREENSHOT:
{"Provided" if screenshot_b64 else "No screenshot"}

RULES:
1. Fix selectors, waits, logic
2. Keep log format:
   - "Running action:"
   - "Action runned:"
   - "failed due to:"
3. Output ONLY raw Python code
"""

        messages = [{"role": "user", "content": prompt}]
        if screenshot_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this screenshot for UI changes."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]
            })

        client = get_azure_openai_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
            max_tokens=4000,
            timeout=300
        )

        healed_code = response.choices[0].message.content.strip()
        cleaned = healed_code.replace("```python", "").replace("```", "").strip()

        return Response(content=cleaned, media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-heal failed: {str(e)}")


# ================================================
# 3. /ai-execution (Generate + Run)
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
            raise HTTPException(status_code=400, detail="script_type must be 'playwright' or 'selenium'")
        if script_lang.lower() != "python":
            raise HTTPException(status_code=400, detail="Only Python is supported")

        prompt = f"""
Generate a FULLY EXECUTABLE Python test script for test case {testcase_id}.
Follow the TEST PLAN (JSON):
{testplan_output}

FRAMEWORK: {script_type.lower()}

LOG FORMAT:
- print("Running action: <STEP> at <timestamp>")
- print("Action runned: <STEP> at <timestamp>")
- print("Action <STEP> failed at <timestamp> due to: <error>")

CAPTURE ON FAILURE:
- Screenshot → 'error_screenshot.png'
- DOM → 'page_dom_dump.txt'
- Re-raise exception

RULES:
- Use sync API
- Wrap every step in try/except
- Implement get_timestamp()
- End with: if __name__ == "__main__": run_test_{testcase_id.lower()}
- Output ONLY raw Python code
"""

        client = get_azure_openai_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000,
            timeout=300
        )

        script = response.choices[0].message.content.strip()
        script = script.replace("```python", "").replace("```", "").strip()

        if not script:
            raise HTTPException(status_code=500, detail="Empty script from OpenAI")

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

        for line in process.stdout:
            if line := line.strip():
                logs.append(f"[{now()}] {line}")

        for line in process.stderr:
            if line := line.strip():
                logs.append(f"[{now()}] ERROR: {line}")

        process.wait()
        if process.returncode != 0:
            status = "FAILED"

        ss_log = dom_log = ""
        if os.path.exists("error_screenshot.png"):
            ss_path = f"artifacts/screenshot_{uuid.uuid4().hex}.png"
            os.replace("error_screenshot.png", ss_path)
            ss_log = f"Screenshot: {ss_path}"

        if os.path.exists("page_dom_dump.txt"):
            dom_path = f"artifacts/dom_{uuid.uuid4().hex}.html"
            os.replace("page_dom_dump.txt", dom_path)
            dom_log = f"DOM: {dom_path}"

        if ss_log: logs.append(ss_log)
        if dom_log: logs.append(dom_log)
        os.unlink(temp_path)

        output = (
            "================ TEST PLAN ================\n"
            f"{testplan_output}\n\n"
            "================ SCRIPT ================\n"
            f"{script}\n\n"
            "================ LOGS ================\n"
            + "\n".join(logs) +
            f"\n\n================ STATUS ================\n{status}"
        )

        return PlainTextResponse(content=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Execution failed: {e}")


# ================================================
# 4. /self-healing-execution
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
Self-heal the failing script.

TEST PLAN:
{testplan_output}

ORIGINAL SCRIPT:
{generated_script}

LOGS:
{execution_logs}

DOM:
{dom_html or "None"}

SCREENSHOT:
{"Provided" if screenshot_b64 else "None"}

Fix selectors, waits, logic. Keep log format. Output ONLY raw Python code.
"""

        messages = [{"role": "user", "content": prompt}]
        if screenshot_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze screenshot."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]
            })

        client = get_azure_openai_client()
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
            max_tokens=4000,
            timeout=300
        )

        healed_code = response.choices[0].message.content.strip()
        healed_code = healed_code.replace("```python", "").replace("```", "").strip()

        if not healed_code:
            raise HTTPException(status_code=500, detail="Empty healed script")

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

        for line in process.stdout:
            if line := line.strip():
                logs.append(f"[{now()}] {line}")

        for line in process.stderr:
            if line := line.strip():
                logs.append(f"[{now()}] ERROR: {line}")

        process.wait()
        if process.returncode != 0:
            status = "FAILED"

        ss_log = dom_log = ""
        if os.path.exists("error_screenshot.png"):
            ss_path = f"artifacts/screenshot_{uuid.uuid4().hex}.png"
            os.replace("error_screenshot.png", ss_path)
            ss_log = f"Screenshot: {ss_path}"

        if os.path.exists("page_dom_dump.txt"):
            dom_path = f"artifacts/dom_{uuid.uuid4().hex}.html"
            os.replace("page_dom_dump.txt", dom_path)
            dom_log = f"DOM: {dom_path}"

        if ss_log: logs.append(ss_log)
        if dom_log: logs.append(dom_log)
        os.unlink(temp_path)

        output = (
            "================ TEST PLAN ================\n"
            f"{testplan_output}\n\n"
            "================ HEALED SCRIPT ================\n"
            f"{healed_code}\n\n"
            "================ LOGS ================\n"
            + "\n".join(logs) +
            f"\n\n================ STATUS ================\n{status}"
        )

        return PlainTextResponse(content=output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing execution failed: {e}")











async def generate_script_with_madl(
    testcase_id: str,
    script_type: str,
    script_lang: str,
    testplan: dict,
    selected_madl_methods: Optional[List[dict]] = None,
    logger: Optional[StructuredLogger] = None
):
    """
    Generate test script using Azure OpenAI with MADL method integration.
    Logic unchanged — only Gemini → Azure OpenAI.
    """
    try:
        if logger:
            logger.info(LogCategory.GENERATION, "Starting script generation with Azure OpenAI")

        # Build MADL methods context
        madl_context = ""
        if selected_madl_methods:
            madl_context = "\n\n# AVAILABLE REUSABLE METHODS (from MADL):\n"
            for method in selected_madl_methods:
                madl_context += f"- {method['signature']}: {method['intent']}\n"
                madl_context += f"  Example: {method['example']}\n"

        prompt = f"""
        Generate a test script for test case ID: {testcase_id}
        Script type: {script_type}, Language: {script_lang}
        Test plan JSON: {json.dumps(testplan)}

        {madl_context}

        Requirements:
        - If AVAILABLE REUSABLE METHODS are provided, USE them where applicable
        - Include comments above each action describing the step
        - Don't use pytest
        - Wrap each action in try-catch block
        - Add print statements with timestamps before and after each action
        - Format: 'Running action: <step> at <timestamp>' and 'Action completed: <step> at <timestamp>'
        - If action fails, print 'Action <step> failed at <timestamp> due to: <error>'
        - Handle errors gracefully with context collection (screenshot, DOM snapshot)
        - Use appropriate imports and syntax
        - Output ONLY the code, no additional explanations or markdown
        """

        client = get_azure_openai_client()  # ← Uses your existing config
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000,
            timeout=300
        )

        raw_text = (response.choices[0].message.content or "").strip()
        if not raw_text:
            raise ValueError("Azure OpenAI returned empty script content")

        # ---- CLEAN MARKDOWN CODE FENCES (same logic) ----
        script_content = raw_text
        if "```" in raw_text:
            parts = raw_text.split("```")
            if len(parts) >= 2:
                code_block = parts[1]
                lines = code_block.splitlines()
                if lines and lines[0].strip().lower().startswith("python"):
                    lines = lines[1:]
                script_content = "\n".join(lines).strip()
        else:
            script_content = raw_text

        if not script_content:
            raise ValueError("Script content empty after cleaning code fences")

        if logger:
            logger.success(
                LogCategory.GENERATION,
                f"Script generated ({len(script_content)} bytes, cleaned markdown fences)"
            )

        return script_content

    except Exception as e:
        if logger:
            logger.error(LogCategory.GENERATION, f"Script generation failed: {str(e)}")
        raise Exception(f"Script generation failed: {str(e)}")


async def collect_enhanced_error_context(
    logs: str,
    testplan: str,
    generated_script: str
) -> Dict[str, Any]:
    """
    Collect comprehensive error context for self-healing
    Includes execution logs, test plan, script, and attempts to extract diagnostics
    """
    try:
        error_context = {
            "execution_logs": logs,
            "testplan": testplan,
            "generated_script": generated_script,
            "timestamp": datetime.now().isoformat(),
            "diagnostics": {
                "error_patterns": [],
                "failed_actions": []
            }
        }
        
        # Extract error patterns from logs
        error_lines = [line for line in logs.split('\n') if 'error' in line.lower() or 'failed' in line.lower()]
        error_context["diagnostics"]["error_patterns"] = error_lines[:10]  # Top 10 errors
        
        # Extract failed actions
        for line in logs.split('\n'):
            if 'failed' in line.lower() or 'exception' in line.lower():
                error_context["diagnostics"]["failed_actions"].append(line.strip())
        
        return error_context
    
    except Exception as e:
        utils.logger.error(f"[HEALING] Error context collection failed: {str(e)}")
        return {"error": str(e), "execution_logs": logs}



