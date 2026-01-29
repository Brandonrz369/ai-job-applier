from playwright.sync_api import sync_playwright
import time
from config import BROWSER_WS, MODEL_FAST, MODEL_SMART, CANDIDATE
from ai import ask

class Agent:
    def __init__(self, account):
        self.account = account
        self.model = MODEL_FAST
        self.fail_count = 0
        
    def build_context(self, job):
        return f"""GOAL: Apply to this job.

CREDENTIALS:
Email: {self.account['gmail']}
Password: {self.account['gmail_pass']}

CANDIDATE:
Name: {CANDIDATE['name']}
Phone: {CANDIDATE['phone']}
Location: {CANDIDATE['location']}
Experience: {CANDIDATE['summary']}

JOB: {job.get('title', '')} at {job.get('company', '')}

Viewport: 1280x800. Look at screenshot and decide next action."""

    def run(self, job):
        """Apply to a single job. Returns (success, message)"""
        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(BROWSER_WS)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            # Load job URL
            page.goto(job['url'], timeout=120000)
            time.sleep(3)
            
            ctx = self.build_context(job)
            
            for step in range(30):
                # Get active page (handles popups/new tabs)
                page = context.pages[-1]
                
                # Screenshot
                screenshot = page.screenshot()
                page.screenshot(path=f"/root/output/step_{step}.png")
                
                # Ask AI
                action = ask(screenshot, ctx, self.model)
                print(f"  Step {step}: {action[:60]}")
                
                # Track failures
                if "FAILED" in action:
                    self.fail_count += 1
                    if self.fail_count >= 3 and self.model == MODEL_FAST:
                        self.model = MODEL_SMART
                        self.fail_count = 0
                        print(f"  -> Switching to smart model")
                        continue  # Retry with better model
                    elif self.fail_count >= 3:
                        return False, action
                else:
                    self.fail_count = 0
                
                # Execute
                if action.startswith("CLICK"):
                    parts = action.replace(",", " ").split()
                    x, y = int(parts[1]), int(parts[2])
                    page.mouse.click(x, y)
                    time.sleep(2)
                    
                elif action.startswith("TYPE"):
                    text = action[4:].strip().strip('"\'')
                    page.keyboard.type(text)
                    time.sleep(0.5)
                    
                elif action.startswith("PRESS"):
                    key = action[5:].strip()
                    page.keyboard.press(key)
                    time.sleep(1)
                    
                elif action.startswith("SCROLL"):
                    direction = action[6:].strip().lower()
                    page.mouse.wheel(0, -300 if "up" in direction else 300)
                    time.sleep(1)
                    
                elif "DONE" in action:
                    self.model = MODEL_FAST
                    return True, "Applied successfully"
                    
                elif "FAILED" in action:
                    pass  # Handled above
                
                time.sleep(1)
            
            return False, "Max steps reached"
