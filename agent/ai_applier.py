#!/usr/bin/env python3
"""
AI Job Applier - Indeed + LinkedIn with separate cookies
"""
import json, time, random, logging, base64, hashlib, re
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests
from cloudflare_handler import solve_cloudflare

QUEUE_DIR = Path('/root/job_bot/queue')
PENDING = QUEUE_DIR / 'pending.json'
APPLIED = QUEUE_DIR / 'applied.json'
FAILED = QUEUE_DIR / 'failed.json'
MANUAL = QUEUE_DIR / 'manual.json'
SCREENSHOTS = Path('/root/job_bot/screenshots')
OUTPUT_DIR = Path('/root/output')
INDEED_COOKIES = Path('/root/job_bot/agent/cookies.json')
LINKEDIN_COOKIES = Path('/root/job_bot/agent/cookies2.json')
ENV_FILE = Path('/root/job_bot/agent/.env')

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().split('\n'):
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v
    return env

ENV = load_env()
OPENROUTER_KEY = ENV.get('OPENROUTER_API_KEY', '')
CAPSOLVER_KEY = ENV.get('CAPSOLVER_API_KEY', '')

MODEL_PRIMARY = "google/gemini-2.0-flash-001"
MODEL_FALLBACK = "google/gemini-2.5-flash"

CONTACT = {
    'first_name': 'Brandon',
    'last_name': 'Ruiz', 
    'email': 'Loungegamingtv@gmail.com',
    'phone': '5625551234',
    'city': 'Long Beach',
    'state': 'CA'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def load_queue(f): 
    try: return json.loads(f.read_text()) if f.exists() else []
    except: return []

def save_queue(f, q): 
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(q, indent=2))

def move_job(job, src, dst, status, error=None):
    q = [j for j in load_queue(src) if j.get('id') != job.get('id')]
    save_queue(src, q)
    job['status'] = status
    job['updated_at'] = datetime.now().isoformat()
    if error: job['error'] = str(error)[:500]
    dq = load_queue(dst)
    dq.append(job)
    save_queue(dst, dq)

def find_resume(job):
    num = job.get('application_number')
    for f in OUTPUT_DIR.glob(f"*_{num}_Resume.pdf"):
        return f
    return None

def img_hash(data):
    return hashlib.md5(data).hexdigest()

def ask_ai(prompt, screenshot_b64, model=MODEL_PRIMARY):
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]}],
                "max_tokens": 500
            },
            timeout=60
        )
        return resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        log.error(f"AI call failed: {e}")
        return ""

def handle_cloudflare(page, ask_ai_func):
    return solve_cloudflare(page, CAPSOLVER_KEY)


def handle_cloudflare_original(page, ask_ai_func):
    """Let AI find and click the Cloudflare checkbox, wait for verification"""
    log.info("Handling Cloudflare with AI vision...")
    
    start_time = time.time()
    max_wait = 60  # Max 60 seconds for verification
    
    while time.time() - start_time < max_wait:
        shot = page.screenshot()
        shot_b64 = base64.b64encode(shot).decode()
        
        # Check if we passed
        html = page.content().lower()
        if 'verify you are human' not in html and 'additional verification' not in html:
            log.info("Cloudflare passed!")
            return True
        
        # Ask AI what to do
        prompt = """Look at this screenshot. There is a Cloudflare verification.

If you see a checkbox to click, respond:
{"action": "click", "x": 520, "y": 240, "reason": "clicking checkbox"}

If you see a spinning/loading verification in progress, respond:
{"action": "wait", "reason": "verification in progress"}

If verification is complete and you see the actual website, respond:
{"action": "done", "reason": "verification passed"}

If you see an unsolvable CAPTCHA (select images, puzzle), respond:
{"action": "captcha", "reason": "needs captcha solver"}

Respond with ONLY JSON, no other text."""

        response = ask_ai_func(prompt, shot_b64, MODEL_PRIMARY)
        log.info(f"Cloudflare AI: {response[:100]}")
        
        try:
            clean = re.sub(r'```json\s*|\s*```', '', response).strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            action = json.loads(clean[start:end])
        except:
            action = {'action': 'wait', 'reason': 'parse error'}
        
        act = action.get('action', 'wait')
        
        if act == 'done':
            log.info("AI says verification passed")
            return True
        
        elif act == 'click':
            x = action.get('x', 520)
            y = action.get('y', 240)
            log.info(f"AI clicking at ({x}, {y})")
            page.mouse.click(x, y)
            time.sleep(3)
        
        elif act == 'captcha':
            log.warning("CAPTCHA detected - needs solver")
            return False
        
        elif act == 'wait':
            log.info("Waiting for verification...")
            time.sleep(3)
        
        else:
            time.sleep(2)
    
    log.warning("Cloudflare timeout after 60s")
    return False

