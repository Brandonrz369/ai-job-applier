#!/usr/bin/env python3
"""
External ATS Site Tester
=========================
Tests Browser-Use Cloud's ability to apply on external ATS sites
(Workday, Greenhouse, Lever, iCIMS, company portals, etc.)

Usage:
    python3 test_external.py --url "https://indeed.com/viewjob?jk=xxx"
    python3 test_external.py --url "https://indeed.com/viewjob?jk=xxx" --resume /path/to/resume.pdf
    python3 test_external.py --test-all   # Test all external_site jobs from failed.json
"""

import asyncio
import json
import re
import time
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv(Path("/root/job_bot/agent/.env"))

from browser_use import Agent
from browser_use.browser.session import BrowserSession
from browser_use_sdk import AsyncBrowserUse
import aiohttp

# ============ CONFIG ============
QUEUE_DIR = Path("/root/job_bot/queue")
OUTPUT_DIR = Path("/root/output")
LOG_DIR = Path("/root/job_bot/logs")
RESULTS_FILE = LOG_DIR / "external_test_results.json"
COOKIES_FILE = Path("/root/job_bot/agent/cookies.json")
STORAGE_STATE_FILE = Path("/root/job_bot/agent/storage_state_test.json")

# Applicant info
APPLICANT = {
    "name": "Brandon Ruiz",
    "email": "brandonlruiz98@gmail.com",
    "phone": "775-530-8234",
    "location": "Anaheim, CA",
    "linkedin": "https://linkedin.com/in/brandonruiz98",
}

# ATS patterns for detection
ATS_PATTERNS = {
    "workday": ["myworkdayjobs.com", "wd1.myworkdayjobs", "wd3.myworkdayjobs", "wd5.myworkdayjobs"],
    "greenhouse": ["greenhouse.io", "boards.greenhouse"],
    "lever": ["lever.co", "jobs.lever.co"],
    "icims": ["icims.com", "careers-"],
    "taleo": ["taleo.net", "recruitingsite.com"],
    "jobvite": ["jobvite.com", "jobs.jobvite"],
    "smartrecruiters": ["smartrecruiters.com"],
    "bamboohr": ["bamboohr.com"],
    "paycom": ["paycomonline.net"],
    "ultipro": ["ultipro.com"],
    "adp": ["adp.com"],
    "successfactors": ["successfactors.com", "successfactors.eu"],
    "brassring": ["brassring.com"],
    "governmentjobs": ["governmentjobs.com", "neogov.com"],
    "apply.indeed": ["apply.indeed.com"],  # Indeed's own external apply
}


def load_cookies_as_storage_state() -> str | None:
    """Convert cookies.json to Playwright storage state file"""
    if not COOKIES_FILE.exists():
        print("  [COOKIES] No cookies.json found")
        return None

    raw_cookies = json.loads(COOKIES_FILE.read_text())

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

        if cookie.get("expirationDate"):
            pw_cookie["expires"] = cookie.get("expirationDate")

        same_site = cookie.get("sameSite", "Lax")
        if same_site == "no_restriction":
            same_site = "None"
        elif same_site == "unspecified":
            same_site = "Lax"
        pw_cookie["sameSite"] = same_site

        pw_cookies.append(pw_cookie)

    storage_state = {"cookies": pw_cookies, "origins": []}
    STORAGE_STATE_FILE.write_text(json.dumps(storage_state, indent=2))
    print(f"  [COOKIES] Loaded {len(pw_cookies)} cookies")
    return str(STORAGE_STATE_FILE)


def detect_ats_type(url: str) -> str:
    """Detect ATS type from URL"""
    url_lower = url.lower()
    for ats_name, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            if pattern in url_lower:
                return ats_name
    return "unknown"


def load_test_results() -> list:
    """Load existing test results"""
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text())
        except:
            return []
    return []


def save_test_results(results: list):
    """Save test results"""
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


async def upload_file_to_cloud(session_id: str, file_path: str) -> str | None:
    """Upload file to Browser-Use Cloud session"""
    api_key = os.getenv("BROWSER_USE_API_KEY")
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        print(f"  [UPLOAD] File not found: {file_path}")
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
                    print(f"  [UPLOAD] Success: {file_name} ({file_size} bytes)")
                    return presigned.file_name
                else:
                    print(f"  [UPLOAD] Failed: HTTP {resp.status}")
                    return None
    except Exception as e:
        print(f"  [UPLOAD] Error: {e}")
        return None


