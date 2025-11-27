# app/routers/executions.py
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, UploadFile, File
from typing import List, Dict, Any, Optional
from fastapi.responses import StreamingResponse
import json
import subprocess
import logging
import os
import tempfile
from datetime import datetime
import asyncio
import sys
import aiosqlite
import traceback

from app import utils
from app.routers.users import get_current_any_user
from app.routers.structured_logging import StructuredLogger, LogLevel, LogCategory
from app.routers import ai_healing

DB_PATH = "genai.db"   # adjust path if needed

async def get_db():
    return await aiosqlite.connect(DB_PATH)

# ---------------- Azure/OpenAI imports and client builder ----------------
from azure.identity import CertificateCredential
from openai import AzureOpenAI

router = APIRouter()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
CERT_PATH = os.getenv("CERTIFICATE_PATH")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

# Only require these env vars at runtime when generation is used
def get_bearer_token():
    cred = CertificateCredential(tenant_id=AZURE_TENANT_ID, client_id=AZURE_CLIENT_ID, certificate_path=CERT_PATH)
    token = cred.get_token("https://cognitiveservices.azure.com/.default")
    return token.token

def build_azure_client():
    bearer = get_bearer_token()
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        default_headers={
            "Authorization": f"Bearer {bearer}",
            "api-key": AZURE_OPENAI_API_KEY
        }
    )
    return client

azure_client = None
try:
    if all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_MODEL,
            CERT_PATH, AZURE_TENANT_ID, AZURE_CLIENT_ID]):
        azure_client = build_azure_client()
    else:
        logging.getLogger("execution_engine").warning("Azure OpenAI env vars not fully set - generation disabled")
except Exception as e:
    logging.getLogger("execution_engine").warning("Azure OpenAI client init failed: %s", e)
    azure_client = None

# ---------------- Generation function (your existing Azure wrapper) ----------------
async def generate_script(testcase_id: str, script_type: str, script_lang: str, testplan: dict):
    """Generate Python automation script via Azure OpenAI."""
    if azure_client is None:
        raise RuntimeError("Azure OpenAI client not initialized or env vars missing")

    prompt = (
        f"Generate a test script for test case ID: {testcase_id}\n"
        f"Script type: {script_type}, Language: {script_lang}\n"
        f"Test plan JSON: {json.dumps(testplan)}\n\n"
        "Requirements:\n"
        "- Include comments above each action describing the step.\n"
        "- Don't use pytest.\n"
        "- Wrap each action in try/except.\n"
        "- Add print statements with timestamps before and after each action.\n"
        "- Print failures with reasons.\n"
        "- Output only code — no markdown, no explanation.\n"
    )

    system_msg = (
        "You are an assistant that outputs only runnable Python test code. "
        "No markdown, no explanation. Only script content."
    )

    try:
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_MODEL,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=2800
        )
        # several SDK variants; try to extract text robustly
        script = None
        try:
            script = response.choices[0].message.content.strip()
        except Exception:
            try:
                script = response.choices[0].text.strip()
            except Exception:
                script = str(response)
        # Remove markdown fences if present
        if "```" in script:
            parts = script.split("```")
            if len(parts) >= 2:
                block = parts[1]
                lines = block.splitlines()
                if lines and lines[0].strip().lower().startswith("python"):
                    lines = lines[1:]
                script = "\n".join(lines).strip()
        return script
    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Azure OpenAI script generation failed: {e}")

# ---------------- SQLite compatible helpers ----------------
async def fetch_prereq_chain(conn: aiosqlite.Connection, testcase_id: str) -> List[str]:
    """
    Return list of testcase ids in prerequisite order ending with testcase_id.
    Schema assumptions: testcase table has columns (testcaseid, pretestid)
    """
    chain = []
    visited = set()

    async def _recurse(tc_id):
        if not tc_id or tc_id in visited:
            return
        visited.add(tc_id)
        cur = await conn.execute("SELECT pretestid FROM testcase WHERE testcaseid = ?", (tc_id,))
        row = await cur.fetchone()
        if row:
            pre = row[0]
            if pre:
                await _recurse(pre)
        chain.append(tc_id)

    await _recurse(testcase_id)
    return chain

