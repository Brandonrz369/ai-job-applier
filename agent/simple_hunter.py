#!/usr/bin/env python3
"""
Job Hunter - Simple Version
===========================
Uses jobspy to scrape Indeed/LinkedIn without browser automation.
Scores jobs with Gemini 2.5 Flash, sends passing jobs to n8n for document generation.

Usage:
    python simple_hunter.py
    python simple_hunter.py --loop
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Job scraping
from jobspy import scrape_jobs
import pandas as pd

# Scoring
from scorer import score_job, pre_filter_job, is_duplicate

# ============================================
# CONFIGURATION
# ============================================

# API endpoint
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/incoming-job')

# Search settings
SEARCH_TERMS = [
    # Core IT Support (strongest match)
    "IT Support",
    "Help Desk",
    "Desktop Support",
    "IT Technician",
    "IT Specialist",
    "Technical Support",
    "Service Desk",
    "Computer Technician",

    # Infrastructure/Admin
    "Systems Administrator",
    "Network Technician",
    "Network Administrator",
    "IT Administrator",
    "Infrastructure Technician",
    "Junior Sysadmin",
    "Junior Systems Administrator",
    "Junior Network Engineer",

    # Field/MSP
    "Field Service Technician",
    "MSP Technician",
    "IT Field Engineer",

    # Specialty (candidate has direct experience)
    "VoIP Technician",
    "NOC Technician",
    "Firewall Administrator",
    "M365 Administrator",
    "Endpoint Technician",

    # Stretch (entry-level only)
    "Junior Security Analyst",
    "SOC Analyst",
    "IT Coordinator",
    "IT Project Coordinator",
    "Implementation Specialist",
]

LOCATION = 'Anaheim, CA'
DISTANCE_MILES = 35  # Search radius in miles
RESULTS_PER_SEARCH = 50  # Get more results per term, dedup handles overlap
HOURS_OLD = 72  # Jobs posted in last 72 hours
MAX_JOBS_TOTAL = 50  # Stop after this many jobs sent to factory
PARALLEL_SEARCHES = 3  # Number of concurrent JobSpy searches (VPS has 3 cores)
PARALLEL_SCORING = 20  # Number of concurrent job scoring calls

# Remote settings (ratio disabled - keep all remote jobs)
REMOTE_RATIO = 1.0  # Set to 1.0 to accept ALL remote jobs (no filtering)
INCLUDE_REMOTE_SEARCHES = True  # Add "remote" suffix searches on Indeed
INCLUDE_LINKEDIN = False  # Disabled - LinkedIn doesn't return descriptions reliably

# Paths
OUTPUT_DIR = Path('./output')
STATS_FILE = OUTPUT_DIR / '.counter.json'
LOG_FILE = OUTPUT_DIR / 'applications.csv'
QUEUE_DIR = Path('/root/job_bot/queue')
SKIPPED_FILE = QUEUE_DIR / 'skipped.json'

# Rate limiting
DELAY_BETWEEN_JOBS = 10  # seconds
DELAY_BETWEEN_SEARCHES = 5  # seconds between search queries

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/root/job_bot/logs/hunter.log'),
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# STATS TRACKING
# ============================================

def load_stats() -> Dict:
    try:
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'total': 0, 'remote': 0, 'local': 0, 'scored_yes': 0, 'scored_no': 0, 'scored_maybe': 0}

def save_stats(stats: Dict):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def is_remote(job: pd.Series) -> bool:
    """Check if job is remote"""
    keywords = ['remote', 'work from home', 'wfh', 'anywhere']
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
    return any(kw in text for kw in keywords)

def should_apply(job: pd.Series, stats: Dict) -> bool:
    """Apply ratio logic - disabled when REMOTE_RATIO >= 1.0"""
    # If ratio is 1.0 or higher, accept all jobs (no filtering)
    if REMOTE_RATIO >= 1.0:
        return True

    if stats['total'] == 0:
        return True

    current_remote_ratio = stats['remote'] / stats['total']

    if is_remote(job):
        return current_remote_ratio < REMOTE_RATIO

    return True

# ============================================
# SKIPPED JOBS LOG
# ============================================

def load_skipped() -> list:
    if SKIPPED_FILE.exists():
        try:
            return json.loads(SKIPPED_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            return []
    return []

def save_skipped(skipped: list):
    SKIPPED_FILE.write_text(json.dumps(skipped, indent=2))

def log_skipped_job(job: pd.Series, score_result: dict):
    """Log a skipped job to skipped.json for review"""
    skipped = load_skipped()
    skipped.append({
        'title': str(job.get('title', 'Unknown')),
        'company': str(job.get('company', 'Unknown')),
        'location': str(job.get('location', '')),
        'url': str(job.get('job_url', '')),
        'score': score_result.get('score', 0),
        'recommendation': score_result.get('recommendation', 'NO'),
        'reason': score_result.get('reason', ''),
        'skipped_at': datetime.now().isoformat(),
    })
    save_skipped(skipped)

# ============================================
# N8N INTEGRATION
# ============================================

def clean_description(desc: str) -> str:
    """Clean job description for n8n - normalize whitespace and fix escapes"""
    if not desc:
        return ""
    # Fix escaped markdown characters
    desc = desc.replace('\\-', '-').replace('\\*', '*').replace('\\_', '_')
    # Normalize all whitespace to single spaces (fixes n8n JSON parsing issues)
    desc = ' '.join(desc.split())
    return desc[:3000]  # Truncate to 3000 chars

def send_to_factory(job: pd.Series) -> Dict:
    """Send job to n8n and get back PDF info"""
    import urllib.request

    payload = {
        'title': str(job.get('title', 'Unknown')),
        'company': str(job.get('company', 'Unknown')),
        'description': clean_description(str(job.get('description', ''))),
        'url': str(job.get('job_url', '')),
        'location': str(job.get('location', ''))
    }

    try:
        logger.info(f"  Sending to factory: {payload['company']} - {payload['title']}")

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            N8N_WEBHOOK_URL,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result_text = response.read().decode('utf-8')
            if result_text:
                result = json.loads(result_text)
                logger.info(f"  Factory success: Application #{result.get('application_number')}")
                return result
            else:
                logger.error(f"  Factory error: Empty response")
                return None

    except Exception as e:
        logger.error(f"  Connection failed: {e}")
        return None

# ============================================
# JOB SCRAPER
# ============================================

def search_jobs(search_term: str, location: str) -> pd.DataFrame:
    """Scrape jobs from Indeed with Easy Apply"""
    logger.info(f"Searching: '{search_term}' in '{location}'")

    try:
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=search_term,
            location=location,
            distance=DISTANCE_MILES,
            results_wanted=RESULTS_PER_SEARCH,
            hours_old=HOURS_OLD,
            country_indeed='USA',
            easy_apply=True
        )

        logger.info(f"   Found {len(jobs)} jobs")
        return jobs

    except Exception as e:
        logger.error(f"   Search failed: {e}")
        return pd.DataFrame()


def search_remote_indeed(search_term: str) -> pd.DataFrame:
    """Search Indeed for remote jobs (without easy_apply to allow is_remote)"""
    remote_term = f"{search_term} remote"
    logger.info(f"Searching remote: '{remote_term}'")

    try:
        # Note: Can't use easy_apply with is_remote on Indeed
        # So we search with "remote" in the term instead
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=remote_term,
            location="USA",  # Broader location for remote
            results_wanted=RESULTS_PER_SEARCH,
            hours_old=HOURS_OLD,
            country_indeed='USA',
            easy_apply=True  # Keep Easy Apply filter
        )

        logger.info(f"   Found {len(jobs)} remote jobs")
        return jobs

    except Exception as e:
        logger.error(f"   Remote search failed: {e}")
        return pd.DataFrame()


def search_linkedin_remote(search_term: str) -> pd.DataFrame:
    """Search LinkedIn for remote jobs"""
    logger.info(f"Searching LinkedIn remote: '{search_term}'")

    try:
        jobs = scrape_jobs(
            site_name=["linkedin"],
            search_term=search_term,
            location="USA",
            results_wanted=RESULTS_PER_SEARCH,
            hours_old=HOURS_OLD,
            is_remote=True,  # LinkedIn supports is_remote
            linkedin_fetch_description=True,  # Fetch full descriptions
        )

        logger.info(f"   Found {len(jobs)} LinkedIn remote jobs")
        return jobs

    except Exception as e:
        logger.error(f"   LinkedIn search failed: {e}")
        return pd.DataFrame()


def run_parallel_searches(search_list: List[tuple]) -> List[pd.DataFrame]:
    """Run multiple searches in parallel using ThreadPoolExecutor"""
    results = []

    def execute_search(search_tuple):
        search_type, term = search_tuple
        try:
            if search_type == 'indeed_local':
                return search_jobs(term, LOCATION)
            elif search_type == 'indeed_remote':
                return search_remote_indeed(term)
            elif search_type == 'linkedin_remote':
                return search_linkedin_remote(term)
        except Exception as e:
            logger.error(f"Search failed for {term}: {e}")
            return pd.DataFrame()

    logger.info(f"Running {len(search_list)} searches with {PARALLEL_SEARCHES} threads...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=PARALLEL_SEARCHES) as executor:
        futures = {executor.submit(execute_search, s): s for s in search_list}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None and not result.empty:
                    results.append(result)
            except Exception as e:
                logger.error(f"Search error: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Completed {len(search_list)} searches in {elapsed:.1f}s ({elapsed/len(search_list):.2f}s/search avg)")
    return results

# ============================================
# MAIN LOOP
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

def get_seen_urls() -> set:
    """Get all URLs already in any queue to avoid duplicates"""
    seen = set()
    for queue_name in ['pending', 'applied', 'failed', 'skipped']:
        for job in load_queue(queue_name):
            seen.add(job.get('url', ''))
    return seen

def score_single_job(job_data: dict) -> tuple:
    """Score a single job. Returns (job_data, score_result) for parallel processing."""
    try:
        score_result = score_job({
            'company': job_data['company'],
            'title': job_data['title'],
            'location': job_data['location'],
            'description': job_data['description'][:3000],
        })
        return (job_data, score_result)
    except Exception as e:
        logger.error(f"Error scoring {job_data.get('title', 'Unknown')}: {e}")
        return (job_data, {'score': 5, 'recommendation': 'MAYBE', 'reason': f'Error: {e}'})

def run_parallel_scoring(jobs_to_score: list) -> list:
    """Score multiple jobs in parallel. Returns list of (job_data, score_result) tuples."""
    results = []
    total = len(jobs_to_score)

    logger.info(f"Scoring {total} jobs with {PARALLEL_SCORING} parallel threads...")

    with ThreadPoolExecutor(max_workers=PARALLEL_SCORING) as executor:
        future_to_job = {executor.submit(score_single_job, job): job for job in jobs_to_score}

        completed = 0
        for future in as_completed(future_to_job):
            completed += 1
            try:
                job_data, score_result = future.result()
                results.append((job_data, score_result))

                # Log progress
                rec = score_result.get('recommendation', 'MAYBE')
                score = score_result.get('score', 5)
                logger.info(f"[{completed}/{total}] {job_data['company'][:20]} - {job_data['title'][:30]} | {score}/10 {rec}")
            except Exception as e:
                logger.error(f"Scoring failed: {e}")

    return results

def run_hunt(dry_run=False, max_factory=None):
    """Main hunting loop.

    Args:
        dry_run: If True, scrape and score only — do NOT send to n8n factory.
                 Saves passing jobs to queue/dry_run.json for review.
        max_factory: Override MAX_JOBS_TOTAL for how many jobs to send to factory.
    """
    factory_limit = max_factory if max_factory is not None else MAX_JOBS_TOTAL
    OUTPUT_DIR.mkdir(exist_ok=True)
    QUEUE_DIR.mkdir(exist_ok=True)
    Path('/root/job_bot/logs').mkdir(exist_ok=True)
    stats = load_stats()
    seen_urls = get_seen_urls()

    # Ensure stats has scoring counters
    for key in ['scored_yes', 'scored_no', 'scored_maybe']:
        if key not in stats:
            stats[key] = 0

    mode_label = "DRY RUN (score only, no factory)" if dry_run else "LIVE RUN"
    logger.info("=" * 50)
    logger.info(f"JOB HUNTER STARTING - {mode_label}")
    logger.info(f"   Location: {LOCATION}")
    logger.info(f"   Search terms: {len(SEARCH_TERMS)}")
    logger.info(f"   Remote ratio: {REMOTE_RATIO * 100}%")
    if not dry_run:
        logger.info(f"   Factory limit: {factory_limit}")
    logger.info(f"   Current stats: {stats}")
    logger.info(f"   Already seen URLs: {len(seen_urls)}")
    logger.info("=" * 50)

    total_processed = 0
    total_scored = 0
    total_skipped = 0
    total_passed = 0
    pending = load_queue('pending')
    dry_run_results = []  # For dry run output

    # Build list of all searches to run
    all_searches = []

    # Phase 1: Indeed Easy Apply (local)
    for term in SEARCH_TERMS:
        all_searches.append(('indeed_local', term))

    # Phase 2: Indeed remote searches (with "remote" in term)
    if INCLUDE_REMOTE_SEARCHES:
        # Only add remote searches for key terms (not all 44)
        remote_terms = [
            "IT Support", "Help Desk", "Desktop Support", "Technical Support",
            "Systems Administrator", "Network Administrator",
            "IT Technician", "NOC Technician",
        ]
        for term in remote_terms:
            all_searches.append(('indeed_remote', term))

    # Phase 3: LinkedIn remote searches
    if INCLUDE_LINKEDIN:
        linkedin_terms = [
            "IT Support", "Help Desk", "Systems Administrator",
            "Technical Support", "DevOps", "Automation",
        ]
        for term in linkedin_terms:
            all_searches.append(('linkedin_remote', term))

    logger.info(f"Total searches to run: {len(all_searches)} (parallel: {PARALLEL_SEARCHES})")

    # Run all searches in parallel
    all_job_results = run_parallel_searches(all_searches)

    # Combine all results into one dataframe
    if all_job_results:
        combined_jobs = pd.concat(all_job_results, ignore_index=True)
        logger.info(f"Total jobs found: {len(combined_jobs)}")
    else:
        combined_jobs = pd.DataFrame()
        logger.info("No jobs found")

    # === PHASE 1: Collect jobs to score (filter duplicates and ratio) ===
    jobs_to_score = []
    job_raw_data = {}  # Map job_url -> original job row for later processing

    pre_filtered_count = 0
    dedup_count = 0

    for _, job in combined_jobs.iterrows():
        job_url = str(job.get('job_url', ''))
        company = str(job.get('company', 'Unknown'))
        title = str(job.get('title', 'Unknown'))

        # Skip URL duplicates
        if job_url in seen_urls:
            continue

        # Skip company+title duplicates (catches Multi-Comm etc.)
        if is_duplicate(company, title):
            dedup_count += 1
            continue

        # Pre-filter: fast Python check before wasting API call
        passes, reject_reason = pre_filter_job(title)
        if not passes:
            pre_filtered_count += 1
            log_skipped_job(job, {
                'score': 0, 'recommendation': 'NO',
                'reason': f'Pre-filter: {reject_reason}'
            })
            seen_urls.add(job_url)
            continue

        # Check 75/25 ratio
        if not should_apply(job, stats):
            continue

        # Prepare job data for scoring
        job_data = {
            'job_url': job_url,
            'company': company,
            'title': title,
            'location': str(job.get('location', '')),
            'description': str(job.get('description', '')),
        }
        jobs_to_score.append(job_data)
        job_raw_data[job_url] = job
        seen_urls.add(job_url)

    logger.info(f"Pre-filtered (no API call): {pre_filtered_count}")
    logger.info(f"Company+title deduped: {dedup_count}")
    logger.info(f"Jobs to score (after dedup + pre-filter): {len(jobs_to_score)}")

    # === PHASE 2: Parallel scoring ===
    scored_results = run_parallel_scoring(jobs_to_score)

    # === PHASE 3: Process scored results ===
    for job_data, score_result in scored_results:
        job_url = job_data['job_url']
        company = job_data['company']
        title = job_data['title']
        original_job = job_raw_data.get(job_url)

        recommendation = score_result.get('recommendation', 'MAYBE')
        score = score_result.get('score', 5)
        reason = score_result.get('reason', '')
        total_scored += 1

        # Skip jobs scored NO
        if recommendation == "NO":
            log_skipped_job(original_job, score_result)
            stats['scored_no'] += 1
            total_skipped += 1
            continue

        # Track YES/MAYBE
        total_passed += 1
        if recommendation == "YES":
            stats['scored_yes'] += 1
        else:
            stats['scored_maybe'] += 1

        if dry_run:
            # Dry run: log the result but don't send to factory
            dry_run_results.append({
                'title': title,
                'company': company,
                'url': job_url,
                'location': job_data['location'],
                'description': job_data['description'],  # Store for n8n resume factory
                'score': score,
                'recommendation': recommendation,
                'reason': reason,
                'estimated_salary': score_result.get('estimated_salary', 'Unknown'),
                'scored_at': datetime.now().isoformat(),
            })
        else:
            # Live run: send to factory (but limit to factory_limit)
            if total_processed >= factory_limit:
                continue

            logger.info(f"Sending to factory: {company} - {title[:40]}")
            result = send_to_factory(original_job)

            if result:
                stats['total'] += 1
                if is_remote(original_job):
                    stats['remote'] += 1
                else:
                    stats['local'] += 1

                total_processed += 1

                queue_entry = {
                    'id': str(int(time.time() * 1000)),
                    'title': title,
                    'company': company,
                    'url': job_url,
                    'location': job_data['location'],
                    'description': job_data['description'],  # Store for n8n resume factory
                    'application_number': str(result.get('application_number', '')),
                    'score': score,
                    'recommendation': recommendation,
                    'estimated_salary': score_result.get('estimated_salary', 'Unknown'),
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                }
                pending.append(queue_entry)
                save_queue('pending', pending)

                logger.info(f"   Added to pending queue (#{result.get('application_number')})")

            # Rate limiting between factory calls
            time.sleep(DELAY_BETWEEN_JOBS)

    # Save stats once at end
    save_stats(stats)

    # Save dry run results
    if dry_run and dry_run_results:
        dry_run_file = QUEUE_DIR / 'dry_run.json'
        dry_run_file.write_text(json.dumps(dry_run_results, indent=2))
        logger.info(f"   Dry run results saved to {dry_run_file}")

    logger.info("=" * 50)
    logger.info(f"HUNT COMPLETE - {mode_label}")
    logger.info(f"   Scored: {total_scored} jobs")
    logger.info(f"   Skipped (NO): {total_skipped}")
    logger.info(f"   Passed (YES/MAYBE): {total_passed}")
    if not dry_run:
        logger.info(f"   Sent to factory: {total_processed}")
        logger.info(f"   Pending queue: {len(pending)} jobs")
    else:
        est_cost_low = total_passed * 0.30
        est_cost_high = total_passed * 0.60
        logger.info(f"   Estimated factory cost: ${est_cost_low:.2f}-${est_cost_high:.2f}")
        logger.info(f"   Review: cat /root/job_bot/queue/dry_run.json")
        logger.info(f"   Then run live: python3 simple_hunter.py --max {total_passed}")
    logger.info(f"   Pre-filtered (saved API): {pre_filtered_count}")
    logger.info(f"   Company+title deduped: {dedup_count}")
    logger.info(f"   Scoring breakdown: YES={stats.get('scored_yes',0)} MAYBE={stats.get('scored_maybe',0)} NO={stats.get('scored_no',0)}")
    if stats['total'] > 0:
        logger.info(f"   Remote: {stats['remote']} ({stats['remote']/stats['total']*100:.1f}%)")
        logger.info(f"   Local:  {stats['local']} ({stats['local']/stats['total']*100:.1f}%)")
    logger.info("=" * 50)

    return total_processed if not dry_run else total_passed

def run_loop():
    while True:
        try:
            processed = run_hunt()
            time.sleep(1800 if processed == 0 else 900)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(300)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Job Hunter - Scrape, Score, and Queue Jobs')
    parser.add_argument('--loop', action='store_true', help='Run continuously')
    parser.add_argument('--dry-run', action='store_true', help='Scrape and score only, no factory/Opus costs')
    parser.add_argument('--max', type=int, default=None, help='Max jobs to send to factory (default: 50)')
    parser.add_argument('--remote-only', action='store_true', help='Only search for remote jobs')
    parser.add_argument('--local-only', action='store_true', help='Only search for local jobs (no remote searches)')
    args = parser.parse_args()

    # Override remote settings based on flags (use global keyword)
    if args.remote_only:
        globals()['INCLUDE_REMOTE_SEARCHES'] = True
        globals()['INCLUDE_LINKEDIN'] = True
        SEARCH_TERMS.clear()  # Lists can be modified in place
        logger.info("Remote-only mode: searching only remote jobs")
    elif args.local_only:
        globals()['INCLUDE_REMOTE_SEARCHES'] = False
        globals()['INCLUDE_LINKEDIN'] = False
        logger.info("Local-only mode: no remote searches")

    if args.loop:
        run_loop()
    else:
        run_hunt(dry_run=args.dry_run, max_factory=args.max)