def build_external_task(job_url: str, resume_path: str | None) -> str:
    """Build task for external ATS application"""

    resume_instruction = ""
    if resume_path:
        resume_instruction = f"""
RESUME UPLOAD:
- When you see a file upload field for resume, upload: {resume_path}
- If asked to paste resume text, explain that you have a PDF to upload instead
- Do NOT create an account just to upload a resume if there's a guest apply option
"""

    task = f"""
Navigate to this job posting and attempt to apply: {job_url}

PHASE 1 - DISCOVERY:
1. Go to the job URL on Indeed
2. Click the "Apply" or "Apply now" button
3. If redirected to an external site, note the URL and continue
4. IMPORTANT: Report what site/ATS you're now on (Workday, Greenhouse, Lever, etc.)

PHASE 2 - APPLICATION ATTEMPT:
Try to complete the application. Handle these scenarios:

IF ACCOUNT REQUIRED:
- Look for "Apply as Guest" or "Continue without account" option first
- If no guest option exists, report "ACCOUNT_REQUIRED" and stop
- Do NOT create accounts

IF MULTI-PAGE FORM:
- Fill each page with this info:
  - Name: {APPLICANT['name']}
  - Email: {APPLICANT['email']}
  - Phone: {APPLICANT['phone']}
  - Location/City: {APPLICANT['location']}
  - LinkedIn: {APPLICANT['linkedin']}
- For work history questions, say "See attached resume"
- For Yes/No screening questions, answer "Yes" unless clearly wrong
- For voluntary demographics, select "Prefer not to say" or skip
{resume_instruction}

IF COMPLEX FORM (10+ fields or multiple sections):
- Try to complete it anyway
- If it takes more than 15 steps, report "COMPLEX_FORM" with progress made

PHASE 3 - REPORT:
After attempting, provide a structured report:
- ATS_TYPE: [workday/greenhouse/lever/icims/taleo/other]
- FINAL_URL: [the URL you ended up on]
- ACCOUNT_NEEDED: [yes/no]
- STEPS_TAKEN: [number]
- OUTCOME: [SUCCESS/ACCOUNT_REQUIRED/COMPLEX_FORM/BLOCKED/ERROR]
- NOTES: [any important observations]

Be thorough but efficient. Document everything you see.
"""
    return task


async def test_external_job(
    job_url: str,
    resume_path: str | None = None,
    job_info: dict = None
) -> dict:
    """Test applying to a single external job"""

    start_time = time.time()
    result = {
        "job_url": job_url,
        "company": job_info.get("company", "Unknown") if job_info else "Unknown",
        "title": job_info.get("title", "Unknown") if job_info else "Unknown",
        "resume_used": resume_path,
        "started_at": datetime.now().isoformat(),
        "ats_type": "pending",
        "outcome": "pending",
        "steps": 0,
        "cost_estimate": 0.0,
        "duration_seconds": 0,
        "notes": "",
        "final_url": "",
        "error": None,
    }

    print(f"\n{'='*70}")
    print(f"TESTING: {result['title']} at {result['company']}")
    print(f"URL: {job_url}")
    print(f"Resume: {resume_path or 'None'}")
    print(f"{'='*70}")

    # Load Indeed cookies
    storage_state_path = load_cookies_as_storage_state()

    # Create browser session with cookies
    browser = BrowserSession(
        use_cloud=True,
        cloud_proxy_country_code='us',
        storage_state=storage_state_path,
    )

    try:
        await browser.start()
        print("[BROWSER] Cloud session started")

        # Upload resume if provided
        cloud_resume = None
        if resume_path:
            cdp_url = browser.browser_profile.cdp_url or ""
            session_match = re.search(r'wss://([^.]+)\.cdp', cdp_url)
            if session_match:
                session_id = session_match.group(1)
                print(f"[SESSION] ID: {session_id}")
                cloud_resume = await upload_file_to_cloud(session_id, resume_path)

        # Build task
        file_paths = [cloud_resume] if cloud_resume else ([resume_path] if resume_path else [])
        task = build_external_task(job_url, cloud_resume or resume_path)

        # Create and run agent
        agent = Agent(
            task=task,
            browser_session=browser,
            use_vision=True,
            available_file_paths=file_paths,
            max_failures=5,
            max_actions_per_step=10,
        )

        print("[AGENT] Starting...")
        agent_result = await agent.run()

        # Parse result
        result_str = str(agent_result)

        # Try to extract structured info from agent output
        # Look for ATS type
        for ats_name in ATS_PATTERNS.keys():
            if ats_name.upper() in result_str.upper() or ats_name in result_str.lower():
                result["ats_type"] = ats_name
                break

        # Look for outcome keywords
        if "SUCCESS" in result_str.upper():
            result["outcome"] = "success"
        elif "ACCOUNT_REQUIRED" in result_str.upper() or "CREATE ACCOUNT" in result_str.upper():
            result["outcome"] = "account_required"
        elif "COMPLEX_FORM" in result_str.upper():
            result["outcome"] = "complex_form"
        elif "BLOCKED" in result_str.upper():
            result["outcome"] = "blocked"
        else:
            result["outcome"] = "incomplete"

        # Try to find final URL
        url_match = re.search(r'FINAL_URL:\s*(\S+)', result_str)
        if url_match:
            result["final_url"] = url_match.group(1)

        # Count steps (approximate)
        step_matches = re.findall(r'step_\d+|Step \d+', result_str, re.IGNORECASE)
        result["steps"] = len(step_matches) if step_matches else 10  # estimate

        # Extract any useful notes
        notes_match = re.search(r'NOTES?:\s*(.+?)(?:\n|$)', result_str, re.IGNORECASE)
        if notes_match:
            result["notes"] = notes_match.group(1)[:500]

        print(f"\n[RESULT] ATS: {result['ats_type']}, Outcome: {result['outcome']}")

    except Exception as e:
        result["outcome"] = "error"
        result["error"] = str(e)[:500]
        print(f"[ERROR] {e}")

    finally:
        try:
            await browser.close()
        except:
            pass

    # Calculate metrics
    result["duration_seconds"] = round(time.time() - start_time, 1)
    # Cost estimate: $0.01 init + $0.002/step + $0.015 proxy
    result["cost_estimate"] = round(0.01 + (result["steps"] * 0.002) + 0.015, 3)

    print(f"[METRICS] Duration: {result['duration_seconds']}s, Est. Cost: ${result['cost_estimate']}")

    return result