# ---------------- Single WebSocket endpoint (sqlite compatible) ----------------
@router.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(websocket: WebSocket, testcase_id: str, script_type: str):
    await websocket.accept()
    utils.logger.debug(f"[EXEC] WebSocket opened for {testcase_id}, {script_type}")
    logger = StructuredLogger(testcase_id)

    # --- extract token: query param or Authorization header ---
    token = websocket.query_params.get("session_token") or websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token:
        headers = dict(websocket.scope.get("headers", []))
        auth_header = headers.get(b"authorization") or headers.get(b"Authorization")
        if auth_header and isinstance(auth_header, (bytes, bytearray)):
            try:
                auth_text = auth_header.decode(errors="ignore").strip()
                if auth_text.lower().startswith("bearer "):
                    token = auth_text.split(" ", 1)[1].strip()
            except Exception:
                token = None

    if not token:
        await websocket.send_text(json.dumps({"error": "Authorization token missing", "status": "FAILED"}))
        await websocket.close()
        return

    # Validate JWT (your SECRET in utils.config expected)
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, utils.config.SECRET_KEY, algorithms=[utils.config.ALGORITHM])
        userid = payload.get("userid")
        role = payload.get("role")
        current_user = {"userid": userid, "role": role}
    except JWTError:
        await websocket.send_text(json.dumps({"error": "Invalid token", "status": "FAILED"}))
        await websocket.close()
        return

    conn = None
    try:
        conn = await get_db()
        # Make rows accessible by name
        conn.row_factory = aiosqlite.Row

        userid = current_user["userid"]
        logger.info(LogCategory.INITIALIZATION, f"Execution started for {testcase_id}")

        # ---------------- validate test case exists and user has access ----------------
        cur = await conn.execute("SELECT projectid FROM testcase WHERE testcaseid = ?", (testcase_id,))
        row = await cur.fetchone()
        if not row:
            await websocket.send_text(json.dumps({"error": "Test case not found", "status": "FAILED"}))
            await websocket.close()
            return
        tc_project = row["projectid"]

        # projectuser table likely has (userid, projectid) rows; adjust if your schema stores arrays
        cur = await conn.execute("SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?", (userid, tc_project))
        access = await cur.fetchone()
        if not access:
            await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
            await websocket.close()
            return

        # ---------------- build test plan ----------------
        await websocket.send_text(json.dumps({"status": "BUILDING_PLAN", "log": "Building test plan..."}))
        logger.info(LogCategory.PLAN_BUILDING, "Building test plan from prerequisites and steps")

        prereq_chain = await fetch_prereq_chain(conn, testcase_id)
        testplan_dict = {"pretestid_steps": {}, "current_testid": testcase_id, "current_bdd_steps": {}}

        # fetch steps for prerequisites
        for tc_id in prereq_chain[:-1]:
            cur = await conn.execute("SELECT steps, args FROM teststep WHERE testcaseid = ?", (tc_id,))
            r = await cur.fetchone()
            if r and r["steps"]:
                # assuming steps and args stored as JSON strings or as some serializable format
                steps = r["steps"]
                args = r["args"]
                # if steps/args are stored as JSON text, parse them
                try:
                    if isinstance(steps, str):
                        steps_parsed = json.loads(steps)
                    else:
                        steps_parsed = steps
                    if isinstance(args, str):
                        args_parsed = json.loads(args)
                    else:
                        args_parsed = args
                except Exception:
                    # fallback: assume they are simple comma-separated
                    steps_parsed = steps.split(",") if isinstance(steps, str) else list(steps)
                    args_parsed = args.split(",") if isinstance(args, str) else list(args)

                testplan_dict["pretestid_steps"][tc_id] = dict(zip(steps_parsed, args_parsed))

        # current testcase
        cur = await conn.execute("SELECT steps, args FROM teststep WHERE testcaseid = ?", (testcase_id,))
        r = await cur.fetchone()
        if r and r["steps"]:
            steps = r["steps"]
            args = r["args"]
            try:
                steps_parsed = json.loads(steps) if isinstance(steps, str) else steps
                args_parsed = json.loads(args) if isinstance(args, str) else args
            except Exception:
                steps_parsed = steps.split(",") if isinstance(steps, str) else list(steps)
                args_parsed = args.split(",") if isinstance(args, str) else list(args)
            testplan_dict["current_bdd_steps"] = dict(zip(steps_parsed, args_parsed))

        testplan_json = json.dumps(testplan_dict)
        await websocket.send_text(json.dumps({"status": "PLAN_READY", "log": "Test plan built"}))
        logger.success(LogCategory.PLAN_BUILDING, "Test plan built successfully")

        # request frontend to edit
        await websocket.send_text(json.dumps({"status": "REQUEST_EDIT", "log": "Please edit test data or skip", "testplan": testplan_dict}))
        logger.info(LogCategory.PLAN_BUILDING, "Sent REQUEST_EDIT to frontend; waiting for user response")
        try:
            edit_msg = await websocket.receive_text()
            try:
                edit_data = json.loads(edit_msg)
            except Exception:
                edit_data = {}
            if edit_data.get("type") == "EDITED_TESTPLAN":
                edited_plan = edit_data.get("testplan_json")
                if edited_plan:
                    if isinstance(edited_plan, dict):
                        testplan_dict = edited_plan
                        testplan_json = json.dumps(edited_plan)
                    else:
                        try:
                            testplan_dict = json.loads(edited_plan)
                            testplan_json = json.dumps(testplan_dict)
                        except Exception:
                            logger.info(LogCategory.PLAN_BUILDING, "Edited testplan invalid; continuing original")
        except WebSocketDisconnect:
            logger.warning(LogCategory.PLAN_BUILDING, "Client disconnected while waiting for edit; aborting execution")
            await websocket.close()
            return
        except Exception as e:
            logger.error(LogCategory.PLAN_BUILDING, f"Error while waiting for edited plan: {e}")

        # MADL disabled (stub)
        await websocket.send_text(json.dumps({"status": "NO_MADL_METHODS", "log": "MADL search skipped in this environment"}))
        logger.info(LogCategory.SEARCH, "MADL disabled for this deployment")

        # ---------------- script generation ----------------
        await websocket.send_text(json.dumps({"status": "GENERATING", "log": "Generating script..."}))
        try:
            # Prefer generate_script_with_madl if available
            gen_func = None
            try:
                from app.routers.execution_enhanced import generate_script_with_madl
                gen_func = generate_script_with_madl
            except Exception:
                gen_func = generate_script

            generated_script = await gen_func(testcase_id=testcase_id, script_type=script_type, script_lang="python", testplan=testplan_dict, selected_madl_methods=None, logger=logger)
            if not generated_script or not isinstance(generated_script, str):
                raise RuntimeError("Generated script empty/invalid")
        except Exception as e:
            await websocket.send_text(json.dumps({"error": f"Generation failed: {str(e)}", "status": "FAILED"}))
            await websocket.close()
            return

        # ---------------- execute script ----------------
        first_attempt_passed = False
        autoheal_attempt_passed = False
        execution_message = None
        execution_output = ""
        temp_file_path = None

        await websocket.send_text(json.dumps({"status": "EXECUTING", "log": "Starting execution..."}))
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmpf:
                tmpf.write(generated_script)
                temp_file_path = tmpf.name

            logger.info(LogCategory.EXECUTION, f"Executing script from {temp_file_path}")
            process = subprocess.Popen([sys.executable, temp_file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            for line in process.stdout:
                if line is None:
                    continue
                line = line.rstrip("\n")
                if line.strip():
                    execution_output += line + "\n"
                    await websocket.send_text(json.dumps({"status": "RUNNING", "log": line}))
                    await asyncio.sleep(0.02)

            return_code = process.wait()
            if return_code == 0:
                logger.success(LogCategory.EXECUTION, "Script executed successfully")
                first_attempt_passed = True
                execution_message = "Script executed successfully"
            else:
                logger.error(LogCategory.EXECUTION, "Script execution failed")
                # auto-heal (use your ai_healing module)
                error_context = await ai_healing.collect_enhanced_error_context(execution_output, testplan_json, generated_script)
                await websocket.send_text(json.dumps({"status": "AUTO_HEALING", "log": "Execution failed. Starting auto-healing..."}))
                try:
                    healed_response = await ai_healing.self_heal(testplan_output=testplan_json, generated_script=generated_script, execution_logs=execution_output, screenshot=None, dom_snapshot=None)
                    healed_code = healed_response.body.decode('utf-8') if hasattr(healed_response, 'body') else str(healed_response)
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as hf:
                        hf.write(healed_code)
                        healed_temp_path = hf.name
                    healed_proc = subprocess.Popen([sys.executable, healed_temp_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                    healed_output = ""
                    for line in healed_proc.stdout:
                        if line is None: continue
                        line = line.rstrip("\n")
                        if line.strip():
                            healed_output += line + "\n"
                            await websocket.send_text(json.dumps({"status": "RUNNING", "log": f"[AUTO-HEALED] {line}"}))
                            await asyncio.sleep(0.02)
                    healed_return = healed_proc.wait()
                    if healed_return == 0:
                        logger.success(LogCategory.HEALING, "Healed script executed successfully")
                        autoheal_attempt_passed = True
                        execution_output = healed_output
                        execution_message = "[AUTO-HEALED] Healed execution completed"
                    else:
                        logger.error(LogCategory.HEALING, "Healed script still failed")
                        execution_message = "[AUTO-HEALED] Script failed even after healing"
                        execution_output = healed_output
                    if 'healed_temp_path' in locals() and os.path.exists(healed_temp_path):
                        os.unlink(healed_temp_path)
                except Exception as he:
                    logger.error(LogCategory.HEALING, f"Healing failed: {he}")
                    execution_message = f"Healing failed: {he}"

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

        # ---------------- final status ----------------
        if first_attempt_passed:
            final_status = "success"
        elif autoheal_attempt_passed:
            final_status = "healed"
        else:
            final_status = "fail"

        # ---------------- store execution (sqlite) ----------------
        exeid = await utils.get_next_exeid(conn)  # ensure utils.get_next_exeid works with sqlite (returns string)
        datestamp = datetime.now().date()
        exetime = datetime.now().time()
        await conn.execute(
            "INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (exeid, testcase_id, script_type, str(datestamp), str(exetime), execution_message, execution_output, final_status)
        )
        await conn.commit()

        await websocket.send_text(json.dumps({"status": "STORAGE_SKIPPED", "log": "MADL storage disabled in this environment"}))
        logger.info(LogCategory.STORAGE, "MADL storage skipped")

        await websocket.send_text(json.dumps({"status": "COMPLETED", "log": execution_message, "final_status": final_status, "summary": logger.get_summary()}))
        logger.success(LogCategory.INITIALIZATION, "Execution completed")

    except WebSocketDisconnect:
        logger.warning(LogCategory.INITIALIZATION, "Client disconnected")
    except Exception as exc:
        logger.error(LogCategory.INITIALIZATION, f"Unexpected error: {exc}")
        try:
            await websocket.send_text(json.dumps({"error": str(exc), "status": "FAILED"}))
        except Exception:
            pass
    finally:
        if conn:
            await conn.close()
        try:
            await websocket.close()
        except Exception:
            pass
        utils.logger.info(f"[EXEC] Execution finished for {testcase_id}")
        utils.logger.debug(f"[EXEC] Final logs:\n{logger.get_readable_logs()}")
