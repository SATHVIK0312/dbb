elif action_type == "RADIO":

    step_lower = step_name.lower()

    # -----------------------------------------
    # 1. Extract answer index (answer = 1 / 2)
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
    # 3. Locate radio by ID suffix (NO SCROLL)
    # -----------------------------------------
    radio = content_frame.locator(
        f"input[type='radio'][id$='answer{answer_index}']"
    )

    if await radio.count() == 0:
        raise RuntimeError(
            f"Radio with id ending 'answer{answer_index}' not found"
        )

    radio = radio.first

    # -----------------------------------------
    # 4. HARD DOM CLICK (NO SCROLL, NO STABILITY WAIT)
    # -----------------------------------------
    await content_frame.evaluate(
        """(el) => {
            el.click();
        }""",
        await radio.element_handle()
    )

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully via DOM click: answer={answer_index}"
    )
