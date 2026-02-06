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
    prompt = f"""You are a job-fit scorer for an IT professional. Score this job based on STRICT salary and role criteria.

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
SCORING RULES - FOLLOW EXACTLY
============================================================

STEP 1: ESTIMATE SALARY
- If salary is listed: Use it directly
- If NOT listed: Estimate based on title, company size, industry, location
- Express as annual salary (e.g., "$65,000" or "$45,000")

STEP 2: APPLY SALARY FILTER
- MINIMUM: $60,000/year ($28.85/hour)
- If estimated salary < $60K → Score NO regardless of role fit

STEP 3: APPLY ROLE FILTER

ALWAYS YES (if salary passes):
- IT Support, Help Desk, Desktop Support, Technical Support
- Systems Administrator, Network Administrator, Network Engineer
- DevOps, SRE, Platform Engineer, Infrastructure Engineer
- MSP Technician, Field Service Technician, IT Consultant
- Security Engineer, Security Analyst, SOC Analyst
- Cloud Engineer, Solutions Architect, Technical Account Manager
- Automation Engineer, Integration Engineer, RPA Developer
- Technical Writer, IT Project Manager, IT Coordinator
- NOC Technician, Data Center Technician
- Any role with "Technical" or "Engineer" in IT context

YES IF SALARY $60K+ (business roles that pay well):
- Marketing Manager/Director (not coordinator)
- Account Executive, Account Manager (enterprise/tech sales)
- Business Development (if tech-focused)
- Recruiter (technical recruiter)
- Product Manager, Program Manager (tech companies)
- Customer Success Manager (at software/tech companies)

ALWAYS NO (regardless of salary):
- Sales Representative, Sales Associate, Sales Consultant (retail/B2C sales)
- Medical/Healthcare roles (RN, CNA, Medical Assistant, etc.)
- Administrative Assistant, Executive Assistant, Office Manager
- Receptionist, Front Desk (any industry)
- Records Coordinator, Claims Processor, Data Entry Clerk
- Program Coordinator (non-tech, education, non-profit)
- Warehouse, Logistics, Shipping/Receiving
- Food Service, Retail Store roles
- Real Estate Agent, Insurance Agent
- Requires security clearance candidate doesn't have
- Senior/Principal/Staff level requiring 10+ years explicitly

============================================================
RESPOND IN JSON ONLY - NO OTHER TEXT
============================================================
{{
    "score": <1-10>,
    "recommendation": "YES" | "NO",
    "estimated_salary": "<estimated annual salary like $65,000>",
    "reason": "<one sentence: why YES or NO, mention salary if relevant>"
}}

IMPORTANT:
- No "MAYBE" - commit to YES or NO
- If unsure about salary, estimate conservatively
- Be STRICT about the NO list - these roles waste application credits"""

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
        {
            "company": "Kaiser Permanente",
            "title": "IT Support Specialist",
            "location": "Irvine, CA",
            "description": "IT Support Specialist for help desk, Active Directory, VoIP phones. 2+ years required."
        },
        {
            "company": "Ignite Solutions",
            "title": "Customer Service Associate",
            "location": "Long Beach, CA",
            "description": "B2B sales role selling AT&T fiber and VoIP to businesses. Commission-based, $3600-5200/month."
        },
        {
            "company": "County of Riverside",
            "title": "Executive Assistant IV",
            "location": "Riverside, CA",
            "description": "Administrative support for department head. Calendar management, correspondence, filing."
        },
        {
            "company": "Amazon",
            "title": "Systems Development Engineer",
            "location": "Seattle, WA",
            "description": "Design and implement scalable infrastructure. AWS, Python, Linux. $150K-200K base."
        },
    ]
    for job in test_jobs:
        result = score_job(job)
        print(f"{job['title']} at {job['company']}: {json.dumps(result, indent=2)}")
        print()
