from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    UploadFile,        # ✅ ADD THIS
    File               # (optional – if you use File(...))
)

from typing import List, Dict, Any
from fastapi.responses import StreamingResponse
import json
import subprocess
import logging
import os
import tempfile
from datetime import datetime

import models
import utils
import database as db
from routers.users import get_current_any_user

from concurrent.futures import ThreadPoolExecutor
import asyncio
import sys
import io
import traceback

from selenium import webdriver
from azure_openai_client import call_openai_api
import config

# MADL Imports
from routers.users import get_current_any_user
from routers.madl_integration import madl_client, search_for_reusable_methods
from routers.madl_storage import store_successful_execution_to_madl
from routers.structured_logging import StructuredLogger, LogLevel, LogCategory, extract_madl_from_logs
from routers import ai_healing


router = APIRouter()

# genai.configure(api_key=config.GEMINI_API_KEY) # REMOVE THIS LINE

async def generate_script(testcase_id: str, script_type: str, script_lang: str, testplan: dict):
    """Generate test script using Azure OpenAI API"""
    try:
        prompt = f"Generate a test script for test case ID: {testcase_id}\n"
        prompt += f"Script type: {script_type}, Language: {script_lang}\n"
        prompt += "Test plan JSON: " + json.dumps(testplan) + "\n"
        prompt += "Requirements:\n"
        prompt += "- Include comments above each action describing the step.\n"
        prompt += "- Don't use pytest\n"
        prompt += "- Wrap each action in a try-catch block.\n"
        prompt += "- Add print statements with timestamps before and after each action (e.g., 'Running action: <step> at <timestamp>' and 'Action runned: <step> at <timestamp>').\n"
        prompt += "- If an action fails, print 'Action <step> failed at <timestamp> due to: <error>'.\n"
        prompt += "- Use appropriate imports and syntax for the chosen script type and language.\n"
        prompt += "- Handle actions: 'Navigate to login', 'Enter credentials', 'Submit form' (assume credentials are in 'user/pass' format, split by '/').\n"
        prompt += "- Output only the code, no additional explanations or markdown (e.g., no ''' or # comments outside actions).\n"

        script_content = call_openai_api(
            prompt=prompt,
            max_tokens=4000,
            system_message="You are a test automation expert. Generate only executable Python code."
        )

        if not script_content:
            raise ValueError("Azure OpenAI returned empty script content")

        return script_content
    except Exception as e:
        raise Exception(f"Script generation failed: {str(e)}")

