import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from candidate_profile import CANDIDATE_FULL_PROFILE

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def score_job(job: dict) -> dict:
    prompt = f"""You are a strict job-fit scorer for an IT support/infrastructure professional with NO formal degree, ~2 years formal IT experience + running his own MSP since 2025. Score ONLY roles he can realistically get hired for.

CANDIDATE:
{CANDIDATE_FULL_PROFILE}

JOB:
Company: {job.get('company', 'Unknown')}
Title: {job.get('title', 'Unknown')}
Location: {job.get('location', 'Unknown')}
Pay: {job.get('pay', 'Not listed')}
Description:
{job.get('description', 'No description')[:3000]}

============================================================
SCORING RULES - FOLLOW EXACTLY IN ORDER
============================================================

STEP 1: CHECK TITLE-LEVEL DISQUALIFIERS
If the title contains ANY of these words, score NO immediately:
- Senior, Sr., Principal, Staff, Lead, Director, VP, Head of, Chief
- Manager (UNLESS it is "IT Manager" at a small company with <50 employees)
- Architect (Solutions Architect, Security Architect, Cloud Architect, etc.)
These roles require 5-10+ years of specialized experience the candidate does not have.

STEP 2: CHECK ROLE-TYPE DISQUALIFIERS
Score NO if the role is any of these -- they are NOT the candidate's career track:
- Software Engineer/Developer, Full-Stack, Backend, Frontend, Web Developer
- DevOps Engineer, SRE, Platform Engineer (requires CS background + heavy coding)
- Cloud Engineer, Cloud Architect (requires deep AWS/Azure/GCP expertise)
- Data Engineer, Data Scientist, Data Analyst, ML Engineer, AI Engineer
- Web Analytics, Business Intelligence Developer
- Technical Program Manager, Product Manager, Program Manager
- Account Manager, Account Executive, Business Development, Sales (any kind)
- Customer Success Manager
- Marketing Manager/Director, Recruiter
- Technical Writer (as primary role)
- Medical/Healthcare roles (RN, CNA, etc.)
- Administrative Assistant, Executive Assistant, Office Manager, Receptionist
- Warehouse, Logistics, Shipping, Food Service, Retail
- Real Estate, Insurance Agent
- Any role requiring security clearance candidate doesn't have

STEP 3: CHECK HARD REQUIREMENTS
Score NO if the job REQUIRES (not prefers) any of these:
- Bachelor's or Master's degree (with no "or equivalent experience" alternative)
- 5+ years of experience in a specific technology
- Specific certifications the candidate lacks (CISSP, CCNA, CyberArk CDE, PMP, etc.)
- Software development experience (2+ years coding in Java, C++, Go, etc.)
NOTE: If the listing says "degree OR equivalent experience", that does NOT disqualify.

STEP 4: ESTIMATE SALARY
- If salary listed: Use it
- If NOT listed: Estimate conservatively based on title/company/location
- MINIMUM: $55,000/year ($26.50/hour)
- If estimated salary < $55K, score NO

STEP 5: SCORE ROLE FIT (only if passed steps 1-4)

STRONG FIT (score 7-9) -- candidate's core competencies:
- IT Support Specialist, Help Desk Technician, Desktop Support
- IT Technician, IT Specialist, IT Generalist
- Junior/Associate Systems Administrator
- Junior/Associate Network Administrator
- MSP Technician, Field Service Technician, On-site Technician
- NOC Technician, Data Center Technician
- VoIP Technician, Telecom Support
- IT Coordinator, IT Administrator (small/mid company)
- Endpoint Engineer/Technician

MODERATE FIT (score 5-7) -- candidate has SOME relevant skills:
- Junior Security Analyst, Junior SOC Analyst (entry-level only)
- IT Project Coordinator (not Manager)
- M365 Administrator (entry to mid level)
- Junior Infrastructure Engineer
- IT Consultant (small business / MSP context)
- Firewall Administrator (entry to mid level)

WEAK FIT (score 3-4) -- stretch roles, likely won't get hired:
- Anything requiring deep specialization candidate lacks
- Roles at large enterprises with rigid hiring (FAANG, Big 4, etc.)
- Roles where "no degree" will be filtered out by HR systems

============================================================
RESPOND IN JSON ONLY - NO OTHER TEXT
============================================================
{{
    "score": <1-10>,
    "recommendation": "YES" | "NO",
    "estimated_salary": "<estimated annual salary like $65,000>",
    "reason": "<one sentence explaining fit or rejection>"
}}

SCORING THRESHOLD:
- Score 6+ = YES (apply)
- Score 5 or below = NO (skip)
- No "MAYBE" -- commit to YES or NO
- Be STRICT -- every bad application wastes $0.005 in browser credits and time
- When in doubt, say NO -- it's better to skip a borderline job than waste a credit on one that will reject us"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        result = json.loads(text)

        # Ensure no MAYBE slips through
        if result.get('recommendation') == 'MAYBE':
            result['recommendation'] = 'NO'
            result['reason'] = f"Borderline - defaulting to NO. {result.get('reason', '')}"

        return result

    except Exception as e:
        return {"score": 1, "recommendation": "NO", "estimated_salary": "Unknown", "reason": f"Scoring error: {e}"}


if __name__ == "__main__":
    test_jobs = [
        # Should be YES -- core fit
        {
            "company": "Kaiser Permanente",
            "title": "IT Support Specialist",
            "location": "Irvine, CA",
            "description": "IT Support Specialist for help desk, Active Directory, VoIP phones. 2+ years required. $60K-75K."
        },
        # Should be YES -- strong fit
        {
            "company": "Apex Systems",
            "title": "Desktop Support Technician",
            "location": "Anaheim, CA",
            "description": "Break-fix support, Windows 10/11, Active Directory, printer support. 1-3 years experience. $55K-65K."
        },
        # Should be YES -- moderate fit
        {
            "company": "Managed IT Solutions",
            "title": "MSP Field Technician",
            "location": "Orange, CA",
            "description": "On-site support for SMB clients. Firewalls, VoIP, M365 admin. Must have reliable vehicle. $55K-70K."
        },
        # Should be NO -- senior title
        {
            "company": "Amazon",
            "title": "Sr. Customer Solutions Manager, Games",
            "location": "Irvine, CA",
            "description": "7+ years leading large-scale technical programs. C-suite engagement. $138K-187K."
        },
        # Should be NO -- wrong career track (sales)
        {
            "company": "Pavion",
            "title": "Jr Account Manager",
            "location": "Cypress, CA",
            "description": "B2B sales, account management, RFP responses, sales quotas. Bachelor's preferred. $65K."
        },
        # Should be NO -- wrong career track (software dev)
        {
            "company": "AXS",
            "title": "Sr. Web Analytics Developer",
            "location": "Los Angeles, CA",
            "description": "Adobe Analytics, JavaScript, tag management. 4-6 years web analytics. $111K-157K."
        },
        # Should be NO -- requires degree + too senior
        {
            "company": "Amazon",
            "title": "Technical Program Manager - Music Growth Tech",
            "location": "Culver City, CA",
            "description": "3+ years TPM, 2+ years software development, system-level technical design. Bachelor's required. $127K-172K."
        },
        # Should be NO -- executive assistant
        {
            "company": "County of Riverside",
            "title": "Executive Assistant IV",
            "location": "Riverside, CA",
            "description": "Administrative support for department head. Calendar management, correspondence, filing."
        },
    ]
    print("=" * 60)
    print("SCORER TEST - Expected results noted for each job")
    print("=" * 60)
    for job in test_jobs:
        result = score_job(job)
        rec = result.get('recommendation', 'ERROR')
        score = result.get('score', 0)
        salary = result.get('estimated_salary', 'Unknown')
        reason = result.get('reason', 'No reason')
        print(f"\n{job['title']} at {job['company']}")
        print(f"  Score: {score}/10 | Rec: {rec} | Salary: {salary}")
        print(f"  Reason: {reason}")
