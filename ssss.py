//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "RADIO":

    step_lower = step_name.lower()

    # answer = 1 or answer = 2
    match = re.search(r"answer\s*=\s*(\d+)", step_lower)
    if not match:
        raise RuntimeError("RADIO step must specify answer = 1 or answer = 2")

    answer_index = match.group(1)

    nav_frame, content_frame = resolve_ccs_frames(page)

    radio_xpath = f"//input[@type='radio' and contains(@id,'answer{answer_index}') and not(@disabled)]"

    clicked = await content_frame.evaluate(
        """(xpath) => {
            const res = document.evaluate(
                xpath,
                document,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                null
            );
            for (let i = 0; i < res.snapshotLength; i++) {
                const el = res.snapshotItem(i);
                if (el && el.offsetParent !== null) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""",
        radio_xpath
    )

    if not clicked:
        raise RuntimeError(f"Radio not clicked using xpath: {radio_xpath}")

    await page.wait_for_timeout(1000)

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully: answer={answer_index}"
    )