async def test_all_external_jobs(max_jobs: int = 5):
    """Test all external_site jobs from failed.json"""

    # Load failed jobs
    failed_path = QUEUE_DIR / "failed.json"
    if not failed_path.exists():
        print("No failed.json found")
        return

    failed_jobs = json.loads(failed_path.read_text())

    # Filter for external_site jobs
    external_jobs = [
        j for j in failed_jobs
        if j.get("apply_result") == "external_site"
    ]

    print(f"\nFound {len(external_jobs)} external_site jobs")

    if not external_jobs:
        print("No external_site jobs to test")
        return

    # Load existing results
    results = load_test_results()
    tested_urls = {r["job_url"] for r in results}

    # Test jobs
    jobs_to_test = [j for j in external_jobs if j.get("url") not in tested_urls][:max_jobs]

    print(f"Testing {len(jobs_to_test)} jobs (skipping {len(external_jobs) - len(jobs_to_test)} already tested)")

    for i, job in enumerate(jobs_to_test, 1):
        print(f"\n[{i}/{len(jobs_to_test)}] Testing {job.get('company', 'Unknown')}...")

        # Find resume if available
        resume_path = None
        app_num = job.get("application_number")
        if app_num:
            for pattern in [f"*_{app_num}_Resume.pdf", "*_Resume.pdf"]:
                matches = list(OUTPUT_DIR.glob(pattern))
                if matches:
                    resume_path = str(matches[0])
                    break

        result = await test_external_job(
            job_url=job.get("url"),
            resume_path=resume_path,
            job_info=job,
        )

        results.append(result)
        save_test_results(results)

        # Brief pause between tests
        if i < len(jobs_to_test):
            print("\nPausing 5s before next test...")
            await asyncio.sleep(5)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for r in results[-len(jobs_to_test):]:
        status_icon = "Y" if r["outcome"] == "success" else "x"
        print(f"  [{status_icon}] {r['company'][:25]:<25} | {r['ats_type']:<12} | {r['outcome']:<15} | ${r['cost_estimate']}")

    successes = sum(1 for r in results if r["outcome"] == "success")
    print(f"\nSuccess rate: {successes}/{len(results)} ({100*successes/len(results):.0f}%)")


async def main():
    parser = argparse.ArgumentParser(description="External ATS Site Tester")
    parser.add_argument("--url", type=str, help="Single job URL to test")
    parser.add_argument("--resume", type=str, help="Path to resume PDF")
    parser.add_argument("--test-all", action="store_true", help="Test all external_site jobs from failed.json")
    parser.add_argument("--max", type=int, default=5, help="Max jobs to test (with --test-all)")
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)

    if args.url:
        result = await test_external_job(args.url, args.resume)
        print(f"\nResult: {json.dumps(result, indent=2)}")

        # Save result
        results = load_test_results()
        results.append(result)
        save_test_results(results)

    elif args.test_all:
        await test_all_external_jobs(max_jobs=args.max)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