def load_cookies(context, cookie_file):
    if not cookie_file.exists():
        log.warning(f"Cookie file not found: {cookie_file}")
        return
    try:
        cookies = json.loads(cookie_file.read_text())
        playwright_cookies = []
        for c in cookies:
            pc = {'name': c['name'], 'value': c['value'], 'domain': c['domain'], 'path': c.get('path', '/')}
            if c.get('expirationDate'): pc['expires'] = c['expirationDate']
            if c.get('secure'): pc['secure'] = c['secure']
            if c.get('httpOnly'): pc['httpOnly'] = c['httpOnly']
            if c.get('sameSite'):
                ss = c['sameSite'].lower()
                if ss in ['strict', 'lax', 'none']:
                    pc['sameSite'] = ss.capitalize() if ss != 'none' else 'None'
            playwright_cookies.append(pc)
        context.add_cookies(playwright_cookies)
        log.info(f"Loaded {len(playwright_cookies)} cookies from {cookie_file.name}")
    except Exception as e:
        log.error(f"Cookie load failed: {e}")

def detect_state(page):
    html = page.content().lower()
    url = page.url.lower()
    if 'verify you are human' in html or 'additional verification' in html:
        return 'cloudflare'
    if ('sign in' in html or 'log in' in html) and ('password' in html or 'email' in html):
        if 'indeed.com' in url or 'linkedin.com/login' in url or 'linkedin.com/checkpoint' in url:
            return 'login'
    if 'application submitted' in html or 'thank you for applying' in html or 'your application has been' in html:
        return 'success'
    if 'already applied' in html:
        return 'already_applied'
    return 'ready'

