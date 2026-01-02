elif action_type == "RADIO":

    step_lower = step_name.lower()

    # -----------------------------------------
    # 1. Extract answer index (1 / 2 / 3...)
    # -----------------------------------------
    match = re.search(r"answer\s*=\s*(\d+)", step_lower)
    if not match:
        raise RuntimeError("RADIO step must specify answer = <number>")

    answer_index = match.group(1)

    # -----------------------------------------
    # 2. Resolve frames
    # -----------------------------------------
    nav_frame, content_frame = resolve_ccs_frames(page)

    # -----------------------------------------
    # 3. Build radio selector by ID suffix
    # -----------------------------------------
    # Matches: claimsPageForm.erbeAnswerPanelData.answer2
    radio = content_frame.locator(
        f"input[type='radio'][id$='answer{answer_index}']"
    )

    count = await radio.count()
    if count == 0:
        raise RuntimeError(
            f"Radio with id ending 'answer{answer_index}' not found"
        )

    radio = radio.first

    # -----------------------------------------
    # 4. Click safely
    # -----------------------------------------
    await radio.scroll_into_view_if_needed()
    await radio.wait_for(state="visible", timeout=10000)

    if not await radio.is_checked():
        await radio.check(force=True)

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully: answer={answer_index}"
    )
