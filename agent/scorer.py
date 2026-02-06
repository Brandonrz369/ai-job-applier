import google.generativeai as genai
import json
import os
import re
import hashlib
import logging
from dotenv import load_dotenv
from candidate_profile import CANDIDATE_FULL_PROFILE

load_dotenv()

# ============================================
# LOGGING
# ============================================
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================
GEMINI_MODEL = os.getenv("GEMINI_SCORER_MODEL", "gemini-2.5-flash")

# Configure Gemini with JSON response mode
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    GEMINI_MODEL,
    generation_config={"response_mime_type": "application/json"},
)

# ============================================
# PRE-LLM FILTERS (saves API calls)
# ============================================

# Title words that auto-reject (case-insensitive)
TITLE_BLOCKLIST = [
    # Seniority
    r'\bsenior\b', r'\bsr\.?\b', r'\bprincipal\b', r'\bstaff\b',
    r'\blead\b', r'\bdirector\b', r'\bvp\b', r'\bhead of\b', r'\bchief\b',
    # Architecture (always senior)
    r'\barchitect\b',
    # Non-IT career tracks
    r'\bintern\b', r'\binternship\b', r'\bco-op\b', r'\bstudent\b', r'\bvolunteer\b',
    r'\baccount manager\b', r'\baccount executive\b', r'\bsales\b',
    r'\bbusiness development\b', r'\brecruiter\b',
    r'\bproduct manager\b', r'\bprogram manager\b',
    r'\bmarketing\b', r'\bcustomer success\b',
    r'\bregistered nurse\b', r'\b(?:rn|cna|lpn|medical assistant)\b',
    r'\bexecutive assistant\b', r'\badministrative\b', r'\breceptionist\b',
    r'\bwarehouse\b', r'\blogistics\b', r'\bforklift\b',
    r'\breal estate\b', r'\binsurance agent\b',
    r'\bdiesel\b', r'\bmechanic\b', r'\belectrician\b', r'\bplumber\b',
    r'\bcustodian\b', r'\bjanitor\b', r'\bmaintenance tech\b',
]

# Title words that auto-reject for wrong tech track
TECH_BLOCKLIST = [
    r'\bsoftware engineer\b', r'\bsoftware developer\b',
    r'\bfull.?stack\b', r'\bfrontend\b', r'\bbackend\b',
    r'\bweb developer\b', r'\bweb analytics\b',
    r'\bdevops engineer\b', r'\b(?:sre|site reliability)\b',
    r'\bplatform engineer\b', r'\bcloud engineer\b',
    r'\bdata engineer\b', r'\bdata scientist\b', r'\bml engineer\b',
    r'\bai engineer\b', r'\bbusiness intelligence\b',
    r'\btechnical program manager\b',
]

# Manager is allowed ONLY with IT/tech context
MANAGER_PATTERN = re.compile(r'\bmanager\b', re.IGNORECASE)
IT_MANAGER_OK = re.compile(r'\b(?:it|help desk|service desk|network|infrastructure)\s+manager\b', re.IGNORECASE)


def pre_filter_job(title: str) -> tuple:
    """Fast Python-based pre-filter. Returns (pass, reason) without API call.

    Returns:
        (True, None) if job should proceed to LLM scoring
        (False, reason) if job should be auto-rejected
    """
    t = title.lower().strip()

    # Check title blocklist
    for pattern in TITLE_BLOCKLIST:
        if re.search(pattern, t):
            return False, f"Title blocked: matches '{pattern}'"

    # Check tech blocklist
    for pattern in TECH_BLOCKLIST:
        if re.search(pattern, t):
            return False, f"Wrong tech track: matches '{pattern}'"

    # Manager check: block unless IT-context manager
    if MANAGER_PATTERN.search(t) and not IT_MANAGER_OK.search(t):
        return False, "Manager title without IT context"

    return True, None


# ============================================
# DEDUPLICATION
# ============================================

_seen_hashes = set()


def job_hash(company: str, title: str) -> str:
    """Create a normalized hash for company+title dedup."""
    key = f"{company.lower().strip()}|{title.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def is_duplicate(company: str, title: str) -> bool:
    """Check if we've already seen this company+title combo."""
    h = job_hash(company, title)
    if h in _seen_hashes:
        return True
    _seen_hashes.add(h)
    return False


# ============================================
# LLM SCORER
# ============================================

