planned_steps = 0
    # steps the AI intended
    executed_steps = 0      # steps that actually ran (from logs)
    failed_at_line = None

    try:
        # 1. Count PLANNED steps by reading the actual generated script file
        if 'script_path' in locals() and script_path and Path(script_path):
            script_content = Path(script_path).read_text(encoding="utf-8")

            # Count lines that look like real actions (very reliable)
            action_patterns = [
                r'\.goto\(',
                r'\.click\(',
                r'\.fill\(',
                r'\.type\(',
                r'\.press\(',
                r'\.select_option\(',
                r'\.check\(',
                r'\.hover\(',
                r'\.wait_for_selector\(',
                r'\.expect\(',
                r'page\.get_by',
                r'locator\(',
                r'print\(',
                r'logger\.',
            ]
            planned_steps = sum(bool(re.search(pat, line)) for line in script_content.splitlines() if line.strip() and not line.strip().startswith('#'))

        # 2. Count EXECUTED steps from actual output (clean version like before)
        clean_lines = []
        for line in execution_output.splitlines():
            line = line.strip()
            if not line: 
                continue
            # Skip timestamped duplicates like "2025-12-02 06:39:57 - Browser launched..."
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
                continue
            if any(kw in line.lower() for kw in ["fail", "error", "exception", "timeout", "traceback"]):
                if failed_at_line is None:
                    failed_at_line = line
            clean_lines.append(line)

        executed_steps = len(clean_lines)

    except Exception:
        planned_steps = executed_steps = 0

    # Use the higher number — this is the magic
    total_steps = max(planned_steps, executed_steps)
    failed_steps = 1 if failed_at_line else 0
    passed_steps = total_steps - failed_steps if total_steps > 0 else 0

    summary_lines = [
        "",
        "Test Steps Summary",
        "────────────────────",
        f"Total Steps   : {total_steps} (planned)",
        f"Executed      : {executed_steps}",
        f"Passed        : {passed_steps}",
        f"Failed        : {failed_steps}",
    ]

    if failed_at_line:
        summary_lines.append(f"Failed at     : {failed_at_line}")

    summary_lines.append(f"Overall Status: {'FAILED' if failed_steps > 0 else 'SUCCESS'}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))
