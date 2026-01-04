//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "RADIO":
    step_lower = step_name.lower()

    # HARD extract answer
    if "answer = 1" in step_lower:
        radio_id = "claimsPageForm.erbeAnswerPanelData.answer1"
    elif "answer = 2" in step_lower:
        radio_id = "claimsPageForm.erbeAnswerPanelData.answer2"
    else:
        raise RuntimeError("RADIO step must specify answer = 1 or answer = 2")

    # Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    # HARD XPath
    radio_xpath = f"//input[@id='{radio_id}']"

    # HARD DOM CLICK — NO SCROLL, NO WAIT, NO PLAYWRIGHT CLICK
    clicked = await content_frame.evaluate(
        """
        (xp) => {
            const r = document.evaluate(
                xp,
                document,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null
            ).singleNodeValue;

            if (!r) return false;
            if (r.disabled) return false;
            if (r.checked) return true;

            r.click();
            return true;
        }
        """,
        radio_xpath
    )

    if not clicked:
        raise RuntimeError(f"Failed to click radio with id {radio_id}")

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO clicked HARD via ID: {radio_id}"
    )
