//input[@type='radio' and contains(@id,'answer2') and not(@disabled)]


elif action_type == "RADIO":
    step_lower = step_name.lower()

    # 1. Extract answer number
    match = re.search(r"answer\s*=\s*(\d+)", step_lower)
    if not match:
        raise RuntimeError("RADIO step must specify answer = 1 or 2")

    answer_index = match.group(1)

    # 2. Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    # 3. DOM-level click (NO scroll, NO Playwright click)
    clicked = await content_frame.evaluate(
        """
        (answerIndex) => {
            const radios = Array.from(
                document.querySelectorAll(
                    `input[type='radio'][id*='answer${answerIndex}']`
                )
            );

            // Only visible & enabled radios
            const radio = radios.find(r =>
                r.offsetParent !== null && !r.disabled
            );

            if (!radio) return false;

            radio.click();
            return true;
        }
        """,
        answer_index
    )

    if not clicked:
        raise RuntimeError(
            f"Active radio with answer={answer_index} not found"
        )

    logger.info(
        LogCategory.EXECUTION,
        f"[PHASE 3] RADIO selected successfully via DOM click: answer={answer_index}"
    )
