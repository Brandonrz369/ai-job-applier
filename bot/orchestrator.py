import json
import time
from pathlib import Path
from datetime import datetime
from config import ACCOUNTS_FILE, PENDING_FILE, APPLIED_FILE, FAILED_FILE
from agent import Agent

def load_json(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else []

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2))

def get_available_account(accounts):
    """Get next account that isn't blocked"""
    for acc in accounts:
        if acc.get('status', 'new') in ['new', 'active']:
            return acc
    return None

def run(max_jobs=None):
    accounts = load_json(ACCOUNTS_FILE)
    pending = load_json(PENDING_FILE)
    applied = load_json(APPLIED_FILE)
    failed = load_json(FAILED_FILE)
    
    if not pending:
        print("No pending jobs")
        return
    
    jobs_done = 0
    
    while pending:
        if max_jobs and jobs_done >= max_jobs:
            break
            
        account = get_available_account(accounts)
        if not account:
            print("No available accounts")
            break
        
        job = pending.pop(0)
        print(f"\n{'='*50}")
        print(f"Job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        print(f"Account: {account['gmail']}")
        
        agent = Agent(account)
        success, message = agent.run(job)
        
        job['applied_at'] = datetime.now().isoformat()
        job['message'] = message
        
        if success:
            print(f"✅ {message}")
            applied.append(job)
        else:
            print(f"❌ {message}")
            failed.append(job)
            
            # Mark account if blocked
            if "blocked" in message.lower():
                account['status'] = 'blocked'
                save_json(ACCOUNTS_FILE, accounts)
        
        # Save after each job
        save_json(PENDING_FILE, pending)
        save_json(APPLIED_FILE, applied)
        save_json(FAILED_FILE, failed)
        
        jobs_done += 1
        
        # Delay between jobs
        time.sleep(5)
    
    print(f"\nDone. Applied: {len(applied)}, Failed: {len(failed)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=1)
    args = parser.parse_args()
    run(max_jobs=args.max)
