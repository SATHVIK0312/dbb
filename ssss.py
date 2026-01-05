//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "RADIO":
    step_lower = step_name.lower()

    # Hard decision
    if "answer = 1" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer1') and not(@disabled)]"
    elif "answer = 2" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]"
    else:
        raise RuntimeError("RADIO step must specify answer = 1 or answer = 2")

    # Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    # HARD DOM CLICK (no scrolling possible)
    clicked = await content_frame.evaluate(
        """
        (xpath) => {
            const result = document.evaluate(
                xpath,
                document,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                null
            );

            for (let i = 0; i < result.snapshotLength; i++) {
                const el = result.snapshotItem(i);
                if (el.offsetParent !== null && !el.disabled) {
                    el.click();
                    return true;
                }
            }
            return false;
        }
        """,
        radio_xpath
    )

    if not clicked:
        raise RuntimeError(f"Radio not clicked using xpath: {radio_xpath}")

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO clicked successfully via HARD XPath"
    )

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO clicked HARD via ID: {radio_id}"
    )
