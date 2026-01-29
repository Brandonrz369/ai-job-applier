#!/usr/bin/env python3
"""
Job Application Agent
=====================
Autonomous agent that hunts for jobs, generates tailored resumes,
and submits applications while you sleep.

Architecture:
1. HUNT: Search Indeed/LinkedIn for matching jobs
2. FILTER: Apply 75/25 local/remote ratio
3. GENERATE: Send to n8n webhook, get back tailored PDFs
4. APPLY: Upload documents and submit application
5. LOG: Track everything for portfolio stats
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import requests

# Browser automation
from browser_use import Agent
from langchain_openai import ChatOpenAI

# ============================================
# CONFIGURATION
# ============================================

class Config:
    # API Keys (from environment)
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    
    # URLs
    N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://n8n:5678/webhook/incoming-job')
    
    # Job Search Settings
    TARGET_LOCATION = os.getenv('TARGET_LOCATION', 'Long Beach, CA')
    SEARCH_TERMS = [
        'IT Support',
        'Help Desk',
        'Desktop Support',
        'IT Technician',
        'System Administrator',
        'Network Technician'
    ]
    
    # 75% local, 25% remote
    REMOTE_RATIO = float(os.getenv('REMOTE_RATIO', 0.25))
    
    # Paths
    OUTPUT_DIR = Path('/output')
    LOGS_DIR = Path('/logs')
    STATS_FILE = OUTPUT_DIR / '.counter.json'
    
    # Rate limiting
    DELAY_BETWEEN_JOBS = 30  # seconds
    DELAY_BETWEEN_SEARCHES = 300  # 5 minutes
    MAX_APPLICATIONS_PER_HOUR = 10


# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / 'agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# JOB TARGETING (75/25 Split)
# ============================================

class JobTargeting:
    """Manages the 75% local / 25% remote application ratio"""
    
    def __init__(self):
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        try:
            with open(Config.STATS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'total': 0, 'remote': 0, 'local': 0}
    
    def _save_stats(self):
        with open(Config.STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def is_remote(self, job: Dict) -> bool:
        """Detect if job is remote"""
        keywords = ['remote', 'work from home', 'wfh', 'anywhere', 'telecommute']
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
        return any(kw in text for kw in keywords)
    
    def should_apply(self, job: Dict) -> bool:
        """Decide if we should apply based on 75/25 ratio"""
        is_remote = self.is_remote(job)
        
        total = self.stats['total']
        if total == 0:
            return True
        
        current_remote_ratio = self.stats['remote'] / total
        
        if is_remote:
            # Only take remote if under target ratio
            return current_remote_ratio < Config.REMOTE_RATIO
        
        return True  # Always accept local
    
    def record_application(self, job: Dict):
        """Update stats after application"""
        self.stats['total'] += 1
        if self.is_remote(job):
            self.stats['remote'] += 1
        else:
            self.stats['local'] += 1
        self._save_stats()


# ============================================
# N8N FACTORY INTEGRATION
# ============================================

class ResumeFactory:
    """Interfaces with n8n to generate tailored documents"""
    
    def __init__(self):
        self.webhook_url = Config.N8N_WEBHOOK_URL
    
    def generate_documents(self, job: Dict) -> Optional[Dict]:
        """
        Send job to n8n and get back PDF filenames
        
        Returns:
            dict with 'resume' and 'cover' PDF paths, or None on failure
        """
        payload = {
            'title': job.get('title', 'Unknown'),
            'company': job.get('company', 'Unknown'),
            'description': job.get('description', ''),
            'url': job.get('url', ''),
            'location': job.get('location', '')
        }
        
        try:
            logger.info(f"Sending job to factory: {payload['company']}")
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=120  # 2 min timeout for PDF generation
            )
            
            if response.status_code in [200, 202]:
                result = response.json()
                logger.info(f"Factory success: Application #{result.get('application_number')}")
                return {
                    'resume': Config.OUTPUT_DIR / result['files']['resume'],
                    'cover': Config.OUTPUT_DIR / result['files']['cover'],
                    'application_number': result.get('application_number')
                }
            else:
                logger.error(f"Factory error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Factory connection failed: {e}")
            return None


# ============================================
# BROWSER AGENT - THE HUNTER
# ============================================

class JobHunter:
    """
    Uses Browser Use + DeepSeek to autonomously search and apply for jobs
    """
    
    def __init__(self):
        # Initialize DeepSeek as the brain
        self.llm = ChatOpenAI(
            base_url='https://api.deepseek.com',
            model='deepseek-chat',
            api_key=Config.DEEPSEEK_API_KEY
        )
        self.targeting = JobTargeting()
        self.factory = ResumeFactory()
    
    async def search_jobs(self, search_term: str, location: str) -> List[Dict]:
        """
        Search Indeed for jobs matching criteria
        
        Returns list of job dicts with: title, company, description, url, location
        """
        agent = Agent(
            task=f"""
            Go to indeed.com
            Search for "{search_term}" jobs in "{location}"
            For the first 5 job listings:
            1. Click on each job
            2. Extract: job title, company name, full job description, job URL
            3. Return the data as a JSON array
            
            Return ONLY valid JSON, no other text.
            """,
            llm=self.llm
        )
        
        try:
            result = await agent.run()
            # Parse the JSON result
            jobs = json.loads(result)
            logger.info(f"Found {len(jobs)} jobs for '{search_term}'")
            return jobs
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []
    
    async def apply_to_job(self, job: Dict, documents: Dict) -> bool:
        """
        Navigate to job application page and submit
        
        Args:
            job: Job details dict
            documents: Dict with 'resume' and 'cover' PDF paths
        
        Returns:
            True if application submitted successfully
        """
        resume_path = str(documents['resume'])
        cover_path = str(documents['cover'])
        app_number = documents['application_number']
        
        agent = Agent(
            task=f"""
            Go to: {job['url']}
            
            Look for an "Apply" or "Apply Now" button and click it.
            
            If there's an application form:
            1. Fill in name: Brandon Ruiz
            2. Fill in email: brandonlruiz98@gmail.com
            3. Fill in phone: 775-530-8234
            4. Upload resume from: {resume_path}
            5. Upload cover letter from: {cover_path} (if there's a field for it)
            6. Answer any simple questions honestly
            7. Click Submit
            
            If it redirects to an external site (Workday, Greenhouse, etc.):
            1. Follow the same process
            2. Fill out required fields
            3. Upload documents
            4. Submit
            
            Take a screenshot of the confirmation page.
            
            Return "SUCCESS" if submitted, or "FAILED: [reason]" if not.
            """,
            llm=self.llm
        )
        
        try:
            result = await agent.run()
            if 'SUCCESS' in result.upper():
                logger.info(f"✅ Application #{app_number} submitted to {job['company']}")
                return True
            else:
                logger.warning(f"❌ Application failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Application error: {e}")
            return False
    
    async def run_hunt_cycle(self):
        """
        One complete hunt cycle:
        1. Search for jobs
        2. Filter by 75/25 ratio
        3. Generate documents
        4. Submit applications
        """
        applications_this_hour = 0
        
        for search_term in Config.SEARCH_TERMS:
            if applications_this_hour >= Config.MAX_APPLICATIONS_PER_HOUR:
                logger.info("Hourly limit reached, pausing...")
                await asyncio.sleep(3600)  # Wait an hour
                applications_this_hour = 0
            
            # Search for jobs
            jobs = await self.search_jobs(search_term, Config.TARGET_LOCATION)
            
            for job in jobs:
                # Check 75/25 ratio
                if not self.targeting.should_apply(job):
                    logger.info(f"Skipping {job['company']} (remote ratio exceeded)")
                    continue
                
                # Generate tailored documents
                documents = self.factory.generate_documents(job)
                if not documents:
                    continue
                
                # Wait for PDFs to be written
                await asyncio.sleep(5)
                
                # Submit application
                success = await self.apply_to_job(job, documents)
                
                if success:
                    self.targeting.record_application(job)
                    applications_this_hour += 1
                
                # Rate limiting
                await asyncio.sleep(Config.DELAY_BETWEEN_JOBS)
            
            # Pause between search terms
            await asyncio.sleep(Config.DELAY_BETWEEN_SEARCHES)
    
    async def run_forever(self):
        """Main loop - run indefinitely"""
        logger.info("🚀 Job Hunter Agent starting...")
        logger.info(f"Target: {Config.TARGET_LOCATION}")
        logger.info(f"Remote ratio: {Config.REMOTE_RATIO * 100}%")
        
        while True:
            try:
                await self.run_hunt_cycle()
                logger.info("Hunt cycle complete. Restarting in 10 minutes...")
                await asyncio.sleep(600)
            except Exception as e:
                logger.error(f"Hunt cycle error: {e}")
                await asyncio.sleep(60)  # Wait a minute before retry


# ============================================
# GITHUB STATS UPDATER
# ============================================

class GitHubUpdater:
    """Updates GitHub repo with latest stats"""
    
    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.repo = 'brandonruiz/job-agent'  # Update with your repo
    
    def generate_stats_md(self) -> str:
        """Generate STATS.md content"""
        try:
            with open(Config.STATS_FILE, 'r') as f:
                stats = json.load(f)
        except:
            stats = {'total': 0, 'remote': 0, 'local': 0}
        
        remote_pct = (stats['remote'] / stats['total'] * 100) if stats['total'] > 0 else 0
        local_pct = (stats['local'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        return f"""# Application Statistics

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PST*

## Overview

| Metric | Count |
|--------|-------|
| **Total Applications** | {stats['total']} |
| **Remote** | {stats['remote']} ({remote_pct:.1f}%) |
| **Local** | {stats['local']} ({local_pct:.1f}%) |

## Target Ratio
- 🎯 Local: 75%
- 🌐 Remote: 25%
- Current: Local {local_pct:.1f}% / Remote {remote_pct:.1f}%

## Currently Studying
- 📚 AWS Cloud Practitioner

---
*Stats auto-generated by the Job Application Agent*
"""
    
    def update_repo(self):
        """Push updated stats to GitHub"""
        if not self.token:
            logger.warning("No GitHub token, skipping update")
            return
        
        # This would use the GitHub API to update files
        # Simplified for now - you can use PyGithub library
        logger.info("GitHub update would happen here")


# ============================================
# MAIN ENTRY POINT
# ============================================

async def main():
    """Main entry point"""
    # Ensure directories exist
    Config.OUTPUT_DIR.mkdir(exist_ok=True)
    Config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Start the hunter
    hunter = JobHunter()
    await hunter.run_forever()


if __name__ == '__main__':
    asyncio.run(main())
