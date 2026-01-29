"""
Job Application Agent using Browser-Use Cloud with US residential proxy
Focuses on Indeed Easy Apply only
"""
import asyncio
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(Path("/root/job_bot/agent/.env"))

# Browser-Use imports
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile, ProxySettings
from browser_use.browser.session import BrowserSession

# SDK for cloud file uploads
from browser_use_sdk import AsyncBrowserUse
import aiohttp

# ============ CONFIG ============
QUEUE_DIR = Path("/root/job_bot/queue")
OUTPUT_DIR = Path("/root/output")
COOKIES_FILE = Path("/root/job_bot/agent/cookies.json")

# Bright Data residential proxy settings from environment
BRIGHT_DATA_PROXY = ProxySettings(
    server="http://brd.superproxy.io:33335",
    username=os.getenv("BRIGHT_DATA_USERNAME", ""),
    password=os.getenv("BRIGHT_DATA_PASSWORD", ""),
)

# Applicant info
APPLICANT = {
    "name": "Brandon Ruiz",
    "email": "brandonlruiz98@gmail.com",  # Must match Indeed account
    "phone": "775-530-8234",
    "location": "Anaheim, CA",
}

# Rate limiting
DELAY_BETWEEN_JOBS = 10  # seconds


STORAGE_STATE_FILE = Path("/root/job_bot/agent/storage_state.json")

def load_cookies_as_storage_state() -> str:
    """Convert cookies.json to Playwright storage state file and return path"""
    if not COOKIES_FILE.exists():
        return None

    raw_cookies = json.loads(COOKIES_FILE.read_text())

    # Convert to Playwright cookie format
    pw_cookies = []
    for cookie in raw_cookies:
        pw_cookie = {
            "name": cookie.get("name"),
            "value": cookie.get("value"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
        }

        # Add expiration if not session cookie
        if cookie.get("expirationDate"):
            pw_cookie["expires"] = cookie.get("expirationDate")

        # Handle sameSite
        same_site = cookie.get("sameSite", "Lax")
        if same_site == "no_restriction":
            same_site = "None"
        elif same_site == "unspecified":
            same_site = "Lax"
        pw_cookie["sameSite"] = same_site

        pw_cookies.append(pw_cookie)

    storage_state = {
        "cookies": pw_cookies,
        "origins": []
    }

    # Write to file and return path
    STORAGE_STATE_FILE.write_text(json.dumps(storage_state, indent=2))
    return str(STORAGE_STATE_FILE)


def load_queue(name: str) -> list:
    """Load a queue JSON file"""
    path = QUEUE_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_queue(name: str, data: list):
    """Save a queue JSON file"""
    path = QUEUE_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))


N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/incoming-job')

import requests as http_requests


async def upload_file_to_cloud_session(session_id: str, file_path: str) -> str | None:
    """Upload a local file to a Browser-Use Cloud session via presigned URL.
    Returns the cloud filename on success, None on failure."""
    api_key = os.getenv("BROWSER_USE_API_KEY")
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        print(f"  Upload skipped: {file_path} does not exist")
        return None

    file_size = file_path_obj.stat().st_size
    file_name = file_path_obj.name

    try:
        client = AsyncBrowserUse(api_key=api_key)
        presigned = await client.files.browser_session_upload_file_presigned_url(
            session_id=session_id,
            file_name=file_name,
            content_type="application/pdf",
            size_bytes=file_size,
        )

        # Upload the file to the presigned URL
        form_data = aiohttp.FormData()
        for key, value in presigned.fields.items():
            form_data.add_field(key, value)
        form_data.add_field(
            'file',
            open(file_path, 'rb'),
            filename=file_name,
            content_type='application/pdf',
        )

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(presigned.url, data=form_data) as resp:
                if resp.status in [200, 201, 204]:
                    print(f"  Uploaded {file_name} to cloud session ({file_size} bytes)")
                    return presigned.file_name
                else:
                    body = await resp.text()
                    print(f"  Upload failed: HTTP {resp.status} - {body[:200]}")
                    return None

    except Exception as e:
        print(f"  Cloud upload error: {e}")
        return None


