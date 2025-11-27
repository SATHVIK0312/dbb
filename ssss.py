@app.websocket("/testcases/{testcase_id}/execute-with-madl")
async def execute_testcase_with_madl(
    websocket: WebSocket,
    testcase_id: str,
    script_type: str
):
    await websocket.accept()
    logger = StructuredLogger(testcase_id)
    logger.info(LogCategory.INITIALIZATION, f"Execution started: {testcase_id} | {script_type}")

    conn = None
    try:
        # === Extract & Validate JWT (exactly as before) ===
        token = None
        for k, v in websocket.scope.get("headers", []):
            if k == b"authorization":
                try:
                    token = v.decode().split("Bearer ")[1].strip()
                except:
                    pass
                break

        if not token:
            await websocket.send_text(json.dumps({"error": "Missing token", "status": "FAILED"}))
            return

        from jose import jwt, JWTError
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            userid = payload.get("userid")
        except JWTError:
            await websocket.send_text(json.dumps({"error": "Invalid token", "status": "FAILED"}))
            return

        # === DB Connection & Access Check ===
        conn = await db.get_db_connection()

        tc_row = await conn.fetchrow(
            "SELECT projectid FROM testcase WHERE testcaseid = $1", testcase_id
        )
        if not tc_row:
            await websocket.send_text(json.dumps({"error": "Test case not found", "status": "FAILED"}))
            return

        user_projects = await conn.fetchval(
            "SELECT projectid FROM projectuser WHERE userid = $1", userid
        )
        user_projects = set(from_json(user_projects)) if user_projects else set()
        tc_projects = set(from_json(tc_row["projectid"]))

        if not (user_projects & tc_projects):
            await websocket.send_text(json.dumps({"error": "Unauthorized", "status": "FAILED"}))
            return

        # === Build Test Plan ===
        await websocket.send_text(json.dumps({"status": "BUILDING_PLAN", "log": "Building test plan..."}))

        prereq_chain = await utils.get_prereq_chain(conn, testcase_id)
        testplan = {"pretestid_steps": {}, "current_bdd_steps": {}}

        for tid in prereq_chain[:-1]:
            row = await conn.fetchrow(
                "SELECT steps, args FROM teststep WHERE testcaseid = $1", tid
            )
            if row and row["steps"]:
                testplan["pretestid_steps"][tid] = dict(zip(from_json(row["steps"]), from_json(row["args"])))

        current_row = await conn.fetchrow(
            "SELECT steps, args FROM teststep WHERE testcaseid = $1", testcase_id
        )
        if current_row and current_row["steps"]:
            testplan["current_bdd_steps"] = dict(zip(from_json(current_row["steps"]), from_json(current_row["args"])))

        testplan_json = json.dumps(testplan, indent=2)
        await websocket.send_text(json.dumps({"status": "PLAN_READY", "log": "Test plan built"}))

        # === Generate Script using Azure OpenAI (no MADL) ===
        await websocket.send_text(json.dumps({"status": "GENERATING", "log": "Generating script..."}))

        prompt = f"""
Generate a complete, executable Python {script_type} test script for test case {testcase_id}.

Prerequisites:
{json.dumps(testplan["pretestid_steps"], indent=2)}

Current steps:
{json.dumps(testplan["current_bdd_steps"], indent=2)}

Requirements:
- Use sync API
- Wrap every action in try/except
- Print before: "Running action: <step> at <timestamp>"
- Print after: "Action completed: <step> at <timestamp>"
- On error: print "Action <step> failed due to: <error>"
- Save screenshot → error_screenshot.png
- Save DOM → page_dom_dump.txt
- Output ONLY raw Python code. No markdown, no explanations.
"""

        client = get_azure_openai_client()
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000,
            timeout=300
        )

        raw_script = response.choices[0].message.content.strip()
        script = raw_script
        if "```" in raw_script:
            parts = raw_script.split("```")
            if len(parts) >= 3:
                script = parts[2].strip()
            elif "python" in parts[1]:
                script = parts[1].split("python", 1)[-1].strip()
            else:
                script = parts[1].strip()

        # === Execute Script ===
        await websocket.send_text(json.dumps({"status": "EXECUTING", "log": "Running script..."}))

        temp_path = None
        execution_output = ""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script)
                temp_path = f.name

            process = subprocess.Popen(
                [sys.executable, temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                line = line.rstrip()
                if line:
                    execution_output += line + "\n"
                    await websocket.send_text(json.dumps({"status": "RUNNING", "log": line}))
                await asyncio.sleep(0.01)

            return_code = process.wait()

            if return_code == 0:
                status = "SUCCESS"
                message = "Script executed successfully"
            else:
                # === Auto-Healing ===
                await websocket.send_text(json.dumps({"status": "AUTO_HEALING", "log": "Healing..."}))
                logger.info(LogCategory.HEALING, "Self-healing triggered")

                healed_code = await ai_healing.self_heal(
                    testplan_output=testplan_json,
                    generated_script=script,
                    execution_logs=execution_output,
                    screenshot=None,
                    dom_snapshot=None
                )

                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(healed_code)
                    healed_path = f.name

                healed_process = subprocess.Popen(
                    [sys.executable, healed_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                healed_output = ""
                for line in healed_process.stdout:
                    line = line.rstrip()
                    if line:
                        healed_output += line + "\n"
                        await websocket.send_text(json.dumps({"status": "RUNNING", "log": f"[HEALED] {line}"}))
                    await asyncio.sleep(0.01)

                healed_rc = healed_process.wait()
                os.unlink(healed_path)

                if healed_rc == 0:
                    status = "SUCCESS"
                    message = "Healed & passed"
                    execution_output = healed_output
                else:
                    status = "FAILED"
                    message = "Healing failed"
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        # === Save Execution Result ===
        exeid = await utils.get_next_exeid(conn)
        await conn.execute("""
            INSERT INTO execution 
            (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, exeid, testcase_id, script_type, datetime.now().date(), datetime.now().time(),
           message, execution_output, status)

        # === Final Message (exact same format) ===
        await websocket.send_text(json.dumps({
            "status": "COMPLETED",
            "final_status": status,
            "log": message
        }))

        logger.success(LogCategory.INITIALIZATION, "Execution completed")

    except WebSocketDisconnect:
        logger.warning(LogCategory.INITIALIZATION, "Client disconnected")
    except Exception as e:
        logger.error(LogCategory.INITIALIZATION, f"Error: {e}")
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
