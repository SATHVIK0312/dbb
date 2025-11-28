# ------------------ START EXECUTION ------------------
await websocket.send_text(json.dumps({
    "status": "EXECUTING",
    "log": "Starting script execution..."
}))

execution_logs = []
temp_file_path = None

try:
    # Write script to a temporary .py file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(generated_script)
        temp_file_path = temp_file.name

    logger.info(LogCategory.EXECUTION, f"Executing script from {temp_file_path}")

    # Launch script subprocess
    process = subprocess.Popen(
        [sys.executable, temp_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line buffered
    )

    execution_output = ""

    # Stream output line-by-line
    for line in process.stdout:
        line = line.rstrip("\n")
        if line.strip():
            execution_logs.append(line)
            execution_output += line + "\n"

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
        logger.error(LogCategory.EXECUTION, "Script execution failed")
        execution_status = "FAILED"
        execution_message = "Script execution failed"

finally:
    if temp_file_path and os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
