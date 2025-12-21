import re

async def execute_account_row_click(page, step_name: str):
    """
    Handles:
    - first / second / third / nth account number
    - Uses XPath with contains(text()) for legacy CCS DOM
    """

    # Resolve frames
    nav_frame, content_frame = resolve_ccs_frames(page)

    step_lower = step_name.lower()

    # -------------------------------
    # STEP 1: Extract index from step
    # -------------------------------
    index_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5
    }

    index = None

    for word, value in index_map.items():
        if word in step_lower:
            index = value
            break

    # Support numeric: 1st / 2nd / 3rd / 4th
    if index is None:
        m = re.search(r"(\d+)(st|nd|rd|th)", step_lower)
        if m:
            index = int(m.group(1))

    if index is None:
        raise RuntimeError(
            "ACCOUNT_ROW_CLICK requires first / second / nth account"
        )

    # -----------------------------------------
    # STEP 2: Build base XPath (NO INDEX YET)
    # -----------------------------------------
    base_xpath = (
        "//table[.//text()[contains(.,'Customer Account List')]]"
        "//a[contains(@href,'selectedAccountNumber')]"
    )

    # -----------------------------------------
    # STEP 3: Validate index exists
    # -----------------------------------------
    total_accounts = await content_frame.locator(
        f"xpath={base_xpath}"
    ).count()

    if total_accounts == 0:
        raise RuntimeError("No account numbers found in Customer Account List")

    if index > total_accounts:
        raise RuntimeError(
            f"Only {total_accounts} accounts found, cannot click index {index}"
        )

    # -----------------------------------------
    # STEP 4: Final XPath with index
    # -----------------------------------------
    final_xpath = f"({base_xpath})[{index}]"

    # -----------------------------------------
    # STEP 5: Click the account
    # -----------------------------------------
    account_link = content_frame.locator(f"xpath={final_xpath}")

    await account_link.wait_for(state="visible", timeout=15000)
    await account_link.scroll_into_view_if_needed()
    await account_link.click(timeout=10000)

    # -----------------------------------------
    # STEP 6: Wait for navigation
    # -----------------------------------------
    await content_frame.wait_for_selector(
        "div:has-text('Account Display')",
        timeout=20000
    )
