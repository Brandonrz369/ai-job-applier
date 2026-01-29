import anthropic
import json
import os
from dotenv import load_dotenv
from candidate_profile import CANDIDATE_FULL_PROFILE

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def score_job(job: dict) -> dict:
    prompt = f"""You are a job-fit scorer. Score this job for the candidate below.

CANDIDATE:
{CANDIDATE_FULL_PROFILE}

JOB:
Company: {job.get('company', 'Unknown')}
Title: {job.get('title', 'Unknown')}
Location: {job.get('location', 'Unknown')}
Pay: {job.get('pay', 'Not listed')}
Description:
{job.get('description', 'No description')[:3000]}

SCORING RULES:

SCORE "YES" IF:
- Skills/experience roughly align (even 50% match is fine)
- Pay is $20+/hr or salary ~$42K+ (or pay not listed - assume it's fine)
- Role involves any of: IT, tech support, help desk, networking, systems admin,
  automation, AI/LLM, project coordination, technical writing, consulting,
  operations at a tech company, MSP work, documentation, DevOps, VoIP,
  field service, NOC, implementation, customer success (tech), RPA, integration

SCORE "NO" IF:
- Retail management (CVS store manager type roles)
- Food service, warehouse labor, manual labor
- Healthcare requiring clinical licenses (RN, CNA, LPN, etc.)
- Requires active security clearance that candidate does not have
- Senior/Principal/Staff/Architect level explicitly requiring 10+ years
- Completely unrelated field (accounting, legal, HR generalist, nursing, etc.)
- Pay is explicitly below $20/hr or below $42K salary

SCORE "MAYBE" IF:
- It's borderline - could go either way
- Role is adjacent to IT but unclear if it's a good fit
- Description is too vague to judge

IMPORTANT - IGNORE THESE "REQUIREMENTS" (treat as preferred, not required):
- Certifications (CCNA, CompTIA, AWS certs, Security+, etc.)
- Degree requirements (Bachelor's, Associate's, etc.)
- Specific years of experience numbers (e.g. "5+ years required")
The candidate learns fast and has done the work without formal credentials.
Do NOT score NO just because a cert or degree is listed as "required".

RESPOND IN JSON ONLY:
{{
    "score": <1-10>,
    "recommendation": "YES" | "MAYBE" | "NO",
    "reason": "<one sentence explaining why>"
}}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)

    except Exception as e:
        return {"score": 5, "recommendation": "MAYBE", "reason": f"Error: {e}"}


if __name__ == "__main__":
    test_jobs = [
        {
            "company": "Test Corp",
            "title": "IT Support Specialist",
            "location": "Irvine, CA",
            "description": "IT Support Specialist for help desk, Active Directory, VoIP phones. 2+ years required. CompTIA A+ preferred."
        },
        {
            "company": "CVS Health",
            "title": "Store Manager",
            "location": "Anaheim, CA",
            "description": "Manage daily store operations, staff scheduling, inventory management, customer service. Retail experience required."
        },
        {
            "company": "Tech Solutions Inc",
            "title": "Junior DevOps Engineer",
            "location": "Remote",
            "description": "Looking for Junior DevOps engineer. AWS, Docker, CI/CD pipelines. Bachelor's degree required. 5+ years experience preferred."
        },
    ]
    for job in test_jobs:
        result = score_job(job)
        print(f"{job['title']} at {job['company']}: {json.dumps(result, indent=2)}")
        print()
