# ────────────────────── SMART STEP SUMMARY (FIXED) ──────────────────────
    import re
    step_pattern = re.compile(r'Step\s+(\d+)[\s:-]*\s*(.+)', re.IGNORECASE)

    detected_steps = []
    for line in execution_output.splitlines():
        match = step_pattern.search(line)
        if match:
            step_num = int(match.group(1))
            message = match.group(2).strip()
            is_fail = any(word in line.lower() for word in ["fail", "error", "timeout", "exception", "assert", "not found", "could not"])
            status = "FAIL" if is_fail else "PASS"
            detected_steps.append({"num": step_num, "msg": message, "status": status})

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
        # Find first failed step from print() output
        first_failed = next((s for s in detected_steps if s["status"] == "FAIL"), None)
        if first_failed:
            summary_lines.append(f"Failed at     : Step {first_failed['num']} – \"{first_failed['msg']}\"")
        else:
            # Fallback to StructuredLogger steps
            for log in reversed(real_steps):
                if log.level == LogLevel.ERROR.value:
                    num = log.code.replace("STEP_", "")
                    summary_lines.append(f"Failed at     : Step {num} – \"{log.message}\"")
                    if log.details and "error" in log.details:
                        err = str(log.details["error"])[:120]
                        summary_lines.append(f"Error         : {err}{'...' if len(str(log.details["error"])) > 120 else ''}")
                    break

        overall_status = "FAILED"
    else:
        overall_status = "SUCCESS"

    summary_lines.append(f"Overall Status: {overall_status}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",
        "log": "\n".join(summary_lines)
    }))
