# SMART STEP DETECTION – works with print("Step 1: ...") style
    import re
    step_pattern = re.compile(r'Step\s+(\d+)[\s:-]*\s*(.+)', re.IGNORECASE)

    detected_steps = []
    for line in execution_output.splitlines():
        match = step_pattern.search(line)
        if match:
            step_num = int(match.group(1))
            message = match.group(2).strip()
            # Detect failure by keywords
            is_fail = any(word in line.lower() for word in ["fail", "error", "timeout", "exception", "assert", "trace", "not found", "could not"])
            status = "FAIL" if is_fail else "PASS"
            detected_steps.append({"num": step_num, "msg": message, "status": status})

    # Also count real logger.step() calls (if any)
    real_steps = [log for log in logger.logs if log.code and log.code.startswith("STEP_")]
    total_steps = max(len(detected_steps), len(real_steps))
    passed = len([s for s in detected_steps if s["status"] == "PASS"]) + len([l for l in real_steps if l.level == LogLevel.SUCCESS.value])
    failed = total_steps - passed

    summary_lines = [
        "",
        "Test Steps Summary",
        "────────────────────",
        f"Total Steps   : {total_steps}",
        f"Passed        : {passed}",
        f"Failed        : {failed}",
    ]

    if failed > 0:
        # Find first failed step
        first_failed = None
        for s in detected_steps:
            if s["status"] == "FAIL":
                first_failed = s
                break

        if first_failed:
            summary_lines.append(f"Failed at Step {first_failed['num']} – \"{first_failed['msg']}\"")
            summary_lines.append(f"Error         : {first_failed['msg']}")
        else:
            # fallback to logger
            for log in real_steps:
                if log.level == LogLevel.ERROR.value:
                    summary_lines.append(f"Failed at Step {log.code.replace('STEP_', '')} – \"{log.message}")
                    summary_lines.append(f"Error         : {log.details.get('error', 'unknown error')}")

    summary_lines.append(f"Overall Status: {'FAILED' if failed > 0}")
    summary_lines.append(f"Overall Status: {failed > 0}")

    # Send summary
    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))
