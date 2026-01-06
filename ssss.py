//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "RADIO":
    step_lower = step_name.lower()

    print("I found the radio button")
    logger.info(
        LogCategory.EXECUTION,
        "[PHASE 3] RADIO step detected"
    )

    # ----------------------------
    # Hard decision based on step
    # ----------------------------
    if "answer = 1" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer1') and not(@disabled)]"
    elif "answer = 2" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]"
    else:
        raise RuntimeError("RADIO step must specify answer = 1 or answer = 2")

    # ----------------------------
    # HARD CLICK – NO SCROLL, NO FRAME, NO WAIT
    # ----------------------------
    radio = page.locator(f"xpath={radio_xpath}").first

    await radio.wait_for(state="attached", timeout=10000)
    await radio.click(force=True)

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO clicked successfully using xpath: {radio_xpath}"
    )

    continue
