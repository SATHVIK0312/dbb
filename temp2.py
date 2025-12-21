async def execute_account_row_click(page, step_name: str):

    # ⏸ Pause 10 seconds before doing anything
    await page.wait_for_timeout(10_000)

    # Re-resolve frame (MANDATORY after navigation)
    nav_frame, content_frame = resolve_ccs_frames(page)

    # Wait until account list table is present
    await content_frame.wait_for_selector(
        "xpath=//table[.//text()[contains(.,'Customer Account List')]]",
        timeout=20000
    )

    step_lower = step_name.lower()

    # Determine index
    if "first" in step_lower:
        index = 1
    elif "second" in step_lower:
        index = 2
    elif "third" in step_lower:
        index = 3
    else:
        raise RuntimeError("Specify first / second / third account")

    # Build final XPath
    xpath = (
        f"(//table[.//text()[contains(.,'Customer Account List')]]"
        f"//a[contains(@href,'selectedAccountNumber')])[{index}]"
    )

    account_link = content_frame.locator(f"xpath={xpath}")

    await account_link.wait_for(state="visible", timeout=15000)
    await account_link.scroll_into_view_if_needed()
    await account_link.click(timeout=10000)

    # Wait for Account Display page
    await content_frame.wait_for_selector(
        "div:has-text('Account Display')",
        timeout=20000
    )