async def execute_with_auto_healing(
    testcase_id: str,
    script_type: str,
    conn,
    user_id: str
):
    """
    Execute test script with automatic self-healing on failure.
    Steps:
    1. Execute script
    2. If fails, collect error context (logs, screenshot, DOM)
    3. Call self-healing API
    4. Re-execute healed script
    """
    from app.routers import ai_healing
    import tempfile
    
    try:
        # Fetch script
        script_row = await conn.fetchrow(
            "SELECT script FROM testscript WHERE testcaseid = $1",
            testcase_id
        )
        if not script_row or not script_row["script"]:
            return {
                "status": "FAILED",
                "message": "No script found",
                "healed": False,
                "logs": []
            }
        
        # Parse script
        script_json = script_row["script"]
        script_data = json.loads(script_json)
        script_obj = script_data.get("script", {})
        script_content_lines = script_obj.get("code", [])
        script_content = '\n'.join(line for line in script_content_lines if line.strip())
        
        # Fetch test plan
        testplan_row = await conn.fetchrow(
            "SELECT * FROM testplan WHERE testcaseid = $1",
            testcase_id
        )
        testplan_output = json.dumps(dict(testplan_row)) if testplan_row else "{}"
        
        # First execution attempt
        logs = []
        temp_file_path = None
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(script_content)
                temp_file_path = temp_file.name
            
            utils.logger.info(f"[EXEC] Executing script: {temp_file_path}")
            process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stdout, stderr = process.communicate()
            logs.append(stdout)
            
            if process.returncode == 0:
                utils.logger.info(f"[EXEC] Script executed successfully for {testcase_id}")
                return {
                    "status": "SUCCESS",
                    "message": "Script executed successfully",
                    "healed": False,
                    "logs": logs,
                    "output": stdout
                }
            else:
                # First execution failed - trigger self-healing
                execution_logs = stderr or stdout
                
                utils.logger.warning(f"[HEALING] Script failed for {testcase_id}, triggering self-healing...")
                utils.logger.info(f"[HEALING] Error logs: {execution_logs[:200]}")
                
                try:
                    healed_response = await ai_healing.self_heal(
                        testplan_output=testplan_output,
                        generated_script=script_content,
                        execution_logs=execution_logs,
                        screenshot=None,
                        dom_snapshot=None
                    )
                    
                    # Extract healed code from Response object
                    healed_code = healed_response.body.decode('utf-8') if hasattr(healed_response, 'body') else str(healed_response)
                    logs.append(f"\n[SELF-HEALING] Healed script generated:\n{healed_code[:200]}...")
                    
                    # Execute healed script
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as healed_file:
                        healed_file.write(healed_code)
                        healed_temp_path = healed_file.name
                    
                    utils.logger.info(f"[HEALING] Executing healed script: {healed_temp_path}")
                    healed_process = subprocess.Popen(
                        [sys.executable, healed_temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    healed_stdout, healed_stderr = healed_process.communicate()
                    logs.append(healed_stdout)
                    
                    if healed_process.returncode == 0:
                        utils.logger.info(f"[HEALING] Healed script executed successfully for {testcase_id}")
                        return {
                            "status": "SUCCESS",
                            "message": "Script executed successfully after self-healing",
                            "healed": True,
                            "logs": logs,
                            "output": healed_stdout
                        }
                    else:
                        utils.logger.error(f"[HEALING] Healed script still failed: {healed_stderr}")
                        return {
                            "status": "FAILED",
                            "message": f"Script failed even after self-healing: {healed_stderr}",
                            "healed": True,
                            "logs": logs,
                            "output": healed_stderr
                        }
                    
                finally:
                    if 'healed_temp_path' in locals() and os.path.exists(healed_temp_path):
                        os.unlink(healed_temp_path)
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except Exception as e:
        utils.logger.error(f"[HEALING] Auto-healing failed: {str(e)}")
        return {
            "status": "FAILED",
            "message": f"Auto-healing error: {str(e)}",
            "healed": False,
            "logs": logs if 'logs' in locals() else []
        }

from jose import jwt, JWTError
from jose import jwt, JWTError
from fastapi import WebSocket, WebSocketDisconnect
import json
import tempfile
import subprocess
import sys
import asyncio
import os
from datetime import datetime

import utils, config, database as db
from routers.madl_integration import search_for_reusable_methods
from routers.execution_enhanced import generate_script_with_madl
from routers import madl_storage


@router.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str
):
    """
    WebSocket endpoint:
    1. Validate JWT from headers
    2. Build test plan (prereq + current steps)
    3. SEND test plan to client for EDITING (NEW)
    4. Wait for edited testplan or skip (NEW)
    5. Search MADL for reusable methods (using edited TP)
    6. Generate script with Gemini (using edited TP)
    7. Execute script, stream logs
    8. Store execution + optionally store reusable MADL methods
    """
    await websocket.accept()
    utils.logger.debug(f"[MADL-EXEC] WebSocket opened for {testcase_id}, {script_type}")

    # ---------------- JWT extraction & validation ----------------
    token = None
    if "headers" in websocket.scope:
        headers = dict(websocket.scope["headers"])
        auth_header = headers.get(b"authorization")
        if auth_header and isinstance(auth_header, bytes) and auth_header.startswith(b"Bearer "):
            token = auth_header.decode().split("Bearer ")[1].strip()

    if not token:
        await websocket.send_text(json.dumps({
            "status": "FAILED",
            "error": "Authorization token missing"
        }))
        await websocket.close()
        return

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        userid = payload.get("userid")
        if not userid:
            raise JWTError("userid missing in token")
    except JWTError as e:
        await websocket.send_text(json.dumps({
            "status": "FAILED",
            "error": f"Invalid token: {str(e)}"
        }))
        await websocket.close()
        return

    conn = None
    temp_file_path = None
    execution_output = ""
    execution_status = "FAILED"
    execution_message = "Unknown error"

    try:
        # ---------------- DB connection ----------------
        conn = await db.get_db_connection()

        # Validate test case access
        tc_project = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1",
            testcase_id
        )
        if not tc_project:
            await websocket.send_text(json.dumps({
                "status": "FAILED",
                "error": "Test case not found"
            }))
            await websocket.close()
            return

        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid,
            tc_project["projectid"]
        )
        if not access:
            await websocket.send_text(json.dumps({
                "status": "FAILED",
                "error": "Unauthorized test case access"
            }))
            await websocket.close()
            return

        # ---------------- BUILD test plan ----------------
        await websocket.send_text(json.dumps({
            "status": "BUILDING_PLAN",
            "log": "Building test plan..."
        }))

        prereq_chain = await utils.get_prereq_chain(conn, testcase_id)

        testplan_dict = {
            "pretestid_steps": {},
            "current_testid": testcase_id,
            "current_bdd_steps": {}
        }

        # Add prereq steps
        for tc_id in prereq_chain[:-1]:
            steps_row = await conn.fetchrow(
                "SELECT steps, args FROM teststep WHERE testcaseid = $1",
                tc_id
            )
            if steps_row and steps_row["steps"]:
                testplan_dict["pretestid_steps"][tc_id] = dict(
                    zip(steps_row["steps"], steps_row["args"])
                )

        # Add current testcase steps
        current_steps = await conn.fetchrow(
            "SELECT steps, args FROM teststep WHERE testcaseid = $1",
            testcase_id
        )
        if current_steps and current_steps["steps"]:
            testplan_dict["current_bdd_steps"] = dict(
                zip(current_steps["steps"], current_steps["args"])
            )

        # Notify that test plan is ready
        await websocket.send_text(json.dumps({
            "status": "PLAN_READY",
            "log": "Test plan ready"
        }))

        # ---------------- SEND TESTPLAN TO CLIENT TO EDIT (NEW) ----------------
        await websocket.send_text(json.dumps({
            "status": "TESTPLAN_READY",
            "log": "Test plan ready for review/editing",
            "testplan": testplan_dict
        }))

        edited_testplan = None
        wait_start = datetime.now()
        EDIT_TIMEOUT_SECONDS = 300

        # Wait for edited testplan or skip
        try:
            while True:
                if (datetime.now() - wait_start).total_seconds() > EDIT_TIMEOUT_SECONDS:
                    await websocket.send_text(json.dumps({
                        "status": "TESTPLAN_EDIT_TIMEOUT",
                        "log": "Timed out waiting for edited testplan; using original"
                    }))
                    break

                try:
                    msg = await websocket.receive_text()
                except:
                    break

                try:
                    data = json.loads(msg)
                except:
                    continue

                action = data.get("action")
                if action == "update_testplan":
                    edited_testplan = data.get("testplan")
                    await websocket.send_text(json.dumps({
                        "status": "TESTPLAN_UPDATED",
                        "log": "Edited testplan received"
                    }))
                    break

                elif action in ("skip_edit", "skip_methods", "continue"):
                    await websocket.send_text(json.dumps({
                        "status": "TESTPLAN_SKIPPED",
                        "log": "Client skipped editing"
                    }))
                    break

        except WebSocketDisconnect:
            utils.logger.warning(f"[MADL-EXEC] Client disconnected while waiting for edited testplan")

        # Validate and choose active plan
        def is_valid_tp(tp):
            return (
                isinstance(tp, dict) and
                "pretestid_steps" in tp and
                "current_bdd_steps" in tp and
                "current_testid" in tp
            )

        if edited_testplan and is_valid_tp(edited_testplan):
            active_testplan = edited_testplan
        else:
            active_testplan = testplan_dict

        # ---------------- MADL SEARCH ----------------
        await websocket.send_text(json.dumps({
            "status": "SEARCHING_MADL",
            "log": "Searching MADL for reusable methods..."
        }))

        reusable_methods = await search_for_reusable_methods(active_testplan)

        if reusable_methods:
            await websocket.send_text(json.dumps({
                "status": "METHODS_FOUND",
                "methods": [
                    {
                        "signature": f"{m.class_name}.{m.method_name}",
                        "intent": m.intent,
                        "match_percentage": m.match_percentage
                    }
                    for m in reusable_methods
                ],
                "log": f"Found {len(reusable_methods)} reusable methods"
            }))
        else:
            await websocket.send_text(json.dumps({
                "status": "NO_MADL_METHODS",
                "log": "No reusable MADL methods found"
            }))

        # ---------------- SCRIPT GENERATION ----------------
        await websocket.send_text(json.dumps({
            "status": "GENERATING",
            "log": "Generating script using AI..."
        }))

        generated_script = await generate_script_with_madl(
            testcase_id=testcase_id,
            script_type=script_type,
            script_lang="python",
            testplan=active_testplan,
            selected_madl_methods=None,
            logger=None
        )

        # ---------------- SCRIPT EXECUTION ----------------
        await websocket.send_text(json.dumps({
            "status": "EXECUTING",
            "log": "Starting execution..."
        }))

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".py", encoding="utf-8"
        ) as tmp:
            tmp.write(generated_script)
            temp_file_path = tmp.name

        process = subprocess.Popen(
            [sys.executable, temp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        while True:
            if process.stdout is None:
                break

            line = process.stdout.readline()
            if not line:
                break

            line = line.rstrip("\n")
            if not line.strip():
                continue

            execution_output += line + "\n"

            await websocket.send_text(json.dumps({
                "status": "RUNNING",
                "log": line
            }))
            await asyncio.sleep(0.01)

        return_code = process.wait()

        if return_code == 0:
            execution_status = "SUCCESS"
            execution_message = "Script executed successfully"
        else:
            execution_status = "FAILED"
            execution_message = f"Script exited with code {return_code}"

        # ---------------- SAVE EXECUTION ----------------
        exeid = await utils.get_next_exeid(conn)
        datestamp = datetime.now().date()
        exetime = datetime.now().time()

        await conn.execute(
            """
            INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            exeid,
            testcase_id,
            script_type,
            datestamp,
            exetime,
            execution_message,
            execution_output,
            execution_status
        )

        # ---------------- OPTIONAL: STORE MADL ----------------
        if execution_status == "SUCCESS":
            try:
                await madl_storage.store_successful_execution_to_madl(
                    testcase_id=testcase_id,
                    generated_script=generated_script,
                    test_plan=active_testplan,
                    execution_logs=execution_output,
                    execution_output=execution_output
                )
            except Exception as e:
                utils.logger.error(f"[MADL] Storage error: {str(e)}")

        # ---------------- FINAL STATUS ----------------
        await websocket.send_text(json.dumps({
            "status": "COMPLETED",
            "final_status": execution_status,
            "log": execution_message
        }))

    except Exception as e:
        utils.logger.error(f"[MADL-EXEC] Unexpected error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({
                "status": "FAILED",
                "error": str(e)
            }))
        except:
            pass

    finally:
        if conn:
            await db.release_db_connection(conn)

        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

        try:
            await websocket.close()
        except:
            pass



@router.websocket("/testcases/{testcase_id}/execute-unified")
async def execute_testcase_unified(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str
):
    """
    Unified endpoint that handles:
    1. Dynamically building test plan from prerequisites and steps
    2. Script generation from test plan
    3. Script execution with auto-healing on failure
    All in one seamless WebSocket flow.
    """
    await websocket.accept()
    utils.logger.debug(f"Unified WebSocket accepted for testcase_id: {testcase_id}, script_type: {script_type}")

    # Extract token from headers
    token = None
    if "headers" in websocket.scope:
        headers = dict(websocket.scope["headers"])
        auth_header = headers.get(b"authorization")
        if auth_header and isinstance(auth_header, bytes) and auth_header.startswith(b"Bearer "):
            token = auth_header.decode().split("Bearer ")[1].strip()
    if not token:
        error_msg = {"error": "Authorization token missing"}
        utils.logger.error(f"Validation failed: {error_msg}")
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return

    # Validate token
    current_user = await utils.validate_token(token)
    if not current_user:
        error_msg = {"error": "Invalid or expired token"}
        utils.logger.error(f"Validation failed: {error_msg}")
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return

    # Initialize database connection
    conn = None
    connection_closed = False
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Validate script_type
        script_type = script_type.lower()
        if script_type not in ["playwright", "selenium"]:
            error_msg = {"error": "Script type must be 'playwright' or 'selenium'"}
            utils.logger.error(f"Validation failed: {error_msg}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True
            return

        # 2. Fetch projectid from testcase
        tc_project = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1",
            testcase_id
        )
        if not tc_project:
            error_msg = {"error": "Test case not found"}
            utils.logger.error(f"Error: {error_msg} for testcase_id: {testcase_id}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True
            return
        project_ids = tc_project["projectid"]

        # 3. Verify user access
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, project_ids
        )
        if not access:
            error_msg = {"error": "You are not authorized for this test case's project"}
            utils.logger.error(f"Error: {error_msg} for userid: {userid}, project_ids: {project_ids}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True
            return

        # Send initial status
        initial_response = {
            "status": "STARTED",
            "log": f"Execution initialized for {testcase_id}"
        }
        await websocket.send_text(json.dumps(initial_response))

        # 4. Build test plan from prerequisites and steps
        build_plan_log = {"status": "BUILDING_PLAN", "log": "Building test plan from prerequisites and steps..."}
        await websocket.send_text(json.dumps(build_plan_log))
        
        try:
            # Get prerequisite chain
            prereq_chain = await utils.get_prereq_chain(conn, testcase_id)
            utils.logger.debug(f"Prerequisite chain: {prereq_chain}")

            # Build categorized result (same logic as GET /testplan endpoint)
            testplan_dict = {
                "pretestid - steps": {},
                "pretestid - scripts": {},
                "current testid": testcase_id,
                "current - bdd steps": {}
            }

            # Process prerequisites
            for tc_id in prereq_chain[:-1]:
                steps_row = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", tc_id)
                if steps_row and steps_row["steps"]:
                    testplan_dict["pretestid - steps"][tc_id] = dict(zip(steps_row["steps"], steps_row["args"]))

                script_row = await conn.fetchrow("SELECT script FROM testscript WHERE testcaseid = $1", tc_id)
                if script_row and script_row["script"]:
                    testplan_dict["pretestid - scripts"][tc_id] = script_row["script"]

            # Current test case steps
            current_steps = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", testcase_id)
            if current_steps and current_steps["steps"]:
                testplan_dict["current - bdd steps"] = dict(zip(current_steps["steps"], current_steps["args"]))

            testplan_json = json.dumps(testplan_dict)
            utils.logger.info(f"[UNIFIED] Test plan built successfully for {testcase_id}")
            
            plan_built_log = {"status": "PLAN_READY", "log": "Test plan built successfully"}
            await websocket.send_text(json.dumps(plan_built_log))
            
        except Exception as e:
            error_msg = {"error": f"Failed to build test plan: {str(e)}"}
            utils.logger.error(f"Plan building error: {str(e)}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True
            return

        # 5. GENERATE SCRIPT
        generation_log = {"status": "GENERATING", "log": "Generating test script using AI..."}
        await websocket.send_text(json.dumps(generation_log))
        
        try:
            generated_script = await generate_script(
                testcase_id=testcase_id,
                script_type=script_type,
                script_lang="python",
                testplan=testplan_dict
            )
            utils.logger.info(f"[UNIFIED] Script generated successfully for {testcase_id}")
            
            generation_complete = {"status": "GENERATED", "log": f"Script generated ({len(generated_script)} bytes)"}
            await websocket.send_text(json.dumps(generation_complete))
        except Exception as e:
            error_msg = {"error": f"Script generation failed: {str(e)}"}
            utils.logger.error(f"Generation error: {str(e)}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True
            return

        
        # 6. EXECUTE with auto-healing (script is not saved, passed directly)
        execution_log = {"status": "EXECUTING", "log": "Starting script execution..."}
        await websocket.send_text(json.dumps(execution_log))

        # Execute directly without database fetch
        import tempfile
        execution_logs = []
        temp_file_path = None
        
        try:
            # Create temp file with generated script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(generated_script)
                temp_file_path = temp_file.name
            
            utils.logger.info(f"[EXEC] Executing generated script: {temp_file_path}")
            
            process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout for unified logging
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1  # Line buffered for real-time output
            )
            
            execution_output = ""
            execution_failed = False
            failure_logs = ""
            
            # Read output line-by-line and send to WebSocket in real-time
            for line in process.stdout:
                line = line.rstrip('\n')
                if line.strip():
                    execution_logs.append(line)
                    execution_output += line + "\n"
                    
                    # Send each log line immediately to WebSocket
                    log_response = {
                        "status": "RUNNING",
                        "log": line
                    }
                    await websocket.send_text(json.dumps(log_response))
                    await asyncio.sleep(0.02)  # Small delay to allow client to process
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code == 0:
                utils.logger.info(f"[EXEC] Script executed successfully for {testcase_id}")
                execution_status = "SUCCESS"
                execution_message = "Script executed successfully"
            else:
                # Execution failed - trigger self-healing
                execution_failed = True
                failure_logs = execution_output
                utils.logger.warning(f"[HEALING] Script failed for {testcase_id}, triggering self-healing...")
                
                try:
                    from app.routers import ai_healing
                    
                    # Send healing status to WebSocket
                    healing_start = {"status": "AUTO_HEALING", "log": "Script execution failed. Starting auto-healing..."}
                    await websocket.send_text(json.dumps(healing_start))
                    
                    healed_response = await ai_healing.self_heal(
                        testplan_output=testplan_json,
                        generated_script=generated_script,
                        execution_logs=failure_logs,
                        screenshot=None,
                        dom_snapshot=None
                    )
                    
                    # Extract healed code
                    healed_code = healed_response.body.decode('utf-8') if hasattr(healed_response, 'body') else str(healed_response)
                    
                    # Send healing complete message
                    healing_complete = {"status": "AUTO_HEALING", "log": "Script healed. Re-executing..."}
                    await websocket.send_text(json.dumps(healing_complete))
                    
                    # Execute healed script
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as healed_file:
                        healed_file.write(healed_code)
                        healed_temp_path = healed_file.name
                    
                    utils.logger.info(f"[HEALING] Executing healed script: {healed_temp_path}")
                    
                    # Stream healed execution output line-by-line
                    healed_process = subprocess.Popen(
                        [sys.executable, healed_temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1
                    )
                    
                    healed_output = ""
                    for line in healed_process.stdout:
                        line = line.rstrip('\n')
                        if line.strip():
                            execution_logs.append(f"[AUTO-HEALED] {line}")
                            healed_output += line + "\n"
                            
                            # Send healed execution logs with AUTO-HEALED tag
                            log_response = {
                                "status": "RUNNING",
                                "log": f"[AUTO-HEALED] {line}"
                            }
                            await websocket.send_text(json.dumps(log_response))
                            await asyncio.sleep(0.02)
                    
                    healed_return_code = healed_process.wait()
                    
                    if healed_return_code == 0:
                        utils.logger.info(f"[HEALING] Healed script executed successfully for {testcase_id}")
                        execution_status = "SUCCESS"
                        execution_message = "[AUTO-HEALED] Script executed successfully after self-healing"
                        execution_output = healed_output
                    else:
                        utils.logger.error(f"[HEALING] Healed script still failed")
                        execution_status = "FAILED"
                        execution_message = "[AUTO-HEALED] Script failed even after self-healing"
                        execution_output = healed_output
                    
                    if 'healed_temp_path' in locals() and os.path.exists(healed_temp_path):
                        os.unlink(healed_temp_path)
                
                except Exception as healing_error:
                    utils.logger.error(f"[HEALING] Self-healing failed: {str(healing_error)}")
                    execution_status = "FAILED"
                    execution_message = f"Script failed and self-healing failed: {str(healing_error)}"
                    execution_output = failure_logs
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Send final status
        final_response = {
            "status": "COMPLETED",
            "log": execution_message
        }
        
        if execution_status == "FAILED":
            final_response["error"] = execution_message
        
        await websocket.send_text(json.dumps(final_response))
        utils.logger.debug(f"Sent completion status: {execution_status}")

        # Save to execution table
        exeid = await utils.get_next_exeid(conn)
        datestamp = datetime.now().date()
        exetime = datetime.now().time()
        await conn.execute(
            """
            INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            exeid, testcase_id, script_type, datestamp, exetime, execution_message, 
            execution_output, execution_status
        )

    except WebSocketDisconnect as e:
        utils.logger.error(f"Client disconnected for testcase {testcase_id}: {str(e)}")
    except HTTPException as e:
        utils.logger.error(f"HTTPException during execution for testcase {testcase_id}: {str(e)}")
        try:
            error_response = {"error": f"Execution failed: {str(e.detail)}", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_response))
        except:
            pass
    except Exception as e:
        utils.logger.error(f"Execution failed for testcase {testcase_id}: {str(e)}")
        try:
            error_response = {"error": f"Execution failed: {str(e)}", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_response))
        except:
            pass
    finally:
        if conn:
            await conn.close()
        if not connection_closed:
            try:
                await websocket.close()
            except:
                pass
        utils.logger.debug("WebSocket connection closed")

