# ---------------- execute script ---------------------
first_attempt = False
healed_attempt = False
execution_message = ""
execution_output = ""
temp_file_path = None

# announce execution start
await websocket.send_text(json.dumps({
    "status": "EXECUTING",
    "log": "Starting execution..."
}))

try:
    # write script to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmpf:
        tmpf.write(generated_script)
        temp_file_path = tmpf.name

    logger.info(LogCategory.EXECUTION, f"Executing script from {temp_file_path}")

    # ---- run primary script ----
    process = subprocess.Popen(
        [sys.executable, temp_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        line = line.rstrip()
        if not line:
            continue
        execution_output += line + "\n"
        await websocket.send_text(json.dumps({"status": "RUNNING", "log": line}))
        await asyncio.sleep(0.02)

    rc = process.wait()

    if rc == 0:
        logger.success(LogCategory.EXECUTION, "Script executed successfully")
        first_attempt = True
        execution_message = "Script executed successfully"
    else:
        logger.error(LogCategory.EXECUTION, "Script execution failed")
        execution_message = "Script execution failed"

        # ------------- AUTO HEAL -------------
        await websocket.send_text(json.dumps({
            "status": "AUTO_HEALING",
            "log": "Execution failed. Starting auto-healing..."
        }))

        try:
            healed_response = await ai_healing.self_heal(
                testplan_output=testplan_json,
                generated_script=generated_script,
                execution_logs=execution_output
            )

            healed_code = healed_response.body.decode("utf-8") if hasattr(healed_response, "body") else str(healed_response)

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
                if not line:
                    continue
                healed_output += line + "\n"
                await websocket.send_text(json.dumps({"status": "RUNNING", "log": f"[AUTO-HEALED] {line}"}))
                await asyncio.sleep(0.02)

            healed_rc = healed_proc.wait()

            if healed_rc == 0:
                logger.success(LogCategory.HEALING, "Healed script executed successfully")
                healed_attempt = True
                execution_output = healed_output
                execution_message = "[AUTO-HEALED] Execution completed"
            else:
                logger.error(LogCategory.HEALING, "Healed script still failed")
                execution_output = healed_output
                execution_message = "[AUTO-HEALED] Script failed"

        except Exception as he:
            logger.error(LogCategory.HEALING, f"Healing failed: {he}")
            execution_message = f"Healing failed: {he}"

finally:
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.unlink(temp_file_path)
        except:
            pass

# ---------- FINAL STATUS ----------
if first_attempt:
    final_status = "success"
elif healed_attempt:
    final_status = "healed"
else:
    final_status = "fail"

# send final result
await websocket.send_text(json.dumps({
    "status": "COMPLETED",
    "log": execution_message,
    "final_status": final_status,
    "summary": logger.get_summary()
}))

logger.success(LogCategory.INITIALIZATION, "Execution completed")
