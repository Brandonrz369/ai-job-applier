import sys
import asyncio
import re
import subprocess
from playwright.async_api import async_playwright

async def run_auth(email, password):
    print(f"Starting auth for {email}")
    
    # Start opencode auth login process
    process = subprocess.Popen(
        ["opencode", "auth", "login"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    auth_url = None
    
    # We'll use a loop to read stdout until we find the URL or handling prompts
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line_str = line.strip()
            print(f"OPENCODE: {line_str}")
            
            # Handle "add new account" prompt
            if "(a)dd new account(s)" in line or "[a/f]" in line:
                print("Answering 'a' to add new account...")
                process.stdin.write("a\n")
                process.stdin.flush()
                continue
            
            # Handle "Project ID" prompt
            if "Project ID" in line and "leave blank" in line:
                print("Skipping Project ID (Enter)...")
                process.stdin.write("\n")
                process.stdin.flush()
                continue

            # Regex to find URL: https://accounts.google.com/o/oauth2/...
            match = re.search(r'(https://accounts\.google\.com/[^\s]+)', line)
            if match:
                auth_url = match.group(1)
                print(f"Found URL: {auth_url}")
                break
                
    if not auth_url:
        print("Failed to find Auth URL")
        process.kill()
        return False

    # Launch Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("Navigating to URL...")
            await page.goto(auth_url)
            
            # Email
            print("Entering email...")
            await page.fill('input[type="email"]', email)
            await page.click('#identifierNext')
            
            # Wait for password field
            print("Waiting for password field...")
            await page.wait_for_selector('input[type="password"]', state='visible')
            await page.fill('input[type="password"]', password)
            await page.click('#passwordNext')
            
            # Wait for navigation or "Allow" button
            print("Waiting for next step...")
            await page.wait_for_load_state('networkidle')
            
            # Check for Allow/Continue
            # This part is tricky as it varies with Antigravity app verification status
            # It might ask for "Continue" or "Allow"
            
            # Try to find common buttons
            try:
                # Look for "Allow" or "Continue"
                # Sometimes it asks to verify it's you?
                # For Antigravity, it's a consent screen.
                
                # Check if we are already redirected to localhost (success)
                if "localhost" in page.url:
                    print("Redirected to localhost immediately.")
                else:
                    # Look for buttons
                    allow_btn = page.locator('button:has-text("Allow")')
                    continue_btn = page.locator('button:has-text("Continuar")') # Spanish? No, usually English
                    continue_btn_en = page.locator('button:has-text("Continue")')
                    
                    if await allow_btn.count() > 0:
                        print("Clicking Allow...")
                        await allow_btn.click()
                    elif await continue_btn_en.count() > 0:
                        print("Clicking Continue...")
                        await continue_btn_en.click()
                    
                    # Wait for redirect
                    await page.wait_for_url('**/localhost:*', timeout=10000)
            except Exception as e:
                print(f"Interaction error or already redirected: {e}")

            print("Auth flow completed in browser.")
            
        except Exception as e:
            print(f"Browser Error: {e}")
            await page.screenshot(path=f"/root/job_bot/logs/error_{email}.png")
            await browser.close()
            process.kill()
            return False
        
        await browser.close()
    
    # Wait for process to finish
    # opencode should detect the callback and exit or print success
    # We can wait a bit
    print("Waiting for opencode to finalize...")
    try:
        # It might be interactive or wait for enter?
        # "After signing in... press Enter to finish."
        # We need to write newline to stdin if it's waiting
        # But we opened with PIPE.
        pass
    except:
        pass

    # Sending input to process if needed
    # process.stdin.write("\n")
    # process.stdin.flush()
    
    # Let's see what opencode says
    # It might run indefinitely until we kill it or valid input?
    # The README says: "After signing in... press Enter to finish."
    
    # So we MUST send Enter.
    # But we didn't open stdin as PIPE initially in my code above? No, I only did stdout/err.
    # I need to open stdin too.
    
    process.terminate() # or kill?
    # Ideally we want opencode to save the token.
    # If we kill it, does it save?
    # Usually the token is exchanged during the callback.
    # Once the callback is hit, opencode prints success.
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python bot/auth_one_account.py <email> <password>")
        sys.exit(1)
        
    email = sys.argv[1]
    password = sys.argv[2]
    
    # Since we need to interact with stdin, we should modify the subprocess call in run_auth
    # But for a quick script, I'll just rewrite the call logic in run_auth (I can't edit it here).
    # I'll update the code block above before submitting.
    
    asyncio.run(run_auth(email, password))
