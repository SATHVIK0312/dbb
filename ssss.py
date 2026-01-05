//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]
//input[@id='claimsPageForm.erbeAnswerPanelData.answer2']


elif action_type == "BUTTON":
    if "name =" not in step_name:
        raise RuntimeError("BUTTON step missing button name")

    step_lower = step_name.lower()
    button_name = step_name.split("name =")[-1].strip().lower()

    nav_frame, content_frame = resolve_ccs_frames(page)

    clicked = await content_frame.evaluate(
        """
        (buttonName) => {
            const buttons = Array.from(
                document.querySelectorAll("input[type='button'], input[type='submit'], button")
            );

            const btn = buttons.find(b => {
                const txt = (b.innerText || "").toLowerCase();
                const val = (b.value || "").toLowerCase();
                return (
                    (txt.includes(buttonName) || val.includes(buttonName)) &&
                    !b.disabled &&
                    b.offsetParent !== null
                );
            });

            if (!btn) return false;

            btn.click();
            return true;
        }
        """,
        button_name
    )

    if not clicked:
        raise RuntimeError(f"Button '{button_name}' not clicked")

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] BUTTON clicked safely via DOM: {button_name}"
    )

    # Allow CCS transition
    await content_frame.wait_for_timeout(800)
