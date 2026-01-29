#!/usr/bin/env python3
"""
Job Bot Orchestrator
====================
Runs the complete job application pipeline:
  1. Scrape jobs (simple_hunter.py)
  2. Score jobs (Haiku)
  3. Send to n8n factory for resume generation (Opus)
  4. Apply via Browser-Use Cloud

Usage:
    python3 orchestrator.py --dry-run              # Scrape + score only
    python3 orchestrator.py --max-factory 20       # Cap jobs sent to factory
    python3 orchestrator.py --max-apply 10         # Cap applications per run
    python3 orchestrator.py --parallel 2           # Run N Browser-Use agents concurrently
    python3 orchestrator.py --remote-only          # Only process remote jobs
    python3 orchestrator.py --local-only           # Only process local jobs
"""

import asyncio
import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ============================================
# CONFIGURATION
# ============================================

QUEUE_DIR = Path("/root/job_bot/queue")
LOG_DIR = Path("/root/job_bot/logs")
OUTPUT_DIR = Path("/root/output")
STATUS_FILE = Path("/root/job_bot/PROJECT_STATUS.md")

# Cost estimates
COSTS = {
    "haiku_per_job": 0.001,      # Scoring
    "opus_per_job": 0.30,        # Resume generation
    "browser_use_per_job": 0.08, # Application
}

# ============================================
# LOGGING
# ============================================

LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# QUEUE HELPERS
# ============================================

def load_queue(name: str) -> list:
    path = QUEUE_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, ValueError):
            return []
    return []


def save_queue(name: str, data: list):
    path = QUEUE_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))


def get_queue_stats() -> Dict:
    return {
        "pending": len(load_queue("pending")),
        "applied": len(load_queue("applied")),
        "failed": len(load_queue("failed")),
        "skipped": len(load_queue("skipped")),
    }

# ============================================
# PHASE 1: SCRAPER + SCORER
# ============================================

def run_scraper(
    dry_run: bool = False,
    max_factory: int = None,
    remote_only: bool = False,
    local_only: bool = False,
) -> Dict:
    """Run the job scraper (simple_hunter.py)"""
    logger.info("=" * 60)
    logger.info("PHASE 1: SCRAPING & SCORING")
    logger.info("=" * 60)

    cmd = ["python3", "/root/job_bot/agent/simple_hunter.py"]

    if dry_run:
        cmd.append("--dry-run")
    if max_factory:
        cmd.extend(["--max", str(max_factory)])
    if remote_only:
        cmd.append("--remote-only")
    elif local_only:
        cmd.append("--local-only")

    logger.info(f"Running: {' '.join(cmd)}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd="/root/job_bot/agent",
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )

        duration = time.time() - start_time
        logger.info(f"Scraper completed in {duration:.1f}s")

        # Parse output for stats
        output = result.stdout + result.stderr
        scored = 0
        passed = 0
        skipped = 0

        for line in output.split("\n"):
            if "Scored:" in line:
                try:
                    scored = int(line.split("Scored:")[1].split()[0])
                except:
                    pass
            if "Passed" in line and "YES/MAYBE" in line:
                try:
                    passed = int(line.split(":")[1].split()[0])
                except:
                    pass
            if "Skipped" in line and "NO" in line:
                try:
                    skipped = int(line.split(":")[1].split()[0])
                except:
                    pass

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "scored": scored,
            "passed": passed,
            "skipped": skipped,
            "cost_estimate": scored * COSTS["haiku_per_job"],
        }

    except subprocess.TimeoutExpired:
        logger.error("Scraper timed out after 30 minutes")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        return {"success": False, "error": str(e)}

# ============================================
# PHASE 2: APPLIER
# ============================================

async def run_applier(
    max_apply: int = 10,
    parallel: int = 1,
) -> Dict:
    """Run the job applier (applier.py)"""
    logger.info("=" * 60)
    logger.info("PHASE 2: APPLYING")
    logger.info("=" * 60)

    pending = load_queue("pending")
    if not pending:
        logger.info("No jobs in pending queue - skipping apply phase")
        return {"success": True, "applied": 0, "failed": 0}

    jobs_to_process = min(len(pending), max_apply)
    logger.info(f"Processing {jobs_to_process} jobs (parallel: {parallel})")

    start_time = time.time()
    applied_count = 0
    failed_count = 0

    # Run in batches based on parallelism
    for batch_start in range(0, jobs_to_process, parallel):
        batch_size = min(parallel, jobs_to_process - batch_start)
        logger.info(f"Batch {batch_start//parallel + 1}: Processing {batch_size} jobs...")

        # Run applier for this batch
        cmd = [
            "python3", "/root/job_bot/bot/applier.py",
            "--max", str(batch_size),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd="/root/job_bot",
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per batch
            )

            # Count results
            output = result.stdout + result.stderr
            if "[SUCCESS]" in output:
                applied_count += output.count("[SUCCESS]")
            if "[FAILED]" in output:
                failed_count += output.count("[FAILED]")

            logger.info(f"Batch complete: {applied_count} applied, {failed_count} failed so far")

        except subprocess.TimeoutExpired:
            logger.error("Applier batch timed out")
            failed_count += batch_size
        except Exception as e:
            logger.error(f"Applier error: {e}")
            failed_count += batch_size

        # Brief pause between batches
        if batch_start + batch_size < jobs_to_process:
            await asyncio.sleep(5)

    duration = time.time() - start_time

    return {
        "success": True,
        "duration": duration,
        "applied": applied_count,
        "failed": failed_count,
        "cost_estimate": (applied_count + failed_count) * COSTS["browser_use_per_job"],
    }

