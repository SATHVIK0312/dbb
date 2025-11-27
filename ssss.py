from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
import subprocess
import logging
import os
import tempfile
from datetime import datetime
import asyncio
import sys

import aiosqlite
from jose import jwt, JWTError

# --- Your local modules (adjust paths if needed) ---
from app import utils
from app.config import SECRET_KEY, ALGORITHM  # Make sure this exists!
from app.routers.structured_logging import StructuredLogger, LogCategory
from app.routers import ai_healing
from app.routers.execution_enhanced import (
    generate_script_with_madl,
    collect_enhanced_error_context,
)

# --- Azure OpenAI with Certificate Auth ---
from azure.identity import CertificateCredential
from openai import AzureOpenAI

router = APIRouter()

DB_PATH = "genai.db"

async def get_db():
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


# ======================================================
# Azure OpenAI Client Setup (Certificate + API Key Auth)
# ======================================================
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
CERT_PATH = os.getenv("CERTIFICATE_PATH")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL]):
    raise RuntimeError("Missing required Azure OpenAI environment variables")

def get_bearer_token():
    if not all([CERT_PATH, AZURE_TENANT_ID, AZURE_CLIENT_ID]):
        raise RuntimeError("Certificate auth env vars missing: CERTIFICATE_PATH, AZURE_TENANT_ID, AZURE_CLIENT_ID")
    credential = CertificateCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        certificate_path=CERT_PATH
    )
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return token.token

def build_azure_client():
    bearer = get_bearer_token()
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        default_headers={
            "Authorization": f"Bearer {bearer}",
            "api-key": AZURE_OPENAI_API_KEY
        }
    )

azure_client = build_azure_client()


