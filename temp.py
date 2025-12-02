total_steps = len([log for log in logger.logs if log.code and log.code.startswith("STEP_")])
    passed_steps = len([log for log in logger.logs if log.code and log.code.startswith("STEP_") and log.level == LogLevel.SUCCESS.value])
    failed_steps = total_steps - passed_steps

    summary_lines = [
        "",
        "Test Steps Summary",
        "──────────────────",
        f"Total Steps   : {total_steps}",
        f"Passed        : {passed_steps}",
        f"Failed        : {failed_steps}",
    ]

    if failed_steps > 0:
        for log in reversed(logger.logs):
            if log.code and log.code.startswith("STEP_") and log.level == LogLevel.ERROR.value:
                step_num = log.code.replace("STEP_", "")
                summary_lines.append(f"Failed at     : Step {step_num} – \"{log.message}\"")
                if log.details and "error" in log.details:
                    err = str(log.details["error"])[:120]
                    summary_lines.append(f"Error         : {err}{'...' if len(err) >= 120 else ''}")
                break
        overall = "FAILED"
    else:
        overall = "SUCCESS"

    summary_lines.append(f"Overall Status: {overall}")

    await websocket.send_text(json.dumps({
        "status": "SUMMARY",                     # ← frontend already accepts any string here
        "log": "\n".join(summary_lines)
    }))