# ============================================
# COST TRACKING
# ============================================

def calculate_run_costs(scraper_result: Dict, applier_result: Dict) -> Dict:
    """Calculate total costs for this run"""

    haiku_cost = scraper_result.get("cost_estimate", 0)

    # Factory cost (Opus) - estimate based on passed jobs
    factory_jobs = scraper_result.get("passed", 0)
    opus_cost = factory_jobs * COSTS["opus_per_job"]

    # Browser-Use cost
    browser_cost = applier_result.get("cost_estimate", 0)

    total = haiku_cost + opus_cost + browser_cost

    return {
        "haiku_scoring": round(haiku_cost, 3),
        "opus_factory": round(opus_cost, 2),
        "browser_use": round(browser_cost, 2),
        "total": round(total, 2),
    }


def log_run_summary(
    scraper_result: Dict,
    applier_result: Dict,
    costs: Dict,
    args: argparse.Namespace,
):
    """Log final run summary"""
    logger.info("=" * 60)
    logger.info("RUN SUMMARY")
    logger.info("=" * 60)

    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if args.remote_only:
        logger.info("Filter: REMOTE ONLY")
    elif args.local_only:
        logger.info("Filter: LOCAL ONLY")

    logger.info("")
    logger.info("SCRAPING:")
    logger.info(f"  Jobs scored: {scraper_result.get('scored', 'N/A')}")
    logger.info(f"  Passed (YES/MAYBE): {scraper_result.get('passed', 'N/A')}")
    logger.info(f"  Skipped (NO): {scraper_result.get('skipped', 'N/A')}")

    if not args.dry_run:
        logger.info("")
        logger.info("APPLYING:")
        logger.info(f"  Applied: {applier_result.get('applied', 0)}")
        logger.info(f"  Failed: {applier_result.get('failed', 0)}")

    logger.info("")
    logger.info("COSTS:")
    logger.info(f"  Haiku (scoring): ${costs['haiku_scoring']}")
    if not args.dry_run:
        logger.info(f"  Opus (factory):  ${costs['opus_factory']}")
        logger.info(f"  Browser-Use:     ${costs['browser_use']}")
        logger.info(f"  TOTAL:           ${costs['total']}")

    # Queue status
    stats = get_queue_stats()
    logger.info("")
    logger.info("QUEUE STATUS:")
    logger.info(f"  Pending: {stats['pending']}")
    logger.info(f"  Applied: {stats['applied']}")
    logger.info(f"  Failed:  {stats['failed']}")
    logger.info(f"  Skipped: {stats['skipped']}")

    logger.info("=" * 60)

# ============================================
# MAIN
# ============================================

async def main():
    parser = argparse.ArgumentParser(
        description='Job Bot Orchestrator - Full Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 orchestrator.py --dry-run              # Preview mode
  python3 orchestrator.py --max-factory 20       # Send 20 jobs to factory
  python3 orchestrator.py --max-apply 10         # Apply to 10 jobs
  python3 orchestrator.py --remote-only          # Remote jobs only
  python3 orchestrator.py --parallel 2           # 2 concurrent applications
        """
    )

    parser.add_argument(
        '--dry-run', action='store_true',
        help='Scrape and score only - no factory or applications'
    )
    parser.add_argument(
        '--max-factory', type=int, default=50,
        help='Maximum jobs to send to n8n factory (default: 50)'
    )
    parser.add_argument(
        '--max-apply', type=int, default=10,
        help='Maximum applications per run (default: 10)'
    )
    parser.add_argument(
        '--parallel', type=int, default=1, choices=[1, 2, 3, 4],
        help='Number of concurrent Browser-Use agents (default: 1)'
    )
    parser.add_argument(
        '--remote-only', action='store_true',
        help='Only search for and apply to remote jobs'
    )
    parser.add_argument(
        '--local-only', action='store_true',
        help='Only search for and apply to local jobs'
    )
    parser.add_argument(
        '--skip-scrape', action='store_true',
        help='Skip scraping, only run applier on existing queue'
    )

    args = parser.parse_args()

    # Validate args
    if args.remote_only and args.local_only:
        logger.error("Cannot use both --remote-only and --local-only")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("JOB BOT ORCHESTRATOR STARTING")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    scraper_result = {}
    applier_result = {}

    # Phase 1: Scrape + Score
    if not args.skip_scrape:
        scraper_result = run_scraper(
            dry_run=args.dry_run,
            max_factory=args.max_factory if not args.dry_run else None,
            remote_only=args.remote_only,
            local_only=args.local_only,
        )

        if not scraper_result.get("success"):
            logger.error("Scraper failed - aborting")
            sys.exit(1)
    else:
        logger.info("Skipping scrape phase (--skip-scrape)")
        scraper_result = {"scored": 0, "passed": 0, "skipped": 0, "cost_estimate": 0}

    # Phase 2: Apply (skip in dry run mode)
    if not args.dry_run:
        applier_result = await run_applier(
            max_apply=args.max_apply,
            parallel=args.parallel,
        )
    else:
        applier_result = {"applied": 0, "failed": 0, "cost_estimate": 0}
        logger.info("Skipping apply phase (--dry-run)")

    # Calculate costs and log summary
    costs = calculate_run_costs(scraper_result, applier_result)
    log_run_summary(scraper_result, applier_result, costs, args)

    logger.info("Orchestrator complete!")


if __name__ == "__main__":
    asyncio.run(main())