# ======================================================
# Main Execution WebSocket Endpoint
# ======================================================
@router.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(websocket: WebSocket, testcase_id: str, script_type: str):
    await websocket.accept()
    logger = StructuredLogger(testcase_id)

    try:
        # ------------------- 1. Extract & Validate JWT Token -------------------
        headers = dict(websocket.scope.get("headers", []))
        auth_header = headers.get(b"authorization") or headers.get(b"Authorization")

        if not auth_header:
            await websocket.send_json({"error": "Missing Authorization header", "status": "FAILED"})
            return

        try:
            auth_text = auth_header.decode("utf-8")
            if not auth_text.startswith("Bearer "):
                raise ValueError("Invalid auth format")
            token = auth_text.split("Bearer ", 1)[1].strip()
        except Exception:
            await websocket.send_json({"error": "Invalid Authorization header", "status": "FAILED"})
            return

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            userid = payload.get("userid")
            if not userid:
                raise JWTError("Missing userid in token")
        except JWTError as e:
            await websocket.send_json({"error": f"Invalid token: {str(e)}", "status": "FAILED"})
            return

        logger.info(LogCategory.INITIALIZATION, f"Execution started by user {userid}")

        # ------------------- 2. Database Connection & Access Check -------------------
        conn = await get_db()

        row = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = ?", (testcase_id,)
        )
        if not row:
            await websocket.send_json({"error": "Test case not found", "status": "FAILED"})
            return

        projectid = row["projectid"]
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = ? AND projectid = ?",
            (userid, projectid)
        )
        if not access:
            await websocket.send_json({"error": "Unauthorized access to project", "status": "FAILED"})
            return

        # ------------------- 3. Build Test Plan -------------------
        await websocket.send_json({"status": "BUILDING_PLAN", "log": "Building test plan..."})
        logger.info(LogCategory.PLAN_BUILDING, "Building test plan")

        prereq_chain = await utils.get_prereq_chain(conn, testcase_id)

        testplan_dict = {
            "pretestid_steps": {},
            "current_testid": testcase_id,
            "current_bdd_steps": {}
        }

        # Load prerequisite steps
        for tc_id in prereq_chain[:-1]:
            row = await conn.fetchrow(
                "SELECT steps, args FROM teststep WHERE testcaseid = ?", (tc_id,)
            )
            if row and row["steps"]:
                testplan_dict["pretestid_steps"][tc_id] = dict(zip(row["steps"], row["args"]))

        # Load current test case steps
        row = await conn.fetchrow(
            "SELECT steps, args FROM teststep WHERE testcaseid = ?", (testcase_id,)
        )
        if row and row["steps"]:
            testplan_dict["current_bdd_steps"] = dict(zip(row["steps"], row["args"]))

        testplan_json = json.dumps(testplan_dict)

        await websocket.send_json({"status": "PLAN_READY", "log": "Test plan ready"})
        logger.success(LogCategory.PLAN_BUILDING, "Test plan built")

        # ------------------- 4. Request Edit from Frontend -------------------
        await websocket.send_json({
            "status": "REQUEST_EDIT",
            "log": "Waiting for test data edit (or skip)...",
            "testplan": testplan_dict
        })

        try:
            msg = await asyncio.wait_for(websocket.receive_text(), timeout=120.0)
            data = json.loads(msg)

            if data.get("type") == "EDITED_TESTPLAN":
                edited = data.get("testplan_json")
                if edited:
                    if isinstance(edited, dict):
                        testplan_dict = edited
                    else:
                        testplan_dict = json.loads(edited)
                    testplan_json = json.dumps(testplan_dict)
                    logger.info(LogCategory.PLAN_BUILDING, "Applied edited test plan")
                else:
                    logger.info(LogCategory.PLAN_BUILDING, "Empty edit received, using original")
            elif data.get("type") == "SKIP_EDIT":
                logger.info(LogCategory.PLAN_BUILDING, "Edit skipped by user")
        except asyncio.TimeoutError:
            logger.warning(LogCategory.PLAN_BUILDING, "Edit timeout - proceeding with original plan")
        except WebSocketDisconnect:
            logger.warning(LogCategory.PLAN_BUILDING, "Client disconnected during edit")
            return
        except Exception as e:
            logger.error(LogCategory.PLAN_BUILDING, f"Edit parse error: {e}")

        # ------------------- 5. Generate Script -------------------
        await websocket.send_json({"status": "GENERATING", "log": "Generating script with AI..."})

        try:
            generated_script = await generate_script_with_madl(
                testcase_id=testcase_id,
                script_type=script_type,
                script_lang="python",
                testplan=testplan_dict,
                selected_madl_methods=None,
                logger=logger
            )
        except Exception as e:
            # Fallback to basic generator if enhanced not available
            from app.routers.executions import generate_script  # fallback
            generated_script = await generate_script(
                testcase_id=testcase_id,
                script_type=script_type,
                script_lang="python",
                testplan=testplan_dict
            )

        if not generated_script.strip():
            raise ValueError("Generated empty script")

        logger.success(LogCategory.GENERATION, "Script generated successfully")

        # ------------------- 6. Execute Script + Auto-Healing -------------------
        await websocket.send_json({"status": "EXECUTING", "log": "Running test script..."})
        execution_output = ""
        temp_file_path = None
        first_attempt_passed = False
        autoheal_attempt_passed = False
        final_status = "fail"
        execution_message = "Unknown error"

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(generated_script)
                temp_file_path = f.name

            process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            for line in process.stdout:
                line = line.rstrip()
                if line.strip():
                    execution_output += line + "\n"
                    await websocket.send_json({"status": "RUNNING", "log": line})

            return_code = process.wait()

            if return_code == 0:
                first_attempt_passed = True
                final_status = "success"
                execution_message = "Test passed"
            else:
                logger.error(LogCategory.EXECUTION, "First execution failed, attempting auto-heal")

                await websocket.send_json({"status": "AUTO_HEALING", "log": "Running AI self-healing..."})

                try:
                    healed_resp = await ai_healing.self_heal(
                        testplan_output=testplan_json,
                        generated_script=generated_script,
                        execution_logs=execution_output
                    )
                    healed_code = healed_resp.body.decode("utf-8")

                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as hf:
                        hf.write(healed_code)
                        healed_path = hf.name

                    healed_proc = subprocess.Popen(
                        [sys.executable, healed_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )

                    healed_output = ""
                    for line in healed_proc.stdout:
                        line = line.rstrip()
                        if line.strip():
                            healed_output += line + "\n"
                            await websocket.send_json({"status": "RUNNING", "log": f"[HEALED] {line}"})

                    if healed_proc.wait() == 0:
                        autoheal_attempt_passed = True
                        execution_output = healed_output
                        final_status = "healed"
                        execution_message = "Failed → Healed & Passed"
                    else:
                        final_status = "fail"
                        execution_message = "Failed even after healing"

                    os.unlink(healed_path)

                except Exception as heal_err:
                    logger.error(LogCategory.HEALING, f"Healing failed: {heal_err}")
                    execution_message = f"Failed (healing error: {heal_err})"

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        # ------------------- 7. Save Execution Result -------------------
        exeid = await utils.get_next_exeid(conn)
        await conn.execute(
            """INSERT INTO execution
               (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (exeid, testcase_id, script_type, datetime.now().date(), datetime.now().time(),
             execution_message, execution_output, final_status)
        )
        await conn.commit()

        # ------------------- 8. Final Response -------------------
        await websocket.send_json({
            "status": "COMPLETED",
            "final_status": final_status,
            "log": execution_message,
            "summary": logger.get_summary()
        })

        logger.success(LogCategory.INITIALIZATION, f"Execution finished → {final_status.upper()}")

    except WebSocketDisconnect:
        logger.warning(LogCategory.INITIALIZATION, "Client disconnected")
    except Exception as e:
        logger.error(LogCategory.INITIALIZATION, f"Unexpected error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e), "status": "FAILED"})
        except:
            pass
    finally:
        if 'conn' in locals():
            await conn.close()
        try:
            await websocket.close()
        except:
            pass
