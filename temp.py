real_user_steps = 0
    executed_user_steps = 0
    failed_step_line = None

    try:
        # 1. Count REAL user steps from the actual script code
        if 'script_path' in locals() and script_path and Path(script_path).exists():
            content = Path(script_path).read_text(encoding="utf-8")

            # These are the ONLY lines that count as one user step
            user_action_keywords = [
                'page.goto(',
                'page.click(',
                'page.fill(',
                'page.type(',
                'page.press(',
                'page.check(',
                'page.select_option(',
                'page.hover(',
                'login_user(',
                'is_on_products_page(',
                '.expect(',
                'get_by_',
                'locator('
            ]

            for line in content.splitlines():
                if any(kw in line for kw in user_action_keywords):
                    real_user_steps += 1

        # 2. Count how many of those real steps actually ran (from clean logs)
        clean_action_lines = []
        for line in execution_output.splitlines():
            line = line.strip()
            if not line:
                continue
            # Skip timestamped noise
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
                continue
            # Only keep lines that match real actions
            if any(kw.lower() in line.lower() for kw in [
                "navigate", "login", "click", "fill", "type", "enter", "submit",
                "password", "username", "button clicked", "products page"
            ]):
                clean_action_lines.append(line)
                if any(err in line.lower() for err in ["fail", "error", "invalid", "timeout"]):
                    if not failed_step_line:
                        failed_step_line = line

        executed_user_steps = len(clean_action_lines)

    except Exception:
        real_user_steps = executed_user_steps = 0

    # Final truth
    total_steps = real_user_steps or 1
    passed = executed_user_steps if not failed_step_line else (executed_user_steps - 1)
    failed = 1 if failed_step_line else 0

    summary_lines = [
        "",
        "Test Steps Summary",
        "────────────────────",
        f"Total Steps   : {total_steps}",
        f"Executed      : {executed_user_steps}",
        f"Passed        : {passed}",
        f"Failed        : {failed}",
    ]

    if failed_step_line:
        summary_lines.append(f"Failed at     : {failed_step_line}")

    summary_lines.append(f"Overall Status: {'FAILED' if failed else 'SUCCESS'}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))
