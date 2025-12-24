elif "radio button" in step_lower:
    action_type = "RADIO"


elif action_type == "RADIO":

    step_lower = step_name.lower()

    # -----------------------------------------
    # Extract radio value (Y / N)
    # -----------------------------------------
    if "value =" not in step_lower:
        raise RuntimeError("RADIO step missing 'value ='")

    radio_value = (
        step_name
        .split("value =", 1)[1]
        .split(" in the ")[0]
        .strip()
        .strip('"')
        .lower()
    )

    # -----------------------------------------
    # Resolve frames
    # -----------------------------------------
    nav_frame, content_frame = resolve_ccs_frames(page)

    # -----------------------------------------
    # Optional section scoping
    # -----------------------------------------
    section = None
    if " in the " in step_lower:
        section = (
            step_lower
            .split(" in the ", 1)[1]
            .replace("section", "")
            .strip()
        )

    if section:
        section_root = content_frame.locator(
            f"div:has-text('{section.title()}')"
        )
        radio_candidates = section_root.locator("input[type='radio']")
    else:
        radio_candidates = content_frame.locator("input[type='radio']")

    total = await radio_candidates.count()
    if total == 0:
        raise RuntimeError("No radio buttons found")

    selected = False

    # -----------------------------------------
    # CLICK ONLY ACTIVE + VISIBLE RADIO
    # -----------------------------------------
    for i in range(total):
        radio = radio_candidates.nth(i)

        # Skip hidden radios
        if not await radio.is_visible():
            continue

        # Skip disabled radios
        if await radio.is_disabled():
            continue

        value_attr = (await radio.get_attribute("value") or "").lower()

        if value_attr == radio_value:
            await radio.scroll_into_view_if_needed()
            await radio.wait_for(state="visible", timeout=5000)
            await radio.click(force=True)
            await content_frame.wait_for_timeout(300)

            logger.info(
                LogCategory.EXECUTION,
                f"[PHASE 3] RADIO selected successfully: value={radio_value}, section={section}"
            )

            selected = True
            break

    if not selected:
        raise RuntimeError(
            f"No ACTIVE radio button with value '{radio_value}' found"
        )

