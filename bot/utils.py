"""
Job Bot Utilities - Helper classes for improved success rate
Generated with Gemini MCP assistance
"""

import time
import re
import logging
from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, List

logger = logging.getLogger("JobBot.Utils")


# ============================================
# STUCK DETECTION SYSTEM
# ============================================

@dataclass(frozen=True)
class ActionRecord:
    action_type: str
    selector: Optional[str]
    url: str
    timestamp: float


class StuckDetectionSystem:
    """
    Analyzes browser automation patterns to detect loops, dead-ends,
    or logic failures.
    """

    def __init__(self, history_size: int = 10):
        self.history: deque[ActionRecord] = deque(maxlen=history_size)

        # Configuration thresholds
        self.REPETITION_THRESHOLD = 3
        self.URL_STAGNATION_THRESHOLD = 5

        # Scoring weights
        self.WEIGHT_REPETITION = 7.0
        self.WEIGHT_STAGNATION = 4.0

    def record_action(self, action_type: str, url: str, selector: Optional[str] = None):
        """Logs a new action into the history buffer."""
        record = ActionRecord(
            action_type=action_type.lower().strip(),
            selector=selector.strip() if selector else None,
            url=url,
            timestamp=time.time()
        )
        self.history.append(record)

    def _check_consecutive_repeats(self) -> bool:
        """Checks if the exact same action was performed N times in a row."""
        if len(self.history) < self.REPETITION_THRESHOLD:
            return False

        last_n = list(self.history)[-self.REPETITION_THRESHOLD:]
        first = last_n[0]

        return all(
            item.action_type == first.action_type and item.selector == first.selector
            for item in last_n
        )

    def _check_url_stagnation(self) -> bool:
        """Checks if the URL has remained unchanged for N actions."""
        if len(self.history) < self.URL_STAGNATION_THRESHOLD:
            return False

        last_n = list(self.history)[-self.URL_STAGNATION_THRESHOLD:]
        first_url = last_n[0].url

        return all(item.url == first_url for item in last_n)

    def get_analysis(self) -> Dict:
        """
        Calculates the stuck score and provides a recommendation.
        Returns: Dict containing score (0-10) and recommendation.
        """
        score = 0.0
        reasons = []

        # 1. Check for consecutive repetition (High signal)
        if self._check_consecutive_repeats():
            score += self.WEIGHT_REPETITION
            reasons.append(f"Detected {self.REPETITION_THRESHOLD} consecutive identical actions.")

        # 2. Check for URL stagnation (Medium signal)
        if self._check_url_stagnation():
            score += self.WEIGHT_STAGNATION
            reasons.append(f"URL unchanged for last {self.URL_STAGNATION_THRESHOLD} actions.")

        # Cap score at 10
        final_score = min(float(score), 10.0)

        # Determine recommendation
        if final_score >= 8.0:
            recommendation = "abort"
        elif final_score >= 4.0:
            recommendation = "rescue"
        else:
            recommendation = "continue"

        return {
            "stuck_score": final_score,
            "recommendation": recommendation,
            "reasons": reasons,
            "history_count": len(self.history)
        }

    def reset(self):
        """Clear history for new job application session."""
        self.history.clear()


# ============================================
# COOKIE HEALTH CHECK
# ============================================

async def check_cookie_health(page) -> bool:
    """
    Checks if the current Playwright session (cookies) is still valid on Indeed.

    Args:
        page: The Playwright page instance from your BrowserSession.

    Returns:
        bool: True if logged in, False if session expired or redirected.
    """
    target_url = "https://www.indeed.com/account/view"

    try:
        logger.info(f"Checking session health at {target_url}...")

        # Navigate with a 30-second timeout
        response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

        if not response:
            logger.error("Failed to get a response from Indeed.")
            return False

        # Wait for redirects to settle
        await page.wait_for_timeout(2000)

        current_url = page.url
        logger.debug(f"Current URL after navigation: {current_url}")

        # Check for redirection to Login/Auth pages
        if "/auth" in current_url or "/login" in current_url:
            logger.warning("Session Health: EXPIRED (Redirected to login page)")
            return False

        # Check for existence of Profile-specific elements
        logged_in_selectors = [
            "button#account-menu-trigger",
            "div.gnav-AccountMenu",
            "a[href*='mysession']",
            "h1:has-text('Profile')",
            "[data-testid='settings-page-container']"
        ]

        for selector in logged_in_selectors:
            try:
                if await page.is_visible(selector, timeout=3000):
                    logger.info("Session Health: VALID (User profile visible)")
                    return True
            except:
                continue

        logger.warning("Session Health: UNCERTAIN (Logged-in elements not found)")
        return False

    except Exception as e:
        logger.error(f"Session health check error: {str(e)}")
        return False


# ============================================
# EXPANDED SUCCESS DETECTION
# ============================================