def score_job(job: dict) -> dict:
    """Score a job listing. Applies pre-filter first, then LLM if needed."""
    title = job.get('title', 'Unknown')
    company = job.get('company', 'Unknown')

    # Pre-filter: fast Python check
    passes, reject_reason = pre_filter_job(title)
    if not passes:
        logger.debug(f"Pre-filtered: {company} - {title} | {reject_reason}")
        return {
            "score": 0,
            "recommendation": "NO",
            "estimated_salary": "Unknown",
            "reason": f"Pre-filter: {reject_reason}",
        }

    # LLM scoring
    prompt = f"""You are a strict job-fit scorer for an IT support/infrastructure professional.

CANDIDATE CONTEXT:
- NO formal degree (100% self-taught)
- ~2 years formal IT experience (Fusion Contact Centers 2016-2017, Geeks-On-Site 2021)
- Running own MSP (LB Computer Help) since April 2025 -- treat this as L2/L3 SysAdmin experience
- Core skills: Help Desk, Active Directory, Windows Server, FortiGate firewalls, VoIP/8x8/SIP, M365 Admin, Veeam, N-Able RMM
- Location: Anaheim, CA / Orange County
- Available: On-site (OC/LA), Hybrid, Limited Remote

FULL PROFILE:
{CANDIDATE_FULL_PROFILE}

JOB TO SCORE:
Company: {company}
Title: {title}
Location: {job.get('location', 'Unknown')}
Pay: {job.get('pay', 'Not listed')}
Description:
{job.get('description', 'No description')[:3000]}

============================================================
SCORING RULES
============================================================

STEP 1: DEGREE REQUIREMENTS
- If "Bachelor's degree required" with NO "or equivalent experience" alternative AND company is large (500+ employees): Score 2, recommend NO
- If "degree preferred" or "or equivalent experience": Do NOT disqualify
- Small/mid companies (<500 employees) are usually flexible on degrees

STEP 2: EXPERIENCE REQUIREMENTS
- If requires 5+ years in a specific technology the candidate lacks: Score NO
- If requires 3+ years and candidate has 2: Allow if skills match well (MSP owner experience counts)
- Treat MSP ownership as equivalent to L2/L3 SysAdmin -- do NOT penalize for "Owner" title

STEP 3: ROLE FIT
STRONG FIT (score 7-9):
- IT Support, Help Desk, Desktop Support, IT Technician, IT Specialist
- Junior/Associate Systems Administrator, Network Administrator
- MSP Technician, Field Service Technician, On-site Technician
- NOC Technician, Data Center Technician, VoIP Technician
- IT Coordinator, IT Administrator, Endpoint Engineer

MODERATE FIT (score 5-7):
- Junior Security Analyst, Junior SOC Analyst (entry-level)
- M365 Administrator, Firewall Administrator
- IT Project Coordinator, Junior Infrastructure Engineer
- IT Consultant (SMB/MSP context)

NOT A FIT (score 1-3):
- Roles requiring deep specialization candidate lacks
- Customer Support/Success (non-technical, SaaS account management)
- Business Consultant, Emergency Management (non-IT)
- Roles at FAANG/Big 4 where no-degree will be HR-filtered

STEP 4: SALARY
- MINIMUM: $55,000/year. Below that = NO
- Estimate conservatively if not listed

STEP 5: LOCATION
- On-site roles must be within reasonable commute of Anaheim/OC/LA area
- Remote roles anywhere in the US are fine
- On-site roles in other states: Score NO unless relocation offered

Return JSON with these exact keys:
- "score": integer 1-10
- "recommendation": "YES" or "NO"
- "estimated_salary": string like "$65,000"
- "reason": one sentence explaining the score
- "degree_required": true/false (is a degree strictly required with no equivalent?)

THRESHOLD: Score 6+ = YES. Score 5 or below = NO.
Be STRICT. When in doubt, NO."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown blocks (safety fallback even with JSON mode)
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        result = json.loads(text)

        # Enforce no MAYBE
        if result.get('recommendation') == 'MAYBE':
            result['recommendation'] = 'NO'
            result['reason'] = f"Borderline - defaulting to NO. {result.get('reason', '')}"

        logger.info(f"Scored: {company[:20]} - {title[:35]} | {result.get('score')}/10 {result.get('recommendation')} | {result.get('reason', '')[:60]}")
        return result

    except json.JSONDecodeError as e:
        raw = response.text[:200] if 'response' in dir() else 'No response'
        logger.error(f"JSON parse error for {company} - {title}: {e} | Raw: {raw}")
        return {"score": 0, "recommendation": "NO", "estimated_salary": "Unknown", "reason": f"JSON parse error: {e}"}

    except Exception as e:
        logger.error(f"Scoring error for {company} - {title}: {e}")
        return {"score": 0, "recommendation": "NO", "estimated_salary": "Unknown", "reason": f"Scoring error: {e}"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    test_jobs = [
        # Should be YES -- core fit
        {"company": "Kaiser Permanente", "title": "IT Support Specialist", "location": "Irvine, CA",
         "description": "IT Support Specialist for help desk, Active Directory, VoIP phones. 2+ years required. $60K-75K."},
        # Should be YES -- strong fit
        {"company": "Apex Systems", "title": "Desktop Support Technician", "location": "Anaheim, CA",
         "description": "Break-fix support, Windows 10/11, Active Directory, printer support. 1-3 years experience. $55K-65K."},
        # Should be YES -- moderate fit
        {"company": "Managed IT Solutions", "title": "MSP Field Technician", "location": "Orange, CA",
         "description": "On-site support for SMB clients. Firewalls, VoIP, M365 admin. Must have reliable vehicle. $55K-70K."},
        # Should be NO -- pre-filter: senior title
        {"company": "Amazon", "title": "Sr. Customer Solutions Manager, Games", "location": "Irvine, CA",
         "description": "7+ years leading large-scale technical programs. C-suite engagement. $138K-187K."},
        # Should be NO -- pre-filter: account manager
        {"company": "Pavion", "title": "Jr Account Manager", "location": "Cypress, CA",
         "description": "B2B sales, account management, RFP responses, sales quotas. Bachelor's preferred. $65K."},
        # Should be NO -- pre-filter: sr + web analytics
        {"company": "AXS", "title": "Sr. Web Analytics Developer", "location": "Los Angeles, CA",
         "description": "Adobe Analytics, JavaScript, tag management. 4-6 years web analytics. $111K-157K."},
        # Should be NO -- pre-filter: technical program manager
        {"company": "Amazon", "title": "Technical Program Manager - Music Growth Tech", "location": "Culver City, CA",
         "description": "3+ years TPM, 2+ years software development. Bachelor's required. $127K-172K."},
        # Should be NO -- pre-filter: executive assistant
        {"company": "County of Riverside", "title": "Executive Assistant IV", "location": "Riverside, CA",
         "description": "Administrative support for department head. Calendar management, correspondence, filing."},
        # Should be NO -- pre-filter: intern
        {"company": "Motorola Solutions", "title": "Intern - Applications Engineer I", "location": "Schaumburg, IL",
         "description": "Summer internship for engineering students. Currently enrolled in CS/EE program. $25/hr."},
        # Edge case: should be YES -- IT Manager at small company
        {"company": "Small Biz Co", "title": "IT Manager", "location": "Fullerton, CA",
         "description": "Manage IT for 30-person company. AD, M365, firewall, help desk. 2+ years. $70K-85K."},
        # Edge case: should be NO -- non-IT customer support
        {"company": "Cryptio", "title": "Customer Support Executive", "location": "Remote",
         "description": "Handle customer inquiries for crypto accounting platform. SaaS support, Zendesk. $70K."},
    ]

    print("=" * 70)
    print("SCORER v2 TEST - Pre-filter + LLM")
    print("=" * 70)

    pre_filtered = 0
    llm_scored = 0

    for job in test_jobs:
        passes, reason = pre_filter_job(job['title'])
        if not passes:
            pre_filtered += 1
            print(f"\n[PRE-FILTER] {job['title']} at {job['company']}")
            print(f"  BLOCKED: {reason}")
        else:
            llm_scored += 1
            result = score_job(job)
            rec = result.get('recommendation', 'ERROR')
            score = result.get('score', 0)
            salary = result.get('estimated_salary', 'Unknown')
            rsn = result.get('reason', 'No reason')
            degree = result.get('degree_required', 'N/A')
            print(f"\n[LLM] {job['title']} at {job['company']}")
            print(f"  Score: {score}/10 | Rec: {rec} | Salary: {salary} | Degree req: {degree}")
            print(f"  Reason: {rsn}")

    print(f"\n{'=' * 70}")
    print(f"Pre-filtered: {pre_filtered} | LLM scored: {llm_scored} | Total: {len(test_jobs)}")
    print(f"API calls saved: {pre_filtered}/{len(test_jobs)} ({pre_filtered/len(test_jobs)*100:.0f}%)")
