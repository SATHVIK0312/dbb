"""
Enhanced Execution Router with MADL Integration
Incorporates MADL search, method selection, enhanced logging, and error context.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Form
from typing import List, Dict, Any, Optional
import json
import subprocess
import tempfile
import os
import asyncio
import sys
from datetime import datetime
from azure_openai_client import call_openai_api

import models as models
import utils
import database as db
import config
from routers.users import get_current_any_user
from routers.madl_integration import madl_client, search_for_reusable_methods
from routers.madl_storage import store_successful_execution_to_madl
from routers.structured_logging import StructuredLogger, LogLevel, LogCategory, extract_madl_from_logs
from routers import ai_healing

router = APIRouter()

async def generate_script_with_madl(
    testcase_id: str,
    script_type: str,
    script_lang: str,
    testplan: dict,
    selected_madl_methods: Optional[List[dict]] = None,
    logger: Optional[StructuredLogger] = None
):
    """
    Generate test script using Azure OpenAI API with MADL method integration.

    Enhanced to:
    - Include selected MADL methods in prompt
    - Strip markdown code fences (\`\`\`python ... \`\`\`) from the model output
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

        raw_text = call_openai_api(
            prompt=prompt,
            max_tokens=4000,
            system_message="You are a test automation expert. Generate only executable Python code with no markdown."
        ).strip()

        if not raw_text:
            raise ValueError("Azure OpenAI returned empty script content")

        # ---- CLEAN MARKDOWN CODE FENCES ----
        script_content = raw_text
        if "\`\`\`" in raw_text:
            # split on fences
            parts = raw_text.split("\`\`\`")
            # typical structure: 0: before, 1: "python\ncode...", 2: after
            if len(parts) >= 2:
                code_block = parts[1]

                # remove optional language tag on first line
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


@router.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str
):
    """
    Enhanced execution endpoint with MADL integration
    
    Flow:
    1. Build test plan
    2. Search MADL for reusable methods
    3. Wait for user to select methods (via dialog)
    4. Generate script with selected methods
    5. Execute with structured logging
    6. On failure: collect context and self-heal
    7. On success: extract MADL data and push to vector DB
    """
    await websocket.accept()
    utils.logger.debug(f"[MADL-EXEC] WebSocket opened for {testcase_id}, {script_type}")
    
    # Extract token
    token = None
    if "headers" in websocket.scope:
        headers = dict(websocket.scope["headers"])
        auth_header = headers.get(b"authorization")
        if auth_header and isinstance(auth_header, bytes) and auth_header.startswith(b"Bearer "):
            token = auth_header.decode().split("Bearer ")[1].strip()
    
    if not token:
        await websocket.send_text(json.dumps({"error": "Authorization token missing", "status": "FAILED"}))
        await websocket.close()
        return
    
    # Validate token
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        userid = payload.get("userid")
        role = payload.get("role")
        current_user = {"userid": userid, "role": role}
    except JWTError:
        await websocket.send_text(json.dumps({"error": "Invalid token", "status": "FAILED"}))
        await websocket.close()
        return
    
    conn = None
    logger = StructuredLogger(testcase_id)
    
    try:
        conn = await db.get_db_connection()
        userid = current_user["userid"]
        
        # Initialize logger
        logger.info(LogCategory.INITIALIZATION, f"Execution started for {testcase_id}")
        
        # Validate and fetch test case
        tc_project = await conn.fetchrow("SELECT projectid FROM testcase WHERE testcaseid = $1", testcase_id)
        if not tc_project:
            error_msg = {"error": "Test case not found", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            return
        
        # Verify access
        access = await conn.fetchrow(
            "SELECT 1 FROM projectuser WHERE userid = $1 AND projectid && $2",
            userid, tc_project["projectid"]
        )
        if not access:
            error_msg = {"error": "Unauthorized", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            return
        
        # Build test plan
        await websocket.send_text(json.dumps({"status": "BUILDING_PLAN", "log": "Building test plan..."}))
        logger.info(LogCategory.PLAN_BUILDING, "Building test plan from prerequisites and steps")
        
        prereq_chain = await utils.get_prereq_chain(conn, testcase_id)
        testplan_dict = {
            "pretestid - steps": {},
            "pretestid - scripts": {},
            "current testid": testcase_id,
            "current - bdd steps": {}
        }
        
        for tc_id in prereq_chain[:-1]:
            steps_row = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", tc_id)
            if steps_row and steps_row["steps"]:
                testplan_dict["pretestid - steps"][tc_id] = dict(zip(steps_row["steps"], steps_row["args"]))
        
        current_steps = await conn.fetchrow("SELECT steps, args FROM teststep WHERE testcaseid = $1", testcase_id)
        if current_steps and current_steps["steps"]:
            testplan_dict["current - bdd steps"] = dict(zip(current_steps["steps"], current_steps["args"]))
        
        testplan_json = json.dumps(testplan_dict)
        await websocket.send_text(json.dumps({"status": "PLAN_READY", "log": "Test plan built"}))
        logger.success(LogCategory.PLAN_BUILDING, "Test plan built successfully")
        
        # Search MADL for reusable methods
        await websocket.send_text(json.dumps({"status": "SEARCHING_MADL", "log": "Searching for reusable methods..."}))
        logger.info(LogCategory.SEARCH, "Searching MADL for reusable methods")
        
        reusable_methods = await search_for_reusable_methods(testplan_dict)
        
        if reusable_methods:
            methods_data = [
                {
                    "signature": f"{m.class_name}.{m.method_name}",
                    "intent": m.intent,
                    "match_percentage": m.match_percentage,
                    "example": m.example
                }
                for m in reusable_methods
            ]
            
            logger.success(LogCategory.SEARCH, f"Found {len(methods_data)} reusable methods")
            
            # Send methods to client for user selection
            await websocket.send_text(json.dumps({
                "status": "METHODS_FOUND",
                "methods": methods_data,
                "message": f"Found {len(methods_data)} reusable methods. Select which to use:"
            }))
            
            # Wait for user selection (timeout after 60 seconds)
            selected_methods = []
            try:
                selection_msg = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                selection_data = json.loads(selection_msg)
                
                if selection_data.get("action") == "confirm_selection":
                    selected_signatures = selection_data.get("selected_methods", [])
                    selected_methods = [m for m in methods_data if m["signature"] in selected_signatures]
                    logger.info(LogCategory.SEARCH, f"User selected {len(selected_methods)} methods")
                    
                    await websocket.send_text(json.dumps({
                        "status": "SELECTION_CONFIRMED",
                        "count": len(selected_methods)
                    }))
            
            except asyncio.TimeoutError:
                logger.warning(LogCategory.SEARCH, "Method selection timeout")
                await websocket.send_text(json.dumps({
                    "status": "SELECTION_TIMEOUT",
                    "log": "No selection received, proceeding without MADL methods"
                }))
        
        else:
            logger.info(LogCategory.SEARCH, "No reusable methods found")
            await websocket.send_text(json.dumps({
                "status": "NO_MADL_METHODS",
                "log": "No reusable methods found in MADL"
            }))
        
        # Generate script (with selected MADL methods if any)
        await websocket.send_text(json.dumps({"status": "GENERATING", "log": "Generating script..."}))
        
        try:
            generated_script = await generate_script_with_madl(
                testcase_id=testcase_id,
                script_type=script_type,
                script_lang="python",
                testplan=testplan_dict,
                selected_madl_methods=selected_methods if 'selected_methods' in locals() else None,
                logger=logger
            )
        
        except Exception as e:
            error_msg = {"error": f"Generation failed: {str(e)}", "status": "FAILED"}
            await websocket.send_text(json.dumps(error_msg))
            await websocket.close()
            return
        
        # Execute script with structured logging
        await websocket.send_text(json.dumps({"status": "EXECUTING", "log": "Starting execution..."}))
        
        execution_output = ""
        temp_file_path = None
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(generated_script)
                temp_file_path = temp_file.name
            
            logger.info(LogCategory.EXECUTION, f"Executing script from {temp_file_path}")
            
            process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            for line in process.stdout:
                line = line.rstrip('\n')
                if line.strip():
                    execution_output += line + "\n"
                    
                    # Stream log to client
                    await websocket.send_text(json.dumps({
                        "status": "RUNNING",
                        "log": line
                    }))
                    await asyncio.sleep(0.02)
            
            return_code = process.wait()
            
            if return_code == 0:
                logger.success(LogCategory.EXECUTION, "Script executed successfully")
                execution_status = "SUCCESS"
                execution_message = "Script executed successfully"
            
            else:
                # Collect error context for healing
                logger.error(LogCategory.EXECUTION, "Script execution failed")
                error_context = await collect_enhanced_error_context(
                    logs=execution_output,
                    testplan=testplan_json,
                    generated_script=generated_script
                )
                
                # Trigger self-healing
                await websocket.send_text(json.dumps({
                    "status": "AUTO_HEALING",
                    "log": "Execution failed. Starting auto-healing with context..."
                }))
                logger.info(LogCategory.HEALING, "Initiating auto-healing")
                
                try:
                    healed_response = await ai_healing.self_heal(
                        testplan_output=testplan_json,
                        generated_script=generated_script,
                        execution_logs=execution_output,
                        screenshot=None,
                        dom_snapshot=None
                    )
                    
                    healed_code = healed_response.body.decode('utf-8') if hasattr(healed_response, 'body') else str(healed_response)
                    
                    # Execute healed script
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as healed_file:
                        healed_file.write(healed_code)
                        healed_temp_path = healed_file.name
                    
                    logger.info(LogCategory.HEALING, "Executing healed script")
                    
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
                            healed_output += line + "\n"
                            await websocket.send_text(json.dumps({
                                "status": "RUNNING",
                                "log": f"[AUTO-HEALED] {line}"
                            }))
                            await asyncio.sleep(0.02)
                    
                    healed_return_code = healed_process.wait()
                    
                    if healed_return_code == 0:
                        logger.success(LogCategory.HEALING, "Healed script executed successfully")
                        execution_status = "SUCCESS"
                        execution_message = "[AUTO-HEALED] Script executed successfully"
                        execution_output = healed_output
                    
                    else:
                        logger.error(LogCategory.HEALING, "Healed script still failed")
                        execution_status = "FAILED"
                        execution_message = "[AUTO-HEALED] Script failed even after healing"
                        execution_output = healed_output
                    
                    if 'healed_temp_path' in locals() and os.path.exists(healed_temp_path):
                        os.unlink(healed_temp_path)
                
                except Exception as healing_error:
                    logger.error(LogCategory.HEALING, f"Healing failed: {str(healing_error)}")
                    execution_status = "FAILED"
                    execution_message = f"Healing failed: {str(healing_error)}"
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Store execution
        exeid = await utils.get_next_exeid(conn)
        datestamp = datetime.now().date()
        exetime = datetime.now().time()
        
        await conn.execute(
            """
            INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            exeid, testcase_id, script_type, datestamp, exetime, execution_message, execution_output, execution_status
        )
        
        # If successful, extract MADL data and push to vector DB
        if execution_status == "SUCCESS":
            logger.info(LogCategory.STORAGE, "Extracting MADL data from successful execution")
            
            try:
                # Store to MADL for future reuse
                storage_success = await store_successful_execution_to_madl(
                    testcase_id=testcase_id,
                    generated_script=generated_script,
                    test_plan=testplan_dict,
                    execution_logs=logger.logs,
                    execution_output=execution_output
                )
                
                if storage_success:
                    logger.success(LogCategory.STORAGE, "Successfully stored to MADL vector DB")
                    await websocket.send_text(json.dumps({
                        "status": "STORAGE_SUCCESS",
                        "log": "Script stored to MADL for future reuse"
                    }))
                else:
                    logger.warning(LogCategory.STORAGE, "Failed to store to MADL")
            
            except Exception as e:
                logger.error(LogCategory.STORAGE, f"MADL storage error: {str(e)}")
        
        # Send final status
        await websocket.send_text(json.dumps({
            "status": "COMPLETED",
            "log": execution_message,
            "final_status": execution_status,
            "summary": logger.get_summary()
        }))
        
        logger.success(LogCategory.INITIALIZATION, "Execution completed")
    
    except WebSocketDisconnect:
        logger.warning(LogCategory.INITIALIZATION, "Client disconnected")
    except Exception as e:
        logger.error(LogCategory.INITIALIZATION, f"Unexpected error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({"error": str(e), "status": "FAILED"}))
        except:
            pass
    
    finally:
        if conn:
            await conn.close()
        try:
            await websocket.close()
        except:
            pass
        
        # Log summary
        utils.logger.info(f"[EXEC] Execution finished for {testcase_id}")
        utils.logger.debug(f"[EXEC] Final logs:\n{logger.get_readable_logs()}")