def apply_to_job(page, job, model=MODEL_PRIMARY):
    url = job.get('url', '')
    company = job.get('company', 'Unknown')
    title = job.get('title', 'Unknown')
    resume = find_resume(job)
    
    if not resume or not resume.exists():
        return False, "Resume not found"
    
    log.info(f"Navigating to {url}")
    page.goto(url, timeout=60000, wait_until='domcontentloaded')
    time.sleep(random.uniform(3, 5))
    
    max_actions = 30
    cloudflare_attempts = 0
    stuck_count = 0
    history = []
    
    for action_num in range(max_actions):
        shot = page.screenshot()
        shot_b64 = base64.b64encode(shot).decode()
        shot_hash = img_hash(shot)
        
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        (SCREENSHOTS / f"{job.get('id')}_{action_num}.png").write_bytes(shot)
        
        state = detect_state(page)
        log.info(f"Action {action_num}: State={state}")
        
        if state == 'cloudflare':
            cloudflare_attempts += 1
            if cloudflare_attempts > 3:
                return False, "Cloudflare blocked"
            handle_cloudflare(page, ask_ai)
            time.sleep(3)
            continue
        
        if state == 'success':
            return True, "Application submitted!"
        
        if state == 'already_applied':
            return False, "Already applied"
        
        if state == 'login':
            return False, "Login required - cookies expired"
        
        prompt = f"""Look at this screenshot. You are applying for a job.

JOB: {title} at {company}
GOAL: Complete and submit the job application

YOUR INFO:
- First Name: {CONTACT['first_name']}
- Last Name: {CONTACT['last_name']}
- Email: {CONTACT['email']}
- Phone: {CONTACT['phone']}
- City: {CONTACT['city']}, {CONTACT['state']}

RECENT ACTIONS: {json.dumps(history[-3:]) if history else 'None yet'}

RULES:
1. If you see an Apply button, click it
2. If you see a form field, fill it with my info
3. If you see a file upload for resume, upload it
4. If you see Submit/Send/Apply button at the end of form, click it
5. If application is complete, say done

Respond with ONLY one JSON object (no markdown, no explanation):
{{"action": "click", "selector": "exact button text or link text", "reason": "brief why"}}
{{"action": "type", "selector": "field label or placeholder", "text": "value to type", "reason": "brief why"}}
{{"action": "upload", "reason": "uploading resume"}}
{{"action": "done", "reason": "application complete"}}
{{"action": "stuck", "reason": "why"}}
"""
        
        response = ask_ai(prompt, shot_b64, model)
        log.info(f"AI ({model.split('/')[-1]}): {response[:150]}")
        
        try:
            clean = re.sub(r'```json\s*|\s*```', '', response).strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            action = json.loads(clean[start:end]) if start >= 0 and end > start else {'action': 'stuck', 'reason': 'Parse error'}
        except:
            action = {'action': 'stuck', 'reason': 'Invalid JSON'}
        
        history.append(action)
        act = action.get('action', 'stuck')
        sel = str(action.get('selector', ''))
        
        if act == 'done':
            return True, "AI reports complete"
        
        if act == 'stuck':
            stuck_count += 1
            if stuck_count >= 2 and model == MODEL_PRIMARY:
                log.info("Escalating to 2.5...")
                model = MODEL_FALLBACK
                stuck_count = 0
                continue
            elif stuck_count >= 2:
                return False, action.get('reason', 'Stuck')
            continue
        
        stuck_count = 0
        
        try:
            if act == 'click':
                clicked = False
                strategies = [
                    lambda: page.get_by_role("button", name=re.compile(sel, re.I)).first.click(timeout=5000),
                    lambda: page.get_by_role("link", name=re.compile(sel, re.I)).first.click(timeout=5000),
                    lambda: page.get_by_text(sel, exact=False).first.click(timeout=5000),
                    lambda: page.locator(f"text=/{sel}/i").first.click(timeout=5000),
                ]
                for strategy in strategies:
                    try:
                        strategy()
                        clicked = True
                        log.info(f"Clicked: {sel}")
                        break
                    except:
                        continue
                if not clicked:
                    log.warning(f"Could not click: {sel}")
            
            elif act == 'type':
                text = str(action.get('text', ''))
                typed = False
                strategies = [
                    lambda: page.get_by_label(re.compile(sel, re.I)).first.fill(text, timeout=5000),
                    lambda: page.get_by_placeholder(re.compile(sel, re.I)).first.fill(text, timeout=5000),
                    lambda: page.locator(f"input[name*='{sel}' i]").first.fill(text, timeout=5000),
                    lambda: page.locator(f"input[aria-label*='{sel}' i]").first.fill(text, timeout=5000),
                ]
                for strategy in strategies:
                    try:
                        strategy()
                        typed = True
                        log.info(f"Typed '{text[:20]}' in: {sel}")
                        break
                    except:
                        continue
                if not typed:
                    log.warning(f"Could not type in: {sel}")
            
            elif act == 'upload':
                try:
                    page.locator('input[type="file"]').first.set_input_files(str(resume), timeout=5000)
                    log.info(f"Uploaded: {resume.name}")
                except Exception as e:
                    log.warning(f"Upload failed: {e}")
        
        except Exception as e:
            log.error(f"Action error: {e}")
        
        time.sleep(random.uniform(2, 4))
        
        new_hash = img_hash(page.screenshot())
        if new_hash == shot_hash:
            log.warning("Page unchanged")
        else:
            log.info("Page changed")
    
    return False, "Max actions reached"

def run(max_jobs=5):
    pending = load_queue(PENDING)
    if not pending:
        log.info("No pending jobs")
        return
    
    log.info(f"Found {len(pending)} pending jobs")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Create separate contexts for Indeed and LinkedIn
        indeed_context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        load_cookies(indeed_context, INDEED_COOKIES)
        
        linkedin_context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        load_cookies(linkedin_context, LINKEDIN_COOKIES)
        
        indeed_page = indeed_context.new_page()
        linkedin_page = linkedin_context.new_page()
        
        applied = 0
        for job in pending[:max_jobs]:
            log.info(f"\n{'='*50}")
            log.info(f"Processing: {job.get('company')} - {job.get('title')}")
            
            url = job.get('url', '')
            if 'linkedin.com' in url:
                page = linkedin_page
                log.info("Using LinkedIn cookies")
            else:
                page = indeed_page
                log.info("Using Indeed cookies")
            
            try:
                success, msg = apply_to_job(page, job)
                if success:
                    log.info(f"SUCCESS: {msg}")
                    move_job(job, PENDING, APPLIED, 'applied')
                    applied += 1
                else:
                    log.warning(f"FAILED: {msg}")
                    if 'login' in msg.lower() or 'cookie' in msg.lower():
                        move_job(job, PENDING, MANUAL, 'manual', msg)
                    else:
                        move_job(job, PENDING, FAILED, 'failed', msg)
            except Exception as e:
                log.error(f"Error: {e}")
                move_job(job, PENDING, FAILED, 'failed', str(e))
            
            time.sleep(random.uniform(10, 20))
        
        browser.close()
    log.info(f"\nDone. Applied: {applied}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=5)
    args = parser.parse_args()
    run(max_jobs=args.max)