@router.websocket("/testcases/{testcase_id}/execute-ws")
async def execute_testcase(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str
):
    await websocket.accept()
    utils.logger.debug(f"WebSocket accepted for testcase_id: {testcase_id}, script_type: {script_type}")

    # Extract token from headers
    token = None
    if "headers" in websocket.scope:
        headers = dict(websocket.scope["headers"])
        auth_header = headers.get(b"authorization")
        if auth_header and isinstance(auth_header, bytes) and auth_header.startswith(b"Bearer "):
            token = auth_header.decode().split("Bearer ")[1].strip()
    if not token:
        error_msg = {"error": "Authorization token missing"}
        utils.logger.error(f"Validation failed: {error_msg}")
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return

    # Validate token
    current_user = await utils.validate_token(token)
    if not current_user:
        error_msg = {"error": "Invalid or expired token"}
        utils.logger.error(f"Validation failed: {error_msg}")
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return

    # Initialize database connection
    conn = None
    connection_closed = False  # Track if we've already closed the connection
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Validate script_type
        script_type = script_type.lower()
        if script_type not in ["playwright", "selenium"]:
            error_msg = {"error": "Script type must be 'playwright' or 'selenium'"}
            utils.logger.error(f"Validation failed: {error_msg}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return

        # 2. Fetch projectid from testcase
        tc_project = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1",
            testcase_id
        )
        if not tc_project:
            error_msg = {"error": "Test case not found"}
            utils.logger.error(f"Error: {error_msg} for testcase_id: {testcase_id}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return
        project_ids = tc_project["projectid"]

        # 3. Verify user access
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, project_ids
        )
        if not access:
            error_msg = {"error": "You are not authorized for this test case's project"}
            utils.logger.error(f"Error: {error_msg} for userid: {userid}, project_ids: {project_ids}")
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return

        # Fetch script (stored as JSON)
        script_row = await conn.fetchrow(
            "SELECT script FROM testscript WHERE testcaseid = $1",
            testcase_id
        )
        if not script_row or not script_row["script"]:
            utils.logger.error(f"No script found for testcase_id: {testcase_id}, script_row: {script_row}")
            error_msg = {"error": "No script found for this test case"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return
        
        script_json = script_row["script"]
        try:
            if isinstance(script_json, str):
                script_data = json.loads(script_json)
            else:
                script_data = script_json
            
            script_obj = script_data.get("script", {})
            script_content_lines = script_obj.get("code", [])
            if not script_content_lines:
                raise ValueError("No 'code' field in script JSON")
            script_content = '\n'.join(line for line in script_content_lines if line.strip())
            utils.logger.debug(f"Retrieved script, extracted content length: {len(script_content)}")
        except json.JSONDecodeError as e:
            utils.logger.error(f"Failed to parse script JSON: {str(e)}")
            error_msg = {"error": f"Invalid script JSON format: {str(e)}"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return
        except ValueError as e:
            utils.logger.error(f"Script JSON error: {str(e)}")
            error_msg = {"error": str(e)}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return
        except Exception as e:
            utils.logger.error(f"Unexpected error processing script JSON: {str(e)}")
            error_msg = {"error": f"Unexpected error: {str(e)}"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            connection_closed = True  # Mark connection as closed
            return

        # Send initial status
        initial_response = {
            "status": "STARTED",
            "log": f"Execution initialized for {testcase_id}"
        }
        await websocket.send_text(json.dumps(initial_response))
        utils.logger.debug("Sent initial status")

        # Execute with auto-healing
        execution_result = await execute_with_auto_healing(
            testcase_id=testcase_id,
            script_type=script_type,
            conn=conn,
            user_id=userid
        )
        
        # Send execution logs line by line
        for log_line in execution_result.get("logs", []):
            if log_line.strip():
                log_response = {
                    "status": "RUNNING",
                    "log": log_line.strip()
                }
                await websocket.send_text(json.dumps(log_response))
                await asyncio.sleep(0.05)
        
        # Send final status
        final_status = "SUCCESS" if execution_result["status"] == "SUCCESS" else "FAILED"
        final_message = execution_result["message"]
        if execution_result.get("healed"):
            final_message = f"[AUTO-HEALED] {final_message}"
        
        final_response = {
            "status": "COMPLETED",
            "log": final_message
        }
        
        if final_status == "FAILED":
            final_response["error"] = final_message
        
        await websocket.send_text(json.dumps(final_response))
        utils.logger.debug(f"Sent completion status: {final_status}")

        # Save to execution table
        exeid = await utils.get_next_exeid(conn)
        datestamp = datetime.now().date()
        exetime = datetime.now().time()
        await conn.execute(
            """
            INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            exeid, testcase_id, script_type, datestamp, exetime, final_message, 
            execution_result.get("output", ""), final_status
        )

    except WebSocketDisconnect as e:
        utils.logger.error(f"Client disconnected for testcase {testcase_id}: {str(e)}")
    except HTTPException as e:
        utils.logger.error(f"HTTPException during execution for testcase {testcase_id}: {str(e)}")
        try:
            error_response = {"error": f"Execution failed: {str(e.detail)}", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_response))
        except:
            pass
    except Exception as e:
        utils.logger.error(f"Execution failed for testcase {testcase_id}: {str(e)}")
        try:
            error_response = {"error": f"Execution failed: {str(e)}", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_response))
        except:
            pass
    finally:
        if conn:
            await conn.close()
        if not connection_closed:
            try:
                await websocket.close()
            except:
                pass
        utils.logger.debug("WebSocket connection closed")

@router.get("/execution", response_model=List[Dict])
async def get_all_execution_logs(current_user: dict = Depends(get_current_any_user)):
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # 1. Get all project IDs the user is assigned to
        user_projects = await conn.fetchrow(
            "SELECT projectid FROM projectuser WHERE userid = $1",
            userid
        )
        if not user_projects or not user_projects["projectid"]:
            return []  # Return empty list if user has no projects

        allowed_project_ids = set(user_projects["projectid"])

        # 2. Get all test case IDs associated with the user's projects
        testcases = await conn.fetch(
            """
            SELECT testcaseid FROM testcase WHERE projectid && $1::varchar[]
            """,
            list(allowed_project_ids)  # Convert set to list for PostgreSQL array
        )

        if not testcases:
            return []  # Return empty list if no test cases are found

        # Extract testcase IDs into a set
        accessible_testcase_ids = {tc["testcaseid"] for tc in testcases}

        # 3. Fetch execution logs for all accessible test cases
        logs = await conn.fetch(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, message, output, status
            FROM execution
            WHERE testcaseid = ANY($1::varchar[])
            ORDER BY datestamp DESC, exetime DESC
            """,
            list(accessible_testcase_ids)  # Pass as PostgreSQL array
        )

        return [dict(log) for log in logs]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching execution logs: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.post("/execute-code")
async def execute_code(file: UploadFile, script_type: str, token: str = Depends(get_current_any_user)):
    try:
        # Validate file
        if not file.filename.endswith((".py", ".java")):
            raise HTTPException(status_code=400, detail="Invalid file format. Use .py or .java")

        # Create temporary file to store uploaded code
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename[-3:]) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Determine language and execution command
        if file.filename.endswith(".py"):
            lang = "python"
            if script_type.lower() not in ["playwright", "selenium"]:
                raise HTTPException(status_code=400, detail="Invalid script_type. Use 'playwright' or 'selenium'")
            # Ensure required libraries are available
            required_libs = {"playwright": "playwright", "selenium": "selenium"}
            try:
                __import__(required_libs[script_type.lower()])
            except ImportError:
                raise HTTPException(status_code=500, detail=f"Missing {script_type} library. Install it first.")
            cmd = ["python", temp_file_path]
        elif file.filename.endswith(".java"):
            lang = "java"
            # Compile and run Java (assumes JDK is installed and class name matches filename without .java)
            class_name = os.path.splitext(file.filename)[0]
            compile_cmd = ["javac", temp_file_path]
            run_cmd = ["java", class_name]
            subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
            cmd = run_cmd
        else:
            raise HTTPException(status_code=500, detail="Unsupported language")

        def generate_logs():
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                output = process.stdout.readline()
                error = process.stderr.readline()
                if output:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    yield f"[{timestamp}] {output.strip()}\n"
                if error:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    yield f"[{timestamp}] ERROR: {error.strip()}\n"
                if process.poll() is not None:
                    break
            # Ensure all remaining output is sent
            for line in process.stdout:
                timestamp = datetime.now().strftime("%H:%M:%S")
                yield f"[{timestamp}] {line.strip()}\n"
            for line in process.stderr:
                timestamp = datetime.now().strftime("%H:%M:%S")
                yield f"[{timestamp}] ERROR: {line.strip()}\n"
            os.unlink(temp_file_path)  # Clean up temporary file

        return StreamingResponse(generate_logs(), media_type="text/plain")

    except HTTPException:
        raise
    except subprocess.CalledProcessError as e:
        utils.logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {e.stderr}")
    except Exception as e:
        utils.logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get("/projects/{project_id}/executions/summary")
async def get_execution_summary(
    project_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_any_user)
):
    """Get summary of last N executions for a project"""
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Verify user has access to project
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND $2 = ANY(projectid)",
            userid, project_id
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not assigned to this project")

        # Get test cases in project
        testcases = await conn.fetch(
            "SELECT testcaseid FROM testcase WHERE $1 = ANY(projectid)",
            project_id
        )
        if not testcases:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "recent_executions": []
            }

        testcase_ids = [tc["testcaseid"] for tc in testcases]

        # Get execution statistics
        stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
            FROM execution
            WHERE testcaseid = ANY($1::varchar[])
            """,
            testcase_ids
        )

        # Get last N executions
        recent = await conn.fetch(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, status, message
            FROM execution
            WHERE testcaseid = ANY($1::varchar[])
            ORDER BY datestamp DESC, exetime DESC
            LIMIT $2
            """,
            testcase_ids, limit
        )

        total = stats["total"] or 0
        successful = stats["successful"] or 0
        failed = stats["failed"] or 0
        success_rate = (successful / total * 100) if total > 0 else 0.0

        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(success_rate, 2),
            "recent_executions": [
                {
                    "exeid": r["exeid"],
                    "testcaseid": r["testcaseid"],
                    "scripttype": r["scripttype"],
                    "datestamp": str(r["datestamp"]),
                    "exetime": str(r["exetime"]),
                    "status": r["status"],
                    "message": r["message"]
                }
                for r in recent
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching execution summary: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/projects/{project_id}/executions/history")
async def get_execution_history(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_any_user)
):
    """Get paginated execution history for a project"""
    conn = None
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]

        # Verify user has access to project
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND $2 = ANY(projectid)",
            userid, project_id
        )
        if not access:
            raise HTTPException(status_code=403, detail="You are not assigned to this project")

        # Get test cases in project
        testcases = await conn.fetch(
            "SELECT testcaseid FROM testcase WHERE $1 = ANY(projectid)",
            project_id
        )
        testcase_ids = [tc["testcaseid"] for tc in testcases] if testcases else []

        if not testcase_ids:
            return {"total": 0, "executions": []}

        # Get total count
        count_result = await conn.fetchval(
            "SELECT COUNT(*) FROM execution WHERE testcaseid = ANY($1::varchar[])",
            testcase_ids
        )

        # Get paginated executions
        executions = await conn.fetch(
            """
            SELECT exeid, testcaseid, scripttype, datestamp, exetime, status, message, output
            FROM execution
            WHERE testcaseid = ANY($1::varchar[])
            ORDER BY datestamp DESC, exetime DESC
            LIMIT $2 OFFSET $3
            """,
            testcase_ids, limit, offset
        )

        return {
            "total": count_result,
            "executions": [
                {
                    "exeid": e["exeid"],
                    "testcaseid": e["testcaseid"],
                    "scripttype": e["scripttype"],
                    "datestamp": str(e["datestamp"]),
                    "exetime": str(e["exetime"]),
                    "status": e["status"],
                    "message": e["message"],
                    "output": e["output"]
                }
                for e in executions
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching execution history: {str(e)}")
    finally:
        if conn:
            await conn.close()
