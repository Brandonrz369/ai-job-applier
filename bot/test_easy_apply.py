#!/usr/bin/env python3
"""
Easy Apply Test v3 - Uses central config, includes resume
"""
import asyncio
import sys
sys.path.insert(0, '/root/job_bot')

from config import APPLICANT, BROWSER_WS, MODELS, API_KEY, RESUME_PATH

def build_task(url):
    resume_instruction = f"Upload resume from: {RESUME_PATH}" if RESUME_PATH else "Skip resume if possible"
    
    return f"""
TASK: Apply to this job on Indeed
URL: {url}

CREDENTIALS (use for Indeed sign-in):
- Email: {APPLICANT['email']}
- Password: {APPLICANT['password']}

APPLICANT INFO (for form fields):
- Full Name: {APPLICANT['name']}
- Phone: {APPLICANT['phone']}
- Location: {APPLICANT['location']}
- Work Authorization: {APPLICANT['work_authorized']}
- Sponsorship Required: {APPLICANT['sponsorship_required']}
- Years Experience: {APPLICANT['years_experience']}

RESUME: {resume_instruction}

STEPS:
1. Click "Apply now" or "Easy Apply" button
2. If sign-in required:
   - Enter email: {APPLICANT['email']}
   - Click Continue
   - Enter password: {APPLICANT['password']}
   - Click Sign In
   - Do NOT use Google/Apple sign-in buttons
3. Fill all required form fields with info above
4. Upload resume if required
5. Click Submit/Continue until you see confirmation

RULES:
- NEVER close popups or modals - they are the path forward
- Use email/password login, NOT Google/Apple
- Say DONE when you see "Application submitted" or confirmation
- Say STUCK only if truly cannot proceed
"""

async def try_model(url, model_config):
    from browser_use import Agent, BrowserSession
    from browser_use.llm import ChatOpenAI
    
    print(f"\n{'='*60}")
    print(f"🤖 Model: {model_config['name']} (Tier {model_config['tier']})")
    print(f"   ID: {model_config['id']}")
    print(f"   Max steps: {model_config['steps']}")
    print(f"   Resume: {RESUME_PATH}")
    print(f"{'='*60}\n")
    
    try:
        llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY,
            model=model_config['id'],
        )
        
        browser = BrowserSession(cdp_url=BROWSER_WS)
        agent = Agent(task=build_task(url), llm=llm, browser_session=browser)
        result = await agent.run(max_steps=model_config['steps'])
        
        result_str = str(result).lower()
        
        # Success indicators
        success = any(x in result_str for x in [
            "application submitted", "successfully applied", 
            "application complete", "thank you for applying",
            "application sent"
        ])
        
        # Failure indicators  
        failure = any(x in result_str for x in [
            "unable to complete", "could not", "failed", "stuck",
            "cannot proceed"
        ])
        
        if success and not failure:
            return True, result
        return False, result
            
    except Exception as e:
        return False, str(e)

async def main(url):
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              INDEED EASY APPLY TEST v3                       ║
╠══════════════════════════════════════════════════════════════╣
║  Applicant: {APPLICANT['name']}
║  Email: {APPLICANT['email']}
║  Resume: {RESUME_PATH.split('/')[-1] if RESUME_PATH else 'None'}
╚══════════════════════════════════════════════════════════════╝
""")
    
    for model in MODELS:
        success, result = await try_model(url, model)
        
        if success:
            print(f"\n✅ SUCCESS with {model['name']}!")
            print(f"   Result: {str(result)[:200]}")
            return True
        else:
            print(f"\n❌ {model['name']} failed")
            print(f"   Result: {str(result)[:200]}")
            print(f"\n⬆️ Escalating...\n")
    
    print("\n😞 ALL MODELS FAILED")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_easy_apply.py <indeed_url>")
        print("\nConfig check:")
        print(f"  Resume: {RESUME_PATH}")
        print(f"  Applicant: {APPLICANT['name']}")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
