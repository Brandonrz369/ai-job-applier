#!/usr/bin/env python3
"""
COMPLETE Job Application Agent
==============================
Full autonomous loop:
1. HUNT: Scrape Indeed/LinkedIn for jobs
2. FILTER: Apply 75/25 local/remote ratio
3. GENERATE: Send to n8n → get tailored PDFs
4. SUBMIT: Browser Use picks up PDFs and submits applications
5. TRACK: Log everything for stats
6. IMPROVE: Analyze what works and adjust prompts

This is the FULL version that actually submits applications.
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import requests

# Job scraping
from jobspy import scrape_jobs
import pandas as pd

# Browser automation
try:
    from browser_use import Agent
    from langchain_openai import ChatOpenAI
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("⚠️  browser-use not installed. Running in SCRAPE-ONLY mode.")
    print("   Install with: pip install browser-use langchain-openai playwright")
    print("   Then run: playwright install chromium")

# ============================================
# CONFIGURATION
# ============================================

class Config:
    # API Keys
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    
    # URLs
    N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/incoming-job')
    
    # Job Search
    TARGET_LOCATION = os.getenv('TARGET_LOCATION', 'Anaheim, CA')
    SEARCH_TERMS = [
        'IT Support',
        'Help Desk', 
        'Desktop Support',
        'IT Technician',
        'System Administrator',
        'Network Technician',
        'IT Help Desk',
        'Technical Support'
    ]
    
    # 75% local, 25% remote
    REMOTE_RATIO = float(os.getenv('REMOTE_RATIO', '0.25'))
    LOCAL_RATIO = 1.0 - REMOTE_RATIO
    
    # Paths
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', './output'))
    LOGS_DIR = Path(os.getenv('LOGS_DIR', './logs'))
    
    # Files
    COUNTER_FILE = OUTPUT_DIR / '.counter.json'
    PENDING_FILE = OUTPUT_DIR / '.pending_submissions.json'
    FEEDBACK_FILE = OUTPUT_DIR / '.feedback.json'
    SUBMITTED_FILE = OUTPUT_DIR / '.submitted.json'
    
    # Rate Limiting
    DELAY_BETWEEN_SCRAPES = 5  # seconds between job scrapes
    DELAY_BETWEEN_SUBMISSIONS = 30  # seconds between application submissions
    DELAY_BETWEEN_SEARCHES = 300  # 5 min between search term rotations
    MAX_APPLICATIONS_PER_HOUR = 10
    
    # Candidate Info (for form filling)
    CANDIDATE = {
        'name': 'Brandon Ruiz',
        'email': 'brandonlruiz98@gmail.com',
        'phone': '(213) 349-6790',
        'location': 'Anaheim, CA'
    }


# ============================================
# LOGGING
# ============================================

def setup_logging():
    Config.LOGS_DIR.mkdir(exist_ok=True)
    Config.OUTPUT_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(Config.LOGS_DIR / 'agent.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================
# STATS & TRACKING
# ============================================

class StatsTracker:
    """Tracks application statistics and feedback for self-improvement"""
    
    def __init__(self):
        self.counter = self._load_json(Config.COUNTER_FILE, {
            'total': 0, 'remote': 0, 'local': 0,
            'submitted': 0, 'responses': 0, 'interviews': 0
        })
        self.feedback = self._load_json(Config.FEEDBACK_FILE, {
            'successful_keywords': [],
            'failed_keywords': [],
            'best_performing_searches': [],
            'response_rate_by_type': {'remote': 0, 'local': 0}
        })
        self.submitted = self._load_json(Config.SUBMITTED_FILE, [])
    
    def _load_json(self, path: Path, default: dict) -> dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default
    
    def _save_json(self, path: Path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_remote(self, job: dict) -> bool:
        keywords = ['remote', 'work from home', 'wfh', 'anywhere', 'telecommute', 'hybrid']
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
        return any(kw in text for kw in keywords)
    
    def should_apply(self, job: dict) -> Tuple[bool, str]:
        """Check if we should apply based on 75/25 ratio"""
        is_remote = self.is_remote(job)
        
        if self.counter['total'] == 0:
            return True, "First application"
        
        current_remote_ratio = self.counter['remote'] / self.counter['total']
        
        if is_remote:
            if current_remote_ratio < Config.REMOTE_RATIO:
                return True, f"Remote OK (current: {current_remote_ratio:.1%}, target: {Config.REMOTE_RATIO:.0%})"
            return False, f"Remote ratio exceeded ({current_remote_ratio:.1%} >= {Config.REMOTE_RATIO:.0%})"
        
        return True, "Local position"
    
    def record_generated(self, job: dict):
        """Record that we generated documents for a job"""
        self.counter['total'] += 1
        if self.is_remote(job):
            self.counter['remote'] += 1
        else:
            self.counter['local'] += 1
        self._save_json(Config.COUNTER_FILE, self.counter)
    
    def record_submitted(self, job: dict, success: bool):
        """Record submission result"""
        if success:
            self.counter['submitted'] += 1
            self.submitted.append({
                'company': job.get('company'),
                'title': job.get('title'),
                'url': job.get('url'),
                'submitted_at': datetime.now().isoformat(),
                'is_remote': self.is_remote(job)
            })
            self._save_json(Config.SUBMITTED_FILE, self.submitted)
        self._save_json(Config.COUNTER_FILE, self.counter)
    
    def record_response(self, job_url: str, response_type: str):
        """Record when we get a response (for self-improvement)"""
        self.counter['responses'] += 1
        if response_type == 'interview':
            self.counter['interviews'] += 1
        self._save_json(Config.COUNTER_FILE, self.counter)
        
        # Find the job and extract keywords for feedback
        for sub in self.submitted:
            if sub.get('url') == job_url:
                # This job got a response - it's a good signal
                logger.info(f"✨ Response recorded for {sub.get('company')}")
                break
    
    def get_stats_summary(self) -> str:
        """Get formatted stats for logging"""
        total = max(self.counter['total'], 1)
        return (
            f"Total: {self.counter['total']} | "
            f"Remote: {self.counter['remote']} ({self.counter['remote']/total:.0%}) | "
            f"Local: {self.counter['local']} ({self.counter['local']/total:.0%}) | "
            f"Submitted: {self.counter['submitted']} | "
            f"Responses: {self.counter['responses']} | "
            f"Interviews: {self.counter['interviews']}"
        )


# ============================================
# N8N FACTORY INTERFACE
# ============================================

class DocumentFactory:
    """Sends jobs to n8n and gets back tailored PDFs"""
    
    def __init__(self):
        self.webhook_url = Config.N8N_WEBHOOK_URL
    
    def generate(self, job: dict) -> Optional[dict]:
        """
        Send job to n8n webhook, returns file info or None
        """
        payload = {
            'title': str(job.get('title', 'Unknown')),
            'company': str(job.get('company', 'Unknown')),
            'description': str(job.get('description', '')),
            'url': str(job.get('job_url', job.get('url', ''))),
            'location': str(job.get('location', ''))
        }
        
        try:
            logger.info(f"📤 Sending to factory: {payload['company']} - {payload['title']}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=180  # 3 min for PDF generation
            )
            
            if response.status_code in [200, 202]:
                result = response.json()
                logger.info(f"✅ Documents generated: #{result.get('application_number')}")
                return {
                    'application_number': result.get('application_number'),
                    'resume_file': Config.OUTPUT_DIR / result['files']['resume'],
                    'cover_file': Config.OUTPUT_DIR / result['files']['cover'],
                    'company': payload['company'],
                    'title': payload['title'],
                    'url': payload['url']
                }
            else:
                logger.error(f"❌ Factory error: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.Timeout:
            logger.error("❌ Factory timeout - PDF generation took too long")
            return None
        except Exception as e:
            logger.error(f"❌ Factory connection failed: {e}")
            return None


# ============================================
# JOB SCRAPER (using jobspy)
# ============================================

class JobScraper:
    """Scrapes jobs from Indeed/LinkedIn using jobspy"""
    
    def __init__(self):
        self.seen_urls = set()  # Avoid duplicate applications
        self._load_seen()
    
    def _load_seen(self):
        """Load previously seen job URLs"""
        try:
            with open(Config.OUTPUT_DIR / '.seen_jobs.json', 'r') as f:
                self.seen_urls = set(json.load(f))
        except:
            self.seen_urls = set()
    
    def _save_seen(self):
        with open(Config.OUTPUT_DIR / '.seen_jobs.json', 'w') as f:
            json.dump(list(self.seen_urls), f)
    
    def search(self, search_term: str, location: str, results: int = 10) -> List[dict]:
        """Search for jobs and return list of job dicts"""
        logger.info(f"🔍 Searching: '{search_term}' in '{location}'")
        
        try:
            jobs_df = scrape_jobs(
                site_name=["indeed", "linkedin"],
                search_term=search_term,
                location=location,
                results_wanted=results,
                hours_old=48,  # Last 48 hours
                country_indeed='USA'
            )
            
            jobs = []
            for _, row in jobs_df.iterrows():
                url = str(row.get('job_url', ''))
                
                # Skip if we've seen this job
                if url in self.seen_urls:
                    continue
                
                jobs.append({
                    'title': str(row.get('title', '')),
                    'company': str(row.get('company', '')),
                    'description': str(row.get('description', '')),
                    'url': url,
                    'location': str(row.get('location', '')),
                    'source': str(row.get('site', ''))
                })
                
                self.seen_urls.add(url)
            
            self._save_seen()
            logger.info(f"   Found {len(jobs)} new jobs")
            return jobs
            
        except Exception as e:
            logger.error(f"   Search failed: {e}")
            return []


# ============================================
# BROWSER AGENT (for submission)
# ============================================

class ApplicationSubmitter:
    """Uses Browser Use to submit applications with the generated PDFs"""
    
    def __init__(self):
        if not BROWSER_USE_AVAILABLE:
            self.enabled = False
            return
            
        self.enabled = True
        self.llm = ChatOpenAI(
            base_url='https://api.deepseek.com',
            model='deepseek-chat',
            api_key=Config.DEEPSEEK_API_KEY
        )
    
    async def submit(self, job: dict, resume_path: Path, cover_path: Path) -> bool:
        """
        Navigate to job posting and submit application
        
        Returns True if successful
        """
        if not self.enabled:
            logger.warning("Browser Use not available - skipping submission")
            return False
        
        candidate = Config.CANDIDATE
        
        task = f"""
        Your task is to apply for a job. Follow these steps carefully:
        
        1. Navigate to: {job['url']}
        
        2. Look for an "Apply", "Apply Now", "Easy Apply", or similar button. Click it.
        
        3. If a form appears, fill it out:
           - Name: {candidate['name']}
           - Email: {candidate['email']}
           - Phone: {candidate['phone']}
           - Location/City: {candidate['location']}
        
        4. For file uploads:
           - Upload resume from: {resume_path}
           - Upload cover letter from: {cover_path} (if there's a field for it)
        
        5. For any other required fields:
           - Work authorization: Yes, authorized to work in the US
           - Willing to relocate: Yes (if asked about Long Beach area)
           - Years of experience: 5+ years
           - Answer honestly and professionally
        
        6. Look for and click the Submit/Apply/Send Application button.
        
        7. Wait for confirmation page or message.
        
        IMPORTANT:
        - If it redirects to Workday, Greenhouse, Lever, etc., follow the same process
        - If you need to create an account, use email: {candidate['email']}
        - If you get stuck or encounter a CAPTCHA, stop and report "BLOCKED"
        - Take a screenshot of the final confirmation
        
        Return one of:
        - "SUCCESS: Application submitted" if you completed the application
        - "BLOCKED: [reason]" if you encountered a barrier
        - "FAILED: [reason]" if something went wrong
        """
        
        try:
            logger.info(f"🌐 Submitting to {job['company']}...")
            
            agent = Agent(task=task, llm=self.llm)
            result = await agent.run()
            
            if 'SUCCESS' in result.upper():
                logger.info(f"✅ Submitted to {job['company']}")
                return True
            elif 'BLOCKED' in result.upper():
                logger.warning(f"🚫 Blocked at {job['company']}: {result}")
                return False
            else:
                logger.warning(f"❌ Failed at {job['company']}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Submission error: {e}")
            return False


# ============================================
# SELF-IMPROVEMENT ENGINE
# ============================================

class SelfImprover:
    """Analyzes results and suggests prompt improvements"""
    
    def __init__(self, stats: StatsTracker):
        self.stats = stats
    
    def analyze(self) -> dict:
        """Analyze current performance and suggest improvements"""
        total = self.stats.counter['total']
        responses = self.stats.counter['responses']
        interviews = self.stats.counter['interviews']
        
        if total < 50:
            return {'status': 'insufficient_data', 'message': 'Need at least 50 applications for analysis'}
        
        response_rate = responses / total * 100
        interview_rate = interviews / total * 100 if total > 0 else 0
        
        insights = {
            'response_rate': f"{response_rate:.1f}%",
            'interview_rate': f"{interview_rate:.1f}%",
            'recommendations': []
        }
        
        # Analyze patterns
        if response_rate < 3:
            insights['recommendations'].append(
                "Low response rate. Consider: more specific job titles, emphasizing certifications"
            )
        
        if self.stats.counter['remote'] > 0:
            remote_response_rate = self.stats.feedback.get('response_rate_by_type', {}).get('remote', 0)
            local_response_rate = self.stats.feedback.get('response_rate_by_type', {}).get('local', 0)
            
            if remote_response_rate > local_response_rate * 1.5:
                insights['recommendations'].append(
                    "Remote positions performing better. Consider increasing REMOTE_RATIO"
                )
        
        return insights
    
    def generate_report(self) -> str:
        """Generate a report for GitHub README"""
        stats = self.stats.counter
        total = max(stats['total'], 1)
        
        report = f"""## 📊 Performance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

### Key Metrics
| Metric | Value |
|--------|-------|
| Total Applications | {stats['total']} |
| Submitted | {stats['submitted']} |
| Responses | {stats['responses']} |
| Interviews | {stats['interviews']} |
| Response Rate | {stats['responses']/total*100:.1f}% |

### Distribution
- Local: {stats['local']} ({stats['local']/total*100:.0f}%)
- Remote: {stats['remote']} ({stats['remote']/total*100:.0f}%)
"""
        return report


# ============================================
# MAIN ORCHESTRATOR
# ============================================

class JobAgent:
    """Main orchestrator that ties everything together"""
    
    def __init__(self):
        self.stats = StatsTracker()
        self.factory = DocumentFactory()
        self.scraper = JobScraper()
        self.submitter = ApplicationSubmitter()
        self.improver = SelfImprover(self.stats)
        
        self.applications_this_hour = 0
        self.hour_start = datetime.now()
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        if now - self.hour_start > timedelta(hours=1):
            self.applications_this_hour = 0
            self.hour_start = now
        
        return self.applications_this_hour < Config.MAX_APPLICATIONS_PER_HOUR
    
    async def process_job(self, job: dict) -> bool:
        """Process a single job through the full pipeline"""
        
        # 1. Check if we should apply (75/25 ratio)
        should_apply, reason = self.stats.should_apply(job)
        if not should_apply:
            logger.info(f"⏭️  Skipping {job['company']}: {reason}")
            return False
        
        logger.info(f"📋 Processing: {job['company']} - {job['title']}")
        logger.info(f"   Reason: {reason}")
        
        # 2. Generate documents via n8n
        docs = self.factory.generate(job)
        if not docs:
            return False
        
        self.stats.record_generated(job)
        
        # 3. Wait for files to be written
        await asyncio.sleep(3)
        
        # 4. Submit application (if browser-use is available)
        if self.submitter.enabled:
            success = await self.submitter.submit(
                job=job,
                resume_path=docs['resume_file'],
                cover_path=docs['cover_file']
            )
            self.stats.record_submitted(job, success)
            
            if success:
                self.applications_this_hour += 1
        else:
            logger.info(f"   📁 Resume: {docs['resume_file']}")
            logger.info(f"   📁 Cover:  {docs['cover_file']}")
            logger.info(f"   🔗 Apply manually: {job['url']}")
        
        return True
    
    async def run_search_cycle(self, search_term: str):
        """Run one search and process results"""
        jobs = self.scraper.search(search_term, Config.TARGET_LOCATION)
        
        for job in jobs:
            if not self._check_rate_limit():
                logger.info("⏸️  Rate limit reached, pausing...")
                await asyncio.sleep(3600)
                self.applications_this_hour = 0
            
            await self.process_job(job)
            await asyncio.sleep(Config.DELAY_BETWEEN_SCRAPES)
    
    async def run_forever(self):
        """Main loop - runs continuously"""
        logger.info("=" * 60)
        logger.info("🚀 JOB APPLICATION AGENT STARTING")
        logger.info(f"   Target: {Config.TARGET_LOCATION}")
        logger.info(f"   Ratio: {Config.LOCAL_RATIO:.0%} local / {Config.REMOTE_RATIO:.0%} remote")
        logger.info(f"   Browser submission: {'ENABLED' if self.submitter.enabled else 'DISABLED'}")
        logger.info("=" * 60)
        
        cycle = 0
        while True:
            cycle += 1
            logger.info(f"\n{'='*40}")
            logger.info(f"CYCLE {cycle} | {self.stats.get_stats_summary()}")
            logger.info(f"{'='*40}\n")
            
            for search_term in Config.SEARCH_TERMS:
                try:
                    await self.run_search_cycle(search_term)
                except Exception as e:
                    logger.error(f"Error in search cycle: {e}")
                
                await asyncio.sleep(Config.DELAY_BETWEEN_SEARCHES)
            
            # Run self-improvement analysis every 10 cycles
            if cycle % 10 == 0:
                insights = self.improver.analyze()
                if insights.get('recommendations'):
                    logger.info("💡 Self-improvement insights:")
                    for rec in insights['recommendations']:
                        logger.info(f"   • {rec}")
            
            logger.info(f"\n🔄 Cycle {cycle} complete. Restarting in 10 minutes...")
            await asyncio.sleep(600)
    
    def run_once(self):
        """Run a single search cycle (for testing)"""
        asyncio.run(self._run_once_async())
    
    async def _run_once_async(self):
        logger.info("🧪 Running single test cycle...")
        for search_term in Config.SEARCH_TERMS[:2]:  # Just first 2 search terms
            await self.run_search_cycle(search_term)
        logger.info(f"✅ Test complete. {self.stats.get_stats_summary()}")


# ============================================
# CLI ENTRY POINT
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Job Application Agent')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--stats', action='store_true', help='Show stats and exit')
    parser.add_argument('--report', action='store_true', help='Generate performance report')
    args = parser.parse_args()
    
    agent = JobAgent()
    
    if args.stats:
        print(agent.stats.get_stats_summary())
        return
    
    if args.report:
        print(agent.improver.generate_report())
        return
    
    if args.once:
        agent.run_once()
    else:
        asyncio.run(agent.run_forever())


if __name__ == '__main__':
    main()
