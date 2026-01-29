import time
import re
import requests
import logging

log = logging.getLogger(__name__)

def solve_cloudflare(page, capsolver_key):
    """Use CapSolver to bypass Cloudflare Turnstile"""
    log.info("Using CapSolver for Cloudflare...")
    
    # Extract sitekey
    html = page.content()
    sitekey = None
    
    # Try iframe src first
    try:
        iframe = page.locator('iframe[src*="challenges.cloudflare"]').first
        if iframe.count() > 0:
            src = iframe.get_attribute('src')
            match = re.search(r'k=([^&]+)', src)
            if match:
                sitekey = match.group(1)
    except:
        pass
    
    # Try data-sitekey
    if not sitekey:
        match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
        if match:
            sitekey = match.group(1)
    
    if not sitekey:
        log.error("No sitekey found")
        return False
    
    log.info(f"Sitekey: {sitekey[:20]}...")
    
    # Create CapSolver task
    try:
        resp = requests.post("https://api.capsolver.com/createTask", json={
            "clientKey": capsolver_key,
            "task": {
                "type": "AntiTurnstileTaskProxyLess",
                "websiteURL": page.url,
                "websiteKey": sitekey
            }
        }, timeout=30)
        
        result = resp.json()
        log.info(f"CapSolver response: {result}")
        
        if result.get('errorId', 0) != 0:
            log.error(f"CapSolver error: {result.get('errorDescription')}")
            return False
        
        task_id = result.get('taskId')
        log.info(f"Task ID: {task_id}")
        
        # Poll for result
        for i in range(20):
            time.sleep(3)
            resp = requests.post("https://api.capsolver.com/getTaskResult", json={
                "clientKey": capsolver_key,
                "taskId": task_id
            }, timeout=30)
            
            result = resp.json()
            status = result.get('status')
            log.info(f"Poll {i+1}: {status}")
            
            if status == 'ready':
                token = result.get('solution', {}).get('token')
                log.info(f"Got token: {token[:50]}...")
                
                # Inject token and reload
                page.evaluate(f"""
                    var el = document.querySelector('[name="cf-turnstile-response"]');
                    if (el) el.value = '{token}';
                """)
                time.sleep(1)
                page.reload()
                time.sleep(3)
                
                if 'verify' not in page.content().lower():
                    log.info("Cloudflare PASSED!")
                    return True
                return False
                
            elif status == 'failed':
                log.error(f"CapSolver failed: {result}")
                return False
        
        log.error("CapSolver timeout")
        return False
        
    except Exception as e:
        log.error(f"CapSolver exception: {e}")
        return False
