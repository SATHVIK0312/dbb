//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "RADIO":

    step_lower = step_name.lower()

    # Decide XPath ONLY
    if "answer = 1" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer1') and not(@disabled)]"
    elif "answer = 2" in step_lower:
        radio_xpath = "//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]"
    else:
        raise RuntimeError("RADIO step must specify answer = 1 or answer = 2")

    # 🚫 NO frames
    # 🚫 NO locators
    # 🚫 NO scroll
    # 🚫 NO wait_for

    clicked = await page.evaluate(
        """
        (xpath) => {
            const res = document.evaluate(
                xpath,
                document,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                null
            );
            for (let i = 0; i < res.snapshotLength; i++) {
                const el = res.snapshotItem(i);
                if (el && el.offsetParent !== null && !el.disabled) {
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
        f"[PHASE 3] RADIO clicked successfully using xpath: {radio_xpath}"
    )

    # 🚀 MOVE TO NEXT STEP IMMEDIATELY
    continue

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully: answer={answer_index}"
    )
