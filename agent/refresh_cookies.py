"""
Refresh Indeed cookies by logging in with Browser-Use
Run this when cookies are stale or triggering CAPTCHAs
"""
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from browser_use import Agent
from browser_use.browser.session import BrowserSession

# Config
COOKIES_FILE = Path(__file__).parent / "cookies.json"
INDEED_EMAIL = "brandonlruiz98@gmail.com"
INDEED_PASSWORD = os.getenv("INDEED_PASSWORD", "")

async def refresh_indeed_cookies(password: str = None):
    """Login to Indeed and save fresh cookies"""

    pwd = password or INDEED_PASSWORD
    if not pwd:
        print("ERROR: No password provided. Set INDEED_PASSWORD in .env or pass as argument")
        return False

    print("Starting Indeed login to refresh cookies...")

    # Use cloud browser for stealth
    browser = BrowserSession(
        use_cloud=True,
        cloud_proxy_country_code='us',
    )

    task = f"""
    Go to https://secure.indeed.com/account/login and log in with these credentials:
    - Email: {INDEED_EMAIL}
    - Password: {pwd}

    STEPS:
    1. Go to the login page
    2. Enter the email address
    3. Click Continue/Next
    4. Enter the password
    5. Click Sign In
    6. If there's a CAPTCHA, try to solve it
    7. If there's 2FA/verification, wait and describe what's needed
    8. Once logged in, go to https://www.indeed.com to confirm you're logged in
    9. Say "LOGIN_SUCCESS" when you see the Indeed homepage while logged in

    If login fails, explain why.
    """

    agent = Agent(
        task=task,
        browser_session=browser,
        use_vision=True,
        max_steps=30,
        max_failures=5,
    )

    try:
        result = await agent.run()
        result_str = str(result)

        if "LOGIN_SUCCESS" in result_str.upper():
            print("Login successful! Extracting cookies...")

            # Get cookies from the browser session
            context = await browser.get_playwright_browser_context()
            cookies = await context.cookies()

            # Filter to Indeed cookies
            indeed_cookies = [c for c in cookies if 'indeed' in c.get('domain', '')]

            if indeed_cookies:
                # Save cookies
                COOKIES_FILE.write_text(json.dumps(indeed_cookies, indent=2))
                print(f"Saved {len(indeed_cookies)} Indeed cookies to {COOKIES_FILE}")
                return True
            else:
                print("No Indeed cookies found!")
                return False
        else:
            print(f"Login may have failed. Result: {result_str[:500]}")
            return False

    except Exception as e:
        print(f"Error during login: {e}")
        return False
    finally:
        await browser.close()


if __name__ == "__main__":
    import sys
    password = sys.argv[1] if len(sys.argv) > 1 else None
    success = asyncio.run(refresh_indeed_cookies(password))
    exit(0 if success else 1)