def send_to_factory(job: dict) -> dict | None:
    """Send job to n8n resume factory and get back PDF paths"""
    payload = {
        'title': str(job.get('title', 'Unknown')),
        'company': str(job.get('company', 'Unknown')),
        'description': str(job.get('description', '')),
        'url': str(job.get('url', '')),
        'location': str(job.get('location', '')),
    }

    try:
        print(f"  Sending to n8n factory for resume generation...")
        response = http_requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=180,
        )

        if response.status_code in [200, 202]:
            result = response.json()
            print(f"  Factory success: app #{result.get('application_number')}")
            return result
        else:
            print(f"  Factory error: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"  Factory connection failed: {e}")
        return None


def get_resume_path(job: dict) -> str | None:
    """Find resume PDF for this job"""
    company = job.get('company', '').replace(' ', '_').replace('/', '_')[:30]
    app_num = job.get('application_number', '')

    # Try patterns (company/app-specific only — no catch-all)
    patterns = [
        f"{company}_{app_num}_Resume.pdf",
        f"{company}_*_Resume.pdf",
        f"*_{app_num}_Resume.pdf",
    ]

    for pattern in patterns:
        matches = list(OUTPUT_DIR.glob(pattern))
        if matches:
            # Return most recent
            return str(sorted(matches, key=lambda x: x.stat().st_mtime, reverse=True)[0])

    return None


def is_indeed_url(url: str) -> bool:
    """Check if URL is from Indeed"""
    return "indeed.com" in url.lower()


def build_task(job: dict, resume_path: str | None) -> str:
    """Build task prompt for Browser-Use agent"""

    resume_instruction = ""
    if resume_path:
        resume_instruction = f"""
RESUME UPLOAD (CRITICAL):
Do NOT use any pre-filled or saved resume from the Indeed account.
You MUST upload this specific custom resume file: {resume_path}
- If a resume is already attached/pre-filled, click "Replace resume" or "Remove" to delete it first
- Then click "Upload resume" or "Upload new resume" and select: {resume_path}
- If there is also a cover letter upload option, skip it
- Make sure the uploaded filename shows the custom file, NOT a default Indeed resume
"""

    task = f"""
Go to this job posting and apply using Easy Apply: {job.get('url')}

IMPORTANT RULES:
- ONLY proceed if you see "Easy Apply" or a simple "Apply" button on Indeed
- If you're asked to login, sign in, or create an account - STOP and say "NEEDS_LOGIN"
- If you're redirected to an external site (not indeed.com) - STOP and say "EXTERNAL_SITE"
- If a dialog box or popup appears that blocks the form, close it immediately before continuing
- Complete ALL pages of the application form until you see a confirmation
- On each page, make sure ALL required fields/questions are answered BEFORE clicking Continue
- Answer all Yes/No qualification questions with "Yes" one by one

STEPS:
1. Go to the job URL
2. Find and click "Easy Apply" or "Apply now" button
3. Fill in these fields if they appear:
   - Full Name: {APPLICANT['name']}
   - Email: {APPLICANT['email']}
   - Phone: {APPLICANT['phone']}
   - City/Location: {APPLICANT['location']}
{resume_instruction}
4. Click Continue on each page after verifying all fields are filled
5. On voluntary self-identification pages, select "I do not want to answer" for each question
6. Click Submit/Apply/Review until application is fully submitted
7. Wait for and screenshot the confirmation page

When done, say "SUCCESS" if application submitted, or explain why it failed.
"""
    return task


async def apply_to_job(job: dict) -> tuple[bool, str]:
    """Apply to a single job using Browser-Use Cloud with US residential proxy"""

    job_url = job.get('url', '')
    job_title = job.get('title', 'Unknown')
    job_company = job.get('company', 'Unknown')

    print(f"\n{'='*60}")
    print(f"Job: {job_title} at {job_company}")
    print(f"URL: {job_url}")
    print(f"{'='*60}")

    # Check if Indeed URL
    if not is_indeed_url(job_url):
        print("SKIP: Not an Indeed URL")
        return False, "not_indeed_url"

    # Send through n8n factory if no resume exists yet
    resume_path = get_resume_path(job)
    if not resume_path:
        print("No resume found — sending to n8n factory...")
        factory_result = send_to_factory(job)
        if factory_result and factory_result.get('files', {}).get('resume'):
            resume_filename = factory_result['files']['resume']
            resume_path = str(OUTPUT_DIR / resume_filename)
            print(f"Resume generated: {resume_path}")
        else:
            print("WARNING: Factory failed to generate resume, continuing without one")

    # Get resume path
    if resume_path:
        print(f"Resume: {resume_path}")
    else:
        print("Resume: None found")

    # Build task
    task = build_task(job, resume_path)

    # Load Indeed cookies as storage state file
    storage_state_path = load_cookies_as_storage_state()
    if storage_state_path:
        print(f"Loaded cookies from {storage_state_path}")
    else:
        print("WARNING: No cookies found - may need to login")

    # Create cloud browser session with US residential proxy
    browser_use_api_key = os.getenv("BROWSER_USE_API_KEY")
    os.environ["BROWSER_USE_API_KEY"] = browser_use_api_key

    browser = BrowserSession(
        use_cloud=True,
        cloud_proxy_country_code='us',
        storage_state=storage_state_path,
    )

    # Pre-start the browser so we can upload files to the cloud session
    await browser.start()

    # Upload resume to cloud browser session if we have one
    cloud_resume_name = None
    if resume_path:
        # Extract session ID from the CDP URL (format: wss://SESSION_ID.cdpN.browser-use.com)
        cdp_url = browser.browser_profile.cdp_url or ""
        session_match = re.search(r'wss://([^.]+)\.cdp', cdp_url)
        if session_match:
            cloud_session_id = session_match.group(1)
            print(f"Cloud session: {cloud_session_id}")
            cloud_resume_name = await upload_file_to_cloud_session(cloud_session_id, resume_path)

    # Set available file paths for the agent
    file_paths = []
    if cloud_resume_name:
        file_paths.append(cloud_resume_name)
    elif resume_path:
        file_paths.append(resume_path)

    # Create agent — use Browser-Use's native model for AI decisions
    agent = Agent(
        task=task,
        browser_session=browser,
        use_vision=True,
        available_file_paths=file_paths,
        max_failures=10,        # Tolerate transient LLM API errors
        max_actions_per_step=5, # Allow more actions per step for complex forms
    )

    try:
        print("Starting Browser-Use Cloud agent...")
        result = await agent.run()

        # Parse result - use regex on string representation (most reliable)
        result_str = str(result)
        final_content = ""

        # Look for the done action's extracted_content
        done_pattern = r"is_done=True.*?extracted_content='([^']+)'"
        matches = re.findall(done_pattern, result_str, re.DOTALL)
        if matches:
            final_content = matches[-1]
        else:
            # Fallback: any extracted_content that looks like a status
            status_match = re.search(r"extracted_content='(NEEDS_LOGIN|EXTERNAL_SITE|COMPLEX_FORM|SUCCESS)'", result_str)
            if status_match:
                final_content = status_match.group(1)

        print(f"Result: {final_content or 'No clear status found'}")

        # Check result based on extracted content
        final_upper = final_content.upper()

        if "NEEDS_LOGIN" in final_upper:
            return False, "needs_login"
        elif "EXTERNAL_SITE" in final_upper:
            return False, "external_site"
        elif "SUCCESS" in final_upper or "SUBMITTED" in final_upper or "APPLIED" in final_upper:
            return True, "applied"
        elif final_content:
            return False, final_content[:200]
        else:
            return False, "incomplete"

    except Exception as e:
        print(f"Error: {e}")
        return False, str(e)[:200]

    finally:
        # Clean up browser session
        try:
            await browser.close()
        except:
            pass


async def main(max_jobs: int = 1, dry_run: bool = False):
    """Main entry point"""

    print("\n" + "="*60)
    print("Indeed Easy Apply Bot - Cloud + US Residential Proxy")
    print("="*60)

    # Load queues
    pending = load_queue("pending")
    applied = load_queue("applied")
    failed = load_queue("failed")

    print(f"\nQueue status:")
    print(f"  Pending: {len(pending)}")
    print(f"  Applied: {len(applied)}")
    print(f"  Failed: {len(failed)}")

    if not pending:
        print("\nNo jobs in pending queue!")
        return

    if dry_run:
        print("\n[DRY RUN MODE - No actual applications]")
        for job in pending[:max_jobs]:
            print(f"\nWould apply to: {job.get('title')} at {job.get('company')}")
            print(f"  URL: {job.get('url')}")
            print(f"  Is Indeed: {is_indeed_url(job.get('url', ''))}")
            resume = get_resume_path(job)
            print(f"  Resume: {resume or 'None found'}")
        return

    # Process jobs
    jobs_processed = 0

    while pending and jobs_processed < max_jobs:
        job = pending.pop(0)

        success, reason = await apply_to_job(job)

        # Record result
        job['apply_result'] = reason
        job['apply_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

        if success:
            print(f"\n[SUCCESS] Applied to {job.get('company')}")
            applied.append(job)
        else:
            print(f"\n[FAILED] {job.get('company')}: {reason}")
            failed.append(job)

        # Save queues after each job
        save_queue("pending", pending)
        save_queue("applied", applied)
        save_queue("failed", failed)

        jobs_processed += 1

        # Rate limiting
        if pending and jobs_processed < max_jobs:
            print(f"\nWaiting {DELAY_BETWEEN_JOBS}s before next job...")
            await asyncio.sleep(DELAY_BETWEEN_JOBS)

    # Final summary
    print("\n" + "="*60)
    print("Session Complete")
    print("="*60)
    print(f"Processed: {jobs_processed}")
    print(f"Applied: {len(applied)}")
    print(f"Failed: {len(failed)}")
    print(f"Remaining: {len(pending)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Indeed Easy Apply Bot")
    parser.add_argument("--max", type=int, default=1, help="Max jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    args = parser.parse_args()

    asyncio.run(main(max_jobs=args.max, dry_run=args.dry_run))