async def detect_application_success(page) -> Dict:
    """
    Analyzes the current page to determine if a job application was successful.
    Returns: dict with is_success, confidence score, and the triggering pattern.
    """
    url = page.url.lower()

    # 1. High Confidence: URL Patterns
    url_patterns = [
        r"/post-apply", r"/confirmation", r"/thank-you",
        r"/success", r"/applied", r"/complete", r"/thankyou"
    ]

    for pattern in url_patterns:
        if re.search(pattern, url):
            return {"is_success": True, "confidence": 100, "matched_pattern": f"URL: {pattern}"}

    # 2. Medium/High Confidence: Page Text Content
    try:
        content = await page.inner_text("body", timeout=5000)
        content_lower = content.lower()

        text_patterns = {
            "application complete": 95,
            "successfully applied": 95,
            "application has been submitted": 95,
            "your application was submitted": 95,
            "we got your application": 90,
            "we received your application": 90,
            "application received": 90,
            "congratulations": 85,
            "thank you for applying": 85,
            "thanks for applying": 85,
            "application sent": 80,
            "application has been sent": 80,
            "you have successfully applied": 80,
            "submitted": 55,  # Lower confidence - appears in other contexts
            "thank you": 45   # Generic
        }

        best_match = None
        highest_conf = 0

        for phrase, score in text_patterns.items():
            if phrase in content_lower:
                if score > highest_conf:
                    highest_conf = score
                    best_match = phrase

        if highest_conf >= 50:
            return {
                "is_success": True,
                "confidence": highest_conf,
                "matched_pattern": f"Text: '{best_match}'"
            }

    except Exception as e:
        logger.debug(f"Could not read page text: {e}")

    # 3. No success detected
    return {"is_success": False, "confidence": 0, "matched_pattern": None}


# ============================================
# IMPROVED TASK PROMPT
# ============================================

OPTIMIZED_TASK_PROMPT = """You are an expert Indeed Job Application Agent. Your goal is to apply to jobs efficiently and flawlessly. You must adhere to the following strict operational protocol:

**1. FORM FILLING STRATEGY (High Priority)**
- **BATCH FIRST:** When encountering *any* form inputs, your **first** move must always be to call `inject_form_data`. Do NOT click and type into individual fields unless injection fails completely.
- **STATE AWARENESS:** Maintain a mental map of the current form state. If a field is already populated correctly, skip it. Do not overwrite valid data.
- **REACT HANDLING:** If you must fill a field manually (because injection failed), you must use `humanize_form_field` immediately after clicking to trigger React change events.

**2. VALIDATION & SUBMISSION**
- **PRE-FLIGHT CHECK:** You are FORBIDDEN from clicking "Continue", "Next", "Submit", or "Apply" without first running `check_validation_errors`.
- **ERROR LOOP:** If `check_validation_errors` returns issues, you must fix the specific fields listed before attempting to proceed again.
- **VERIFICATION:** Periodically run `verify_indeed_easy_apply` to ensure you haven't been redirected to an external site.

**3. ERROR HANDLING & ESCALATION**
- **CAPTCHAS:** If a CAPTCHA appears, immediately call `solve_captcha`.
- **THE 3-STRIKE RULE:** If you attempt the exact same action (e.g., clicking a specific button or filling a specific field) 3 times and it fails or the page does not change, you MUST stop and call `ask_gemini_for_help` with a description of the stalemate.

**Execution Flow:**
1. Detect Form -> 2. `inject_form_data` -> 3. `check_validation_errors` -> 4. If Clean: Click Next/Submit. If Dirty: Fix -> Go to 3.

Start immediately. Analyze the current page state and execute."""


def build_optimized_task(job: dict, resume_path: str, applicant: dict, is_external: bool = False) -> str:
    """Build an optimized task prompt that enforces best practices."""

    job_url = job.get('url', '')
    job_title = job.get('title', 'Unknown')
    job_company = job.get('company', 'Unknown')

    email_to_use = applicant.get('email_external', applicant['email']) if is_external else applicant['email']

    resume_instruction = ""
    if resume_path:
        resume_instruction = f"""
RESUME UPLOAD (CRITICAL):
- You MUST upload this specific resume: {resume_path}
- If a resume is pre-filled, click "Replace resume" or "Remove" first
- Then upload the custom file: {resume_path}
"""

    success_criteria = """
SUCCESS CRITERIA (FLEXIBLE):
Report SUCCESS when you see ANY of these:
- "Application submitted/sent/received/complete"
- "Thank you for applying"
- "Congratulations"
- Any confirmation page after clicking Submit
Do NOT require exact text matching."""

    applicant_info = f"""
APPLICANT INFO:
- Name: {applicant['name']}
- Email: {email_to_use}
- Phone: {applicant['phone']}
- Location: {applicant.get('city', 'Anaheim')}, {applicant.get('state', 'CA')} {applicant.get('zip_code', '92805')}
- Address: {applicant.get('street_address', '')}
- Current Title: {applicant.get('current_job_title', 'IT Support Specialist')}
- Current Company: {applicant.get('current_company', 'Geek Squad')}
- Years Experience: {applicant.get('years_experience', '5')}
"""

    task = f"""{OPTIMIZED_TASK_PROMPT}

---
JOB: {job_title} at {job_company}
URL: {job_url}

{success_criteria}

{applicant_info}

{resume_instruction}

STANDARD ANSWERS:
- Work Authorization: Yes, authorized to work in the US
- Sponsorship: No, do not require sponsorship
- Yes/No qualifications: Answer "Yes" unless clearly unqualified
- Self-identification: "I do not want to answer"

FAILURE MODES TO REPORT:
- "EXTERNAL_SITE" - Redirected off Indeed
- "NEEDS_LOGIN" - Login required, cookies expired
- "JOB_UNAVAILABLE" - Job expired or removed
- "WAF_BLOCKED" - Bot detection triggered

Begin applying now."""

    return task
