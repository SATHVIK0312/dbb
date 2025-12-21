import re

async def execute_account_row_click(page, step_name: str):

    # ⏸ Pause 10 seconds BEFORE doing anything
    await page.wait_for_timeout(10_000)

    # Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    # Wait until account list table is present
    await content_frame.wait_for_selector(
        "xpath=//table[.//text()[contains(.,'Customer Account List')]]",
        timeout=20000
    )

    step_lower = step_name.lower()

    # -----------------------------------------
    # Base XPath (NO INDEX)
    # -----------------------------------------
    base_xpath = (
        "//table[.//text()[contains(.,'Customer Account List')]]"
        "//a[contains(@href,'selectedAccountNumber')]"
    )

    account_links = content_frame.locator(f"xpath={base_xpath}")
    total = await account_links.count()

    if total == 0:
        raise RuntimeError("No account numbers found in Customer Account List")

    link_to_click = None

    # -----------------------------------------
    # CASE 1: first / second / third / nth
    # -----------------------------------------
    index_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5
    }

    for word, idx in index_map.items():
        if word in step_lower:
            if idx > total:
                raise RuntimeError(
                    f"Only {total} accounts found, cannot click {word}"
                )
            link_to_click = account_links.nth(idx - 1)
            break

    # Numeric form: 2nd / 3rd / 4th
    if link_to_click is None:
        m = re.search(r"(\d+)(st|nd|rd|th)", step_lower)
        if m:
            idx = int(m.group(1))
            if idx > total:
                raise RuntimeError(
                    f"Only {total} accounts found, cannot click index {idx}"
                )
            link_to_click = account_links.nth(idx - 1)

    # -----------------------------------------
    # CASE 2: masked value (XXXXXXXX5034)
    # -----------------------------------------
    if link_to_click is None and "xxxx" in step_lower:
        last4 = step_lower[-4:]

        for i in range(total):
            href = await account_links.nth(i).get_attribute("href")
            if href and href.endswith(last4):
                link_to_click = account_links.nth(i)
                break

        if link_to_click is None:
            raise RuntimeError(
                f"No account ending with {last4} found"
            )

    # -----------------------------------------
    # CASE 3: full / partial account number
    # -----------------------------------------
    if link_to_click is None:
        digits = "".join(c for c in step_lower if c.isdigit())

        if digits:
            for i in range(total):
                href = await account_links.nth(i).get_attribute("href")
                if href and digits in href:
                    link_to_click = account_links.nth(i)
                    break

            if link_to_click is None:
                raise RuntimeError(
                    f"Account number {digits} not found"
                )

    # -----------------------------------------
    # FINAL VALIDATION
    # -----------------------------------------
    if link_to_click is None:
        raise RuntimeError(
            "Unable to determine which account to click"
        )

    # -----------------------------------------
    # CLICK
    # -----------------------------------------
    await link_to_click.wait_for(state="visible", timeout=15000)
    await link_to_click.scroll_into_view_if_needed()
    await link_to_click.click(timeout=10000)

    # Wait for Account Display page
    await content_frame.wait_for_selector(
        "div:has-text('Account Display')",
        timeout=20000
    )

    # ⏸ Pause 5 seconds AFTER step completes
    await page.wait_for_timeout(5_000)
