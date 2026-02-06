#!/usr/bin/env python3
"""
Test Script - Run single job application with detailed metrics
Usage: python test_single_job.py --job-index 0
"""

import sys
import time
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from applier import (
    load_queue, save_queue, apply_to_job, is_valid_job,
    is_blocked_ats, get_resume_path, load_cookies_as_storage_state,
    APPLICANT
)
from utils import check_cookie_health, detect_application_success


async def run_test(job_index: int, skip_health_check: bool = False):
    """Run a single job application with detailed instrumentation."""

    start_time = time.time()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load pending jobs
    pending = load_queue("pending")
    if not pending:
        print("ERROR: No pending jobs in queue!")
        return

    if job_index >= len(pending):
        print(f"ERROR: Job index {job_index} out of range (max: {len(pending)-1})")
        return

    job = pending[job_index]
    company = job.get('company', 'Unknown')
    title = job.get('title', 'Unknown')

    # Create report
    report = {
        "job_index": job_index,
        "company": company,
        "title": title,
        "url": job.get('url', ''),
        "timestamp": timestamp,
        "phases": [],
        "result": None,
        "error": None,
        "total_time_seconds": 0
    }

    print("\n" + "="*70)
    print(f"TEST RUN: {title} at {company}")
    print(f"Job Index: {job_index}")
    print(f"URL: {job.get('url', '')[:60]}...")
    print("="*70)

    def log_phase(name, start):
        duration = round(time.time() - start, 2)
        report["phases"].append({"name": name, "duration_seconds": duration})
        print(f"  [{name}] {duration}s")

    try:
        # Phase 1: Validation
        phase_start = time.time()
        valid, reason = is_valid_job(job)
        blocked, domain = is_blocked_ats(job.get('url', ''))
        resume_path = get_resume_path(job)
        log_phase("validation", phase_start)

        print(f"\n  Validation Results:")
        print(f"    Valid: {valid} ({reason})")
        print(f"    Blocked ATS: {blocked} ({domain})")
        print(f"    Resume: {resume_path or 'NOT FOUND'}")

        if not valid:
            report["result"] = "INVALID_JOB"
            report["error"] = reason
            return report

        if blocked:
            report["result"] = "BLOCKED_ATS"
            report["error"] = domain
            return report

        # Phase 2: Cookie Health Check (optional)
        if not skip_health_check:
            phase_start = time.time()
            print("\n  [HEALTH CHECK] Validating Indeed session...")
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                storage_state_path = load_cookies_as_storage_state()
                context = await browser.new_context(
                    storage_state=storage_state_path if storage_state_path else None,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                session_valid = await check_cookie_health(page)
                await browser.close()

            log_phase("health_check", phase_start)
            print(f"    Session Valid: {session_valid}")

            if not session_valid:
                print("    WARNING: Session may be expired!")
                report["phases"][-1]["warning"] = "session_expired"

        # Phase 3: Application
        phase_start = time.time()
        print("\n  [APPLYING] Starting Browser-Use agent...")
        print("-"*50)

        success, result_reason = await apply_to_job(job)

        log_phase("application", phase_start)

        # Record result
        report["result"] = "SUCCESS" if success else "FAILED"
        report["error"] = None if success else result_reason

        print("-"*50)
        print(f"\n  Application Result: {'SUCCESS' if success else 'FAILED'}")
        if not success:
            print(f"  Failure Reason: {result_reason}")

    except Exception as e:
        report["result"] = "ERROR"
        report["error"] = str(e)
        print(f"\n  EXCEPTION: {e}")

    finally:
        report["total_time_seconds"] = round(time.time() - start_time, 2)

        # Save report
        report_dir = Path("/root/job_bot/test_results")
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f"test_{timestamp}_{company[:20].replace(' ', '_')}.json"
        report_path.write_text(json.dumps(report, indent=2))

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"  Result: {report['result']}")
        print(f"  Total Time: {report['total_time_seconds']}s")
        print(f"  Report: {report_path}")
        print("="*70)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test single job application")
    parser.add_argument("--job-index", type=int, default=0, help="Index of job in pending queue (0-based)")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip cookie health check")
    parser.add_argument("--list", action="store_true", help="List pending jobs and exit")
    args = parser.parse_args()

    if args.list:
        pending = load_queue("pending")
        print(f"\nPending Jobs ({len(pending)} total):\n")
        for i, job in enumerate(pending[:20]):
            print(f"  [{i}] {job.get('title', 'Unknown')[:40]} at {job.get('company', 'Unknown')[:25]}")
        if len(pending) > 20:
            print(f"  ... and {len(pending)-20} more")
    else:
        asyncio.run(run_test(args.job_index, args.skip_health_check))
