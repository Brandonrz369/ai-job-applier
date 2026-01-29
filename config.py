"""
Central config for job application system
Both test scripts and production applier use this
"""
from pathlib import Path
import json

# ============ PATHS ============
BASE_DIR = Path("/root/job_bot")
OUTPUT_DIR = Path("/root/output")
QUEUE_DIR = BASE_DIR / "queue"
LOGS_DIR = BASE_DIR / "logs"

# ============ BROWSER ============
BROWSER_WS = "wss://REDACTED_BRIGHTDATA_CREDENTIALS:REDACTED_PASSWORD@brd.superproxy.io:9222"

# ============ APPLICANT INFO ============
APPLICANT = {
    "name": "Brandon Ruiz",
    "email": "brandonlruiz98@gmail.com",
    "password": "REDACTED_PASSWORD",
    "phone": "775-530-8234",
    "location": "Anaheim, CA",
    "linkedin": "linkedin.com/in/yourusername",
    "github": "github.com/brandonrz369",
    "work_authorized": "Yes",
    "sponsorship_required": "No",
    "years_experience": "3",
}

# ============ RESUME ============
# Use most recent resume, or set a specific one
def get_resume_path():
    """Get most recent resume PDF"""
    resumes = sorted(OUTPUT_DIR.glob("*_Resume.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)
    if resumes:
        return str(resumes[0])
    # Fallback - any PDF
    pdfs = sorted(OUTPUT_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)
    return str(pdfs[0]) if pdfs else None

RESUME_PATH = get_resume_path()

# ============ MODELS (with escalation) ============
MODELS = [
    # Tier 1: Cheap, oscillate between these
    {"id": "google/gemini-2.0-flash-001", "name": "Gemini Flash", "steps": 15, "tier": 1},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "steps": 15, "tier": 1},
    {"id": "google/gemini-2.0-flash-001", "name": "Gemini Flash v2", "steps": 15, "tier": 1},
    
    # Tier 2: Mid-range
    {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro", "steps": 20, "tier": 2},
    
    # Tier 3: Premium (last resort)
    {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet", "steps": 25, "tier": 3},
]

# ============ API KEY ============
def get_api_key():
    env_file = BASE_DIR / "agent" / ".env"
    if env_file.exists():
        for line in env_file.read_text().split('\n'):
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("No API key found in .env")

API_KEY = get_api_key()

# ============ PRINT CONFIG ============
if __name__ == "__main__":
    print(f"Resume: {RESUME_PATH}")
    print(f"Applicant: {APPLICANT['name']} <{APPLICANT['email']}>")
    print(f"Models: {[m['name'] for m in MODELS]}")
    print(f"API Key: {API_KEY[:20]}...")
