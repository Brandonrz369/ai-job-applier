#!/usr/bin/env python3
import json, time, random, logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError
from playwright_stealth import Stealth

QUEUE_DIR = Path('/root/job_bot/queue')
PENDING_FILE = QUEUE_DIR / 'pending.json'
APPLIED_FILE = QUEUE_DIR / 'applied.json'
FAILED_FILE = QUEUE_DIR / 'failed.json'
MANUAL_FILE = QUEUE_DIR / 'manual.json'
SCREENSHOTS_DIR = Path('/root/job_bot/screenshots')
OUTPUT_DIR = Path('/root/output')

CONTACT_INFO = {'first_name': 'Brandon', 'last_name': 'Ruiz', 'email': 'brandonlruiz98@gmail.com', 'phone': '7755308234', 'city': 'Anaheim', 'state': 'CA'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def human_delay(min_sec=0.5, max_sec=2.0): time.sleep(random.uniform(min_sec, max_sec))

def human_type(page, selector, text):
    try:
        field = page.locator(selector).first
        if field.count() == 0 or not field.is_visible(): return False
        field.click()
        human_delay(0.3, 0.8)
        for char in text:
            field.type(char, delay=random.randint(50, 150))
            if random.random() < 0.1: human_delay(0.2, 0.5)
        return True
    except: return False

def load_queue(filepath):
    try: return json.loads(filepath.read_text())
    except: return []

def save_queue(filepath, queue): filepath.write_text(json.dumps(queue, indent=2))

def move_job(job, from_file, to_file, status, error=None):
    from_queue = [j for j in load_queue(from_file) if j.get('id') != job.get('id')]
    save_queue(from_file, from_queue)
    job['status'] = status
    job['updated_at'] = datetime.now().isoformat()
    if error: job['error'] = error
    to_queue = load_queue(to_file)
    to_queue.append(job)
    save_queue(to_file, to_queue)

def find_pdf_files(job):
    app_num = job.get('application_number')
    for f in OUTPUT_DIR.glob(f"*_{app_num}_Resume.pdf"):
        cover = OUTPUT_DIR / f.name.replace('_Resume.pdf', '_CoverLetter.pdf')
        return f, cover if cover.exists() else None
    return None, None

def is_indeed_direct_apply(url): return 'indeed.com' in url and '/viewjob' in url

def fill_field(page, selector, value):
    try:
        if human_type(page, selector, value):
            logger.info(f"Filled: {selector[:30]}...")
            human_delay(0.3, 0.8)
    except: pass

def apply_to_job(page, job, resume_path, cover_path=None):
    url = job.get('url', '')
    if not is_indeed_direct_apply(url): return False, "Not Indeed direct apply"
    try:
        logger.info(f"Navigating to: {url}")
        page.goto(url, timeout=30000)
        human_delay(2, 4)
        screenshot_path = SCREENSHOTS_DIR / f"{job.get('id')}_1_job.png"
        page.screenshot(path=str(screenshot_path))
        apply_btn = page.locator('button:has-text("Apply now"), a:has-text("Apply now")')
        if apply_btn.count() == 0: return False, "No apply button"
        btn_text = apply_btn.first.text_content().lower()
        if 'company site' in btn_text: return False, "External application"
        logger.info("Clicking Apply...")
        apply_btn.first.click()
        human_delay(3, 5)
        page.screenshot(path=str(SCREENSHOTS_DIR / f"{job.get('id')}_2_after_click.png"))
        if page.locator('text=Sign in').count() > 0: return False, "Sign-in required"
        resume_input = page.locator('input[type="file"]').first
        if resume_input.count() > 0:
            logger.info(f"Uploading resume: {resume_path}")
            resume_input.set_input_files(str(resume_path))
            human_delay(2, 3)
        fill_field(page, 'input[name*="name" i][name*="first" i]', CONTACT_INFO['first_name'])
        fill_field(page, 'input[name*="name" i][name*="last" i]', CONTACT_INFO['last_name'])
        fill_field(page, 'input[type="email"]', CONTACT_INFO['email'])
        fill_field(page, 'input[type="tel"]', CONTACT_INFO['phone'])
        page.screenshot(path=str(SCREENSHOTS_DIR / f"{job.get('id')}_3_filled.png"))
        logger.info("TEST MODE - not submitting")
        return True, "Form filled (test mode)"
    except TimeoutError: return False, "Page timeout"
    except Exception as e: return False, f"Error: {str(e)}"

def run_applier(max_applications=5, headless=False):
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    pending = load_queue(PENDING_FILE)
    if not pending: logger.info("No pending applications"); return
    logger.info(f"Found {len(pending)} pending applications")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        applied_count = 0
        for job in pending[:max_applications]:
            logger.info(f"\n{'='*50}\nProcessing: {job.get('company')} - {job.get('title')}")
            resume_path, cover_path = find_pdf_files(job)
            if not resume_path or not resume_path.exists():
                logger.error("Resume not found")
                move_job(job, PENDING_FILE, FAILED_FILE, 'failed', 'Resume not found')
                continue
            if not is_indeed_direct_apply(job.get('url', '')):
                logger.info("Not Indeed - moving to manual")
                move_job(job, PENDING_FILE, MANUAL_FILE, 'manual', 'Not Indeed')
                continue
            success, message = apply_to_job(page, job, resume_path, cover_path)
            if success:
                logger.info(f"SUCCESS: {message}")
                move_job(job, PENDING_FILE, APPLIED_FILE, 'applied')
                applied_count += 1
            else:
                logger.warning(f"FAILED: {message}")
                if 'sign-in' in message.lower() or 'manual' in message.lower():
                    move_job(job, PENDING_FILE, MANUAL_FILE, 'manual', message)
                else:
                    move_job(job, PENDING_FILE, FAILED_FILE, 'failed', message)
            human_delay(5, 10)
        browser.close()
    logger.info(f"\nApplied: {applied_count}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=5)
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    run_applier(max_applications=args.max, headless=args.headless)
