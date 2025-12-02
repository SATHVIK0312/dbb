import re
    from pathlib import Path

    real_user_steps = 0
    executed_user_steps = 0
    failed_step_line = None

    try:
        if 'script_path' in locals() and script_path and Path(script_path).exists():
            content = Path(script_path).read_text(encoding="utf-8")
            user_action_keywords = [
                'page.goto(', 'page.click(', 'page.fill(', 'page.type(',
                'page.press(', 'page.check(', 'page.select_option(',
                'page.hover(', 'login_user(', 'is_on_products_page(',
                '.expect(', 'get_by_', 'locator('
            ]
            for line in content.splitlines():
                if any(kw in line for kw in user_action_keywords):
                    real_user_steps += 1

        clean_action_lines = []
        for line in execution_output.splitlines():
            line = line.strip()
            if not line or re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
                continue
            if any(kw.lower() in line.lower() for kw in ["navigate","login","click","fill","type","enter","submit","password","username","button clicked","products page"]):
                clean_action_lines.append(line)
                if any(err in line.lower() for err in ["fail","error","invalid","timeout"]):
                    if not failed_step_line:
                    failed_step_line = line

        executed_user_steps = len(clean_action_lines)

    except Exception:
        real_user_steps = executed_user_steps = 0

    # FIXED MATH — THIS IS THE ONLY PART THAT CHANGED
    total_steps = real_user_steps or 1
    failed_steps = 1 if failed_step_line else 0
    passed_steps = total_steps - failed_steps

    # Make sure nothing goes negative or over total
    passed_steps = max(0, passed_steps)
    failed_steps = min(failed_steps, total_steps)

    summary_lines = [
        "",
        "Test Steps Summary",
        "────────────────────",
        f"Total Steps   : {total_steps}",
        f"Executed      : {executed_user_steps}",
        f"Passed        : {passed_steps}",
        f"Failed        : {failed_steps}",
    ]

    if failed_step_line:
        summary_lines.append(f"Failed at     : {failed_step_line}")

    summary_lines.append(f"Overall Status: {'FAILED' if failed_steps > 0 else 'SUCCESS'}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))
