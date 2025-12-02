    if first_attempt:
        final_status = "success"
    else:
        final_status = "fail"

    # THE ONE AND ONLY CORRECT WAY — COUNT REAL USER ACTIONS IN THE SCRIPT
    import re
    from pathlib import Path

    real_total_steps = 0
    executed_steps = 0
    failed_at_line = None

    try:
        # 1. Count REAL user steps by looking at actual Playwright actions in the script
        if 'script_path' in locals() and script_path and Path(script_path).exists():
            content = Path(script_path).read_text(encoding="utf-8")

            # These are the lines that represent ONE real user step
            real_step_keywords = [
                'page.goto(', 'page.click(', 'page.fill(', 'page.type(',
                'page.press(', 'page.check(', 'page.select_option(',
                'page.hover(', 'page.wait_for_selector(',
                '.expect(', 'get_by_', 'locator(',
                'login_user(', 'is_on_products_page('   # your helper methods too!
            ]

            for line in content.splitlines():
                if any(keyword in line for keyword in real_step_keywords):
                    real_total_steps += 1

        # 2. Count executed clean log lines (non-timestamped)
        clean_lines = []
        for line in execution_output.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
                continue  # skip timestamped duplicates
            if any(word in line.lower() for word in ["fail", "error", "timeout", "exception"]):
                if not failed_at_line:
                    failed_at_line = line
            clean_lines.append(line)

        executed_steps = len(clean_lines)

    except Exception:
        real_total_steps = executed_steps = 0

    # Final numbers
    total_steps = real_total_steps or executed_steps or 1
    passed_steps = executed_steps - (1 if failed_at_line else 0)
    failed_steps = 1 if failed_at_line else 0

    summary_lines = [
        "",
        "Test Steps Summary",
        "────────────────────",
        f"Total Steps   : {total_steps}",
        f"Executed      : {executed_steps}",
        f"Passed        : {passed_steps}",
        f"Failed        : {failed_steps}",
    ]

    if failed_at_line:
        summary_lines.append(f"Failed at     : {failed_at_line}")

    summary_lines.append(f"Overall Status: {'FAILED' if failed_steps else 'SUCCESS'}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))

    return {
        "status": final_status,
        "script_path": script_path if 'script_path' in locals() else None,
        "output": execution_output,
        "logs": execution_logs,
        "execution_message": execution_message
    }
