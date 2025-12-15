from playwright.sync_api import sync_playwright
import json

def analyze_frame(frame):
    selector = None
    if frame.parent_frame:
        try:
            selector = frame.evaluate("""
                () => {
                    const iframes = Array.from(window.parent.document.querySelectorAll('iframe'));
                    const current = window.frameElement;
                    const index = iframes.indexOf(current);
                    return index >= 0 ? `iframe:nth-of-type(${index+1})` : null;
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
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle")

        frame_tree = analyze_frame(page.main_frame)

        with open("frame_tree.json", "w", encoding="utf-8") as f:
            json.dump(frame_tree, f, indent=2)

        browser.close()



analyze_site("https://selectorshub.com/xpath-practice-page/")
