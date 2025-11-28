from playwright.sync_api import sync_playwright

def test_google_search():
    with sync_playwright() as p:
        print("Launching Browser...")
        # using channel="chrome" to fix potential 'spawn UNKNOWN' errors
        browser = p.chromium.launch(headless=False, channel="chrome") 
        page = browser.new_page()

        # 1. Navigate to Google
        print("Step 1: Go to Google")
        page.goto("https://www.google.com")
        
        # 2. Check we are actually on Google
        print(f"   Page Title: {page.title()}")
        assert "Google" in page.title()

        # 3. Type into the search bar
        # Google's search box usually has the name attribute "q"
        print("Step 2: Type search query")
        page.fill('textarea[name="q"]', "Playwright Python")

        # 4. Press Enter to search
        print("Step 3: Press Enter")
        page.press('textarea[name="q"]', "Enter")

        # 5. Wait for results to appear
        # We wait for the 'result-stats' element (e.g., "About 20,000 results")
        print("Step 4: Waiting for results...")
        page.wait_for_selector("#result-stats")
        
        print("Test Passed: Search results loaded.")
        
        # Optional: Take a screenshot
        page.screenshot(path="google_test.png")
        
        browser.close()

if __name__ == "__main__":
    test_google_search()
