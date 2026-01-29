#!/usr/bin/env python3
import os, json, time, logging, argparse, requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from jobspy import scrape_jobs
import pandas as pd
from scorer import score_job

N8N_WEBHOOK_URL = 'http://localhost:5678/webhook/incoming-job'
LOCATIONS = ['Anaheim, CA', 'Irvine, CA', 'Orange County, CA']
SEARCH_TERMS = ['IT Support', 'Help Desk', 'Desktop Support', 'IT Technician', 'System Administrator', 'Network Technician']
RESULTS_PER_SEARCH = 15
HOURS_OLD = 72
REMOTE_RATIO = 0.25
MIN_SCORE = 6
DELAY_BETWEEN_JOBS = 15
DELAY_BETWEEN_SEARCHES = 30
OUTPUT_DIR = Path('/root/job_bot/output')
STATS_FILE = OUTPUT_DIR / '.counter.json'
SEEN_FILE = OUTPUT_DIR / '.seen_jobs.json'
QUEUE_FILE = Path('/root/job_bot/queue/pending.json')
COUNTER_FILE = Path('/root/job_bot/agent/.app_counter.json')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler('/root/job_bot/logs/hunter.log')])
logger = logging.getLogger(__name__)

def load_seen():
    try:
        with open(SEEN_FILE, 'r') as f: return set(json.load(f))
    except: return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f: json.dump(list(seen), f)

def get_next_app_number():
    try:
        count = json.loads(COUNTER_FILE.read_text()).get('count', 0) if COUNTER_FILE.exists() else 0
        count += 1
        COUNTER_FILE.write_text(json.dumps({'count': count}))
        return count
    except: return int(time.time())

def load_stats():
    try:
        with open(STATS_FILE, 'r') as f: return json.load(f)
    except: return {'total': 0, 'remote': 0, 'local': 0, 'skipped_score': 0}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f: json.dump(stats, f, indent=2)

def write_to_queue(payload, app_number):
    try:
        Path('/root/job_bot/queue').mkdir(parents=True, exist_ok=True)
        queue = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
        queue.append({'id': str(int(time.time() * 1000)), 'company': payload['company'], 'title': payload['title'], 'url': payload['url'], 'location': payload['location'], 'application_number': app_number, 'status': 'pending', 'created_at': datetime.now().isoformat()})
        QUEUE_FILE.write_text(json.dumps(queue, indent=2))
        logger.info(f"   Added to queue")
    except Exception as e: logger.error(f"   Queue write failed: {e}")

def is_remote(job):
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
    return any(kw in text for kw in ['remote', 'work from home', 'wfh', 'anywhere', 'telecommute', 'hybrid'])

def should_apply(job, stats):
    if stats['total'] == 0: return True, "First"
    ratio = stats['remote'] / stats['total']
    if is_remote(job): return (True, "Remote OK") if ratio < REMOTE_RATIO else (False, "Remote limit")
    return True, "Local"

def send_to_factory(job):
    def clean(t):
        if t is None or (isinstance(t, float) and pd.isna(t)): return ""
        t = str(t).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('"', "'").replace('\\', '/')
        return t[:5000].strip() if len(t) > 5000 else t.strip()
    app_number = get_next_app_number()
    payload = {'title': clean(job.get('title', 'Unknown')), 'company': clean(job.get('company', 'Unknown')), 'description': clean(job.get('description', '')), 'url': str(job.get('job_url', '')), 'location': clean(job.get('location', '')), 'application_number': app_number}
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        if response.status_code in [200, 202]:
            write_to_queue(payload, app_number)
            logger.info(f"   Sent to n8n")
            return {'application_number': app_number}
        logger.error(f"   HTTP {response.status_code}")
        return None
    except requests.Timeout:
        write_to_queue(payload, app_number)
        logger.info(f"   Sent (background)")
        return {'application_number': app_number}
    except Exception as e:
        logger.error(f"   Failed: {e}")
        return None

def search_jobs(search_term, location):
    logger.info(f"Searching: '{search_term}' in '{location}'")
    try:
        jobs = scrape_jobs(site_name=["indeed", "linkedin"], search_term=search_term, location=location, results_wanted=RESULTS_PER_SEARCH, hours_old=HOURS_OLD, country_indeed='USA')
        logger.info(f"   Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        logger.error(f"   Search failed: {e}")
        return pd.DataFrame()

def run_hunt():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Path('/root/job_bot/logs').mkdir(parents=True, exist_ok=True)
    Path('/root/job_bot/queue').mkdir(parents=True, exist_ok=True)
    seen, stats, processed = load_seen(), load_stats(), 0
    if 'skipped_score' not in stats: stats['skipped_score'] = 0
    logger.info("=" * 50 + "\nJOB HUNTER STARTING\n" + "=" * 50)
    for location in LOCATIONS:
        for search_term in SEARCH_TERMS:
            jobs = search_jobs(search_term, location)
            if jobs.empty: time.sleep(5); continue
            for _, job in jobs.iterrows():
                job_url, company, title = str(job.get('job_url', '')), str(job.get('company', 'Unknown')), str(job.get('title', 'Unknown'))
                if job_url in seen: continue
                should, reason = should_apply(job, stats)
                if not should: continue
                logger.info(f"Scoring: {company} - {title[:40]}")
                score_result = score_job({'company': company, 'title': title, 'location': str(job.get('location', '')), 'description': str(job.get('description', ''))[:3000]})
                score = score_result.get('score', 5)
                score = float(score.split('/')[0]) if isinstance(score, str) and '/' in score else float(score) if isinstance(score, str) else float(score)
                recommendation = score_result.get('recommendation', 'MAYBE')
                logger.info(f"   Score: {score}/10 - {recommendation}")
                if score < MIN_SCORE or recommendation == "NO":
                    seen.add(job_url); save_seen(seen); stats['skipped_score'] += 1; save_stats(stats); continue
                logger.info(f"   Sending to Opus...")
                result = send_to_factory(job)
                if result:
                    seen.add(job_url); save_seen(seen); stats['total'] += 1
                    stats['remote' if is_remote(job) else 'local'] += 1
                    save_stats(stats); processed += 1; time.sleep(DELAY_BETWEEN_JOBS)
                else: seen.add(job_url); save_seen(seen); time.sleep(10)
            time.sleep(DELAY_BETWEEN_SEARCHES)
    logger.info("=" * 50 + f"\nDONE - Processed: {processed}\n" + "=" * 50)
    return processed

def run_loop():
    while True:
        try:
            processed = run_hunt()
            time.sleep(1800 if processed == 0 else 900)
        except KeyboardInterrupt: break
        except Exception as e: logger.error(f"Error: {e}"); time.sleep(300)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--loop', action='store_true')
    args = parser.parse_args()
    run_loop() if args.loop else run_hunt()
