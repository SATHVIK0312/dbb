elif action_type == "RADIO":
    step_lower = step_name.lower()

    # Extract answer number (1 / 2)
    match = re.search(r"answer\s*=\s*(\d+)", step_lower)
    if not match:
        raise RuntimeError("RADIO step must specify answer = 1 or 2")

    answer_index = match.group(1)

    # Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    # STRICT + SAFE locator
    radio = content_frame.locator(
        f"xpath=//input[@type='radio' and contains(@id,'answer{answer_index}') and not(@disabled)]"
    ).filter(has_text="").first

    # Wait until actually usable
    await radio.wait_for(state="visible", timeout=15000)

    # Click safely (NO scroll, NO evaluate)
    if not await radio.is_checked():
        await radio.click(force=True)

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully: answer={answer_index}"
    )
