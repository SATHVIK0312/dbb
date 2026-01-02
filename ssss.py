elif action_type == "RADIO":

    step_lower = step_name.lower()

    # ------------------------------------------------
    # 1. Extract radio value (Y / N)
    # ------------------------------------------------
    match = re.search(r"value\s*=\s*([yn])", step_lower)
    if not match:
        raise RuntimeError("RADIO step must specify value = Y or N")

    radio_value = match.group(1).upper()

    # ------------------------------------------------
    # 2. Resolve frames
    # ------------------------------------------------
    nav_frame, content_frame = resolve_ccs_frames(page)

    # ------------------------------------------------
    # 3. Identify ACTIVE ERBE QUESTION BLOCK
    # ------------------------------------------------
    # erbeQA blocks contain exactly one active question
    questions = content_frame.locator("div.erbeQA")

    q_count = await questions.count()
    if q_count == 0:
        raise RuntimeError("No ERBE question blocks found")

    selected = False

    for i in range(q_count):
        q = questions.nth(i)

        # Skip hidden/inactive questions
        if not await q.is_visible():
            continue

        radios = q.locator("input[type='radio']")

        r_count = await radios.count()
        if r_count == 0:
            continue

        for j in range(r_count):
            radio = radios.nth(j)

            if await radio.is_disabled():
                continue

            value_attr = (await radio.get_attribute("value") or "").upper()

            if value_attr == radio_value:
                await radio.scroll_into_view_if_needed()
                await radio.wait_for(state="visible", timeout=5000)
                await radio.check(force=True)

                logger.info(
                    LogCategory.EXECUTION,
                    f"[PHASE 3] RADIO selected: value={radio_value} in active ERBE question"
                )

                selected = True
                break

        if selected:
            break

    if not selected:
        raise RuntimeError(
            f"Active ERBE radio with value '{radio_value}' not found"
        )
