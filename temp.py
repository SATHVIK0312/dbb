from playwright.sync_api import sync_playwright
import json


def analyze_frame(frame):
    selector = None

    if frame.parent_frame:
        try:
            selector = frame.evaluate("""
            () => {
                try {
                    const el = window.frameElement;
                    if (!el) return null;

                    if (el.id) return 'iframe#' + el.id;
                    if (el.name) return 'iframe[name="' + el.name + '"]';

                    const iframes = Array.from(window.parent.document.querySelectorAll('iframe'));
                    const index = iframes.indexOf(el);
                    return index >= 0 ? `iframe:nth-of-type(${index + 1})` : null;
                } catch {
                    return null;
                }
            }
            """)
        except:
            selector = None

    data = {
        "selector": selector,
        "name": frame.name,
        "url": frame.url,
        "children": []
    }

    for child in frame.child_frames:
        data["children"].append(analyze_frame(child))

    return data


def analyze_site(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
            # executable_path=r"C:\\Path\\To\\Chromium1194\\chrome.exe"  # if required
        )
        context = browser.new_context()
        page = context.new_page()

        # --------------------
        # 1. Go to login page
        # --------------------
        page.goto(url, timeout=60000)

        # --------------------
        # 2. LOGIN (EDIT THESE SELECTORS)
        # --------------------
        page.fill("input[name='username']", "YOUR_USERNAME")
        page.fill("input[name='password']", "YOUR_PASSWORD")
        page.click("button[type='submit']")

        # --------------------
        # 3. WAIT FOR POST-LOGIN STATE
        # --------------------
        # Choose ONE reliable condition:
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        # OR
        # page.wait_for_selector("text=Dashboard", timeout=60000)

        # --------------------
        # 4. ANALYZE IFRAMES (POST LOGIN)
        # --------------------
        frame_tree = analyze_frame(page.main_frame)

        with open("frame_tree.json", "w", encoding="utf-8") as f:
            json.dump(frame_tree, f, indent=2)

        browser.close()


# Example call
analyze_site("https://your-login-page-url")
