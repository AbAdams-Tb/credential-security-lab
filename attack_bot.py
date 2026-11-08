"""Browser demonstration restricted to five known fictional accounts on loopback."""
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = "http://127.0.0.1:8001"
LOGIN = ROOT + "/login"
EXPECTED_EMAILS = [
    "alice@example.com", "bob@example.com", "david@example.com",
    "omar@example.com", "sarah@example.com",
]

def load_combos():
    lines = (Path(__file__).resolve().parent / "combos.txt").read_text(encoding="utf-8").splitlines()
    pairs = [tuple(line.strip().split(":", 1)) for line in lines if line.strip()]
    if [email for email, _ in pairs] != EXPECTED_EMAILS:
        raise ValueError("This lab accepts only the five predefined fictional accounts in order.")
    return pairs

def main():
    pairs = load_combos()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=350)
        try:
            page = browser.new_page()
            print("=== LOCAL-ONLY CREDENTIAL SECURITY DEMO ===")
            for i, (email, password) in enumerate(pairs, 1):
                print(f"[{i}/5] {email}")
                page.goto(LOGIN, wait_until="domcontentloaded")
                page.locator("#email").fill(email)
                page.locator("#password").fill(password)
                with page.expect_response(
                    lambda r: r.url == LOGIN and r.request.method == "POST"
                ) as response_event:
                    page.locator("#submitBtn").click()
                # Read status immediately. Do not read response.json() after a redirect.
                status = response_event.value.status
                if status == 200:
                    try:
                        page.wait_for_url(ROOT + "/account", timeout=10000)
                        body = page.locator("body").inner_text()
                        if "ACCOUNT_ACCESS_GRANTED" in body and email in body:
                            print("  200 SUCCESS — account access confirmed")
                        else:
                            print("  200 — account access NOT confirmed")
                    except PlaywrightTimeoutError:
                        print("  200 — account navigation timed out")
                elif status == 202:
                    try:
                        page.wait_for_url(ROOT + "/mfa", timeout=10000)
                        print("  202 MFA_REQUIRED — verification page opened; access denied pending OTP")
                    except PlaywrightTimeoutError:
                        print("  202 MFA_REQUIRED — verification page not confirmed")
                elif status == 429:
                    print("  429 BLOCKED — rate limit activated; stopping")
                    break
                elif status == 401:
                    print("  401 FAILED — incorrect credentials")
                else:
                    print(f"  Unexpected HTTP {status}")
                page.wait_for_timeout(800)
            input("Press Enter to close Chromium...")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
