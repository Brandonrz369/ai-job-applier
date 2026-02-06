"""
Job Application Agent using Browser-Use Cloud with US residential proxy
Focuses on Indeed Easy Apply only

IMPROVEMENTS (Feb 2026):
- Added hCaptcha support
- Fixed success detection (accepts variations)
- Added domain blocklist for complex ATS
- Added NaN/bad data filtering
- Switched to async aiohttp for CAPTCHA solving
- GEMINI RESCUE SYSTEM: Call Gemini when agent is stuck
- PHASE 2 IMPROVEMENTS (Feb 2026):
  - Cookie health check at startup
  - Stuck detection system
  - Optimized task prompt with form injection enforcement
  - Expanded success detection
"""
import asyncio
import json
import re
import time
import base64
from pathlib import Path
from dotenv import load_dotenv
import os
import aiohttp

# Import new utilities
from utils import (
    StuckDetectionSystem,
    check_cookie_health,
    detect_application_success,
    build_optimized_task,
    OPTIMIZED_TASK_PROMPT
)

# Gemini for "Rescue" system
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Load environment variables
load_dotenv(Path("/root/job_bot/agent/.env"))

# Browser-Use imports
from browser_use import Agent, Controller
from browser_use.agent.views import ActionResult
from browser_use.browser.profile import BrowserProfile, ProxySettings
from browser_use.browser.session import BrowserSession

# SDK for cloud file uploads
from browser_use_sdk import AsyncBrowserUse

# ============ CAPSOLVER CONFIG ============
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")

# ============ BLOCKED DOMAINS (Complex ATS - skip these) ============
BLOCKED_ATS_DOMAINS = [
    'myworkdayjobs.com',
    'myworkday.com',
    'wd1.myworkdayjobs.com',
    'wd3.myworkdayjobs.com',
    'wd5.myworkdayjobs.com',
    'icims.com',
    'taleo.net',
    'oraclecloud.com',
    'brassring.com',
    'ultipro.com',
    'successfactors.com',  # Can work but often problematic
]

# ============ SUCCESS KEYWORDS (flexible matching) ============
SUCCESS_KEYWORDS = [
    'application submitted',
    'application has been submitted',
    'application sent',
    'application has been sent',
    'your application has been sent',
    'thank you for applying',
    'thanks for applying',
    'successfully applied',
    'received your application',
    'application received',
    'application complete',
    'congratulations',
    'we have received your application',
    'your application was submitted',
    'application successfully submitted',
    'you have successfully applied',
    'success!',
    'applied successfully',
]

# Job unavailable indicators (fast-fail)
JOB_UNAVAILABLE_KEYWORDS = [
    'job has expired',
    'job is no longer available',
    'no longer accepting applications',
    'job not found',
    'this job post is no longer available',
    'position has been filled',
    'job listing has expired',
    'this position is closed',
]

# Create controller with CAPTCHA solving action
controller = Controller()

import random

# ============ HUMAN-LIKE BEHAVIOR HELPERS ============
async def human_delay(min_ms=100, max_ms=500):
    """Random delay to simulate human hesitation"""
    delay = random.randint(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)

async def human_type(page, selector: str, text: str):
    """Type text with human-like variable speed"""
    element = await page.query_selector(selector)
    if element:
        await element.click()
        await human_delay(50, 200)
        for char in text:
            await element.type(char, delay=random.randint(30, 120))
            if random.random() < 0.1:  # 10% chance of pause
                await human_delay(100, 300)


@controller.action('Humanize form interaction - dispatch events after clicking (use after radio/checkbox clicks)')
async def humanize_form_field(browser_session: BrowserSession, field_selector: str = "") -> ActionResult:
    """
    Call this after clicking a radio button, checkbox, or dropdown to ensure React/Vue registers the change.
    Also adds human-like delay.
    """
    try:
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        # Add human-like delay
        await human_delay(200, 600)

        # Dispatch events on recently clicked elements
        await page.evaluate("""() => {
            // Find all recently focused/clicked form elements
            const inputs = document.querySelectorAll('input:focus, input:checked, select, [aria-selected="true"]');
            inputs.forEach(el => {
                // Dispatch full set of events React/Vue expect
                el.dispatchEvent(new Event('focus', { bubbles: true }));
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            });

            // Also try to trigger form validation
            const form = document.querySelector('form');
            if (form) {
                form.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }""")

        return ActionResult(extracted_content="Form events dispatched. Form should now recognize the selection.")

    except Exception as e:
        return ActionResult(extracted_content=f"Humanize error: {str(e)}")


# ============ FORM INJECTION SYSTEM ============
# Load the form filler JS
FORM_FILLER_JS = Path("/root/job_bot/skills/form_filler.js").read_text()

# Import DOM parser
import sys
sys.path.insert(0, "/root/job_bot")
from skills.dom_parser import clean_html_for_llm, generate_field_mapping, extract_form_fields, match_field_heuristically


@controller.action('Inject form data - fill ALL fields at once using JS injection (much faster than clicking each field)')
async def inject_form_data(browser_session: BrowserSession) -> ActionResult:
    """
    SPEED OPTIMIZATION: Fill entire form in one step instead of clicking each field.

    1. Extracts form HTML
    2. Maps fields to user profile using heuristics (free) then LLM if needed
    3. Injects all values via React-aware JavaScript
    4. Returns list of filled fields and any that need manual handling (files)
    """
    try:
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        # Get form HTML
        form_html = await page.evaluate("""() => {
            const form = document.querySelector('form');
            if (form) return form.outerHTML;
            // No form tag - get body content with inputs
            return document.body.innerHTML;
        }""")

        if not form_html or len(form_html) < 50:
            return ActionResult(extracted_content="No form found on page")

        # User profile for mapping
        user_profile = {
            'first_name': APPLICANT['name'].split()[0],
            'last_name': APPLICANT['name'].split()[-1] if len(APPLICANT['name'].split()) > 1 else '',
            'email': APPLICANT['email'],
            'phone': APPLICANT['phone'],
            'city': APPLICANT.get('city', 'Anaheim'),
            'state': APPLICANT.get('state', 'CA'),
            'zip': APPLICANT.get('zip_code', '92805'),
            'address': APPLICANT.get('street_address', ''),
            'linkedin': 'linkedin.com/in/brandonruiz',
        }

        # Generate field mapping (heuristics first, then LLM if needed)
        def llm_callback(unmatched_fields, profile):
            # Use Gemini Flash for quick field mapping
            if not GEMINI_AVAILABLE:
                return {}
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                fields_desc = "\n".join([f"- {f.get('name') or f.get('id') or f.get('placeholder')}: {f.get('type')}" for f in unmatched_fields])
                prompt = f"""Map these form fields to user profile values. Return JSON only.

Fields:
{fields_desc}

Profile: {json.dumps(profile)}

Return format: {{"selector": "value", ...}}
Use CSS selectors like [name="fieldname"] or #id"""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={'temperature': 0.1}
                )
                # Parse JSON from response
                text = response.text or ""
                match = re.search(r'\{[^}]+\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except Exception as e:
                print(f"  [Form Injection] LLM mapping error: {e}")
            return {}

        field_mapping = generate_field_mapping(form_html, user_profile, llm_callback)

        if not field_mapping:
            return ActionResult(extracted_content="Could not generate field mapping. Use manual form filling.")

        # Inject the form filler function and execute it
        injection_script = f"""
        {FORM_FILLER_JS}

        return await injectFormData({json.dumps(field_mapping)});
        """

        result = await page.evaluate(injection_script)

        filled = result.get('filled', [])
        failed = result.get('failed', [])
        files = result.get('files', [])

        summary = f"Filled {len(filled)} fields"
        if failed:
            summary += f", {len(failed)} not found"
        if files:
            summary += f", {len(files)} file uploads needed"

        print(f"  [Form Injection] {summary}")

        return ActionResult(
            extracted_content=f"FORM INJECTED: {summary}. Fields filled: {', '.join(filled[:5])}{'...' if len(filled) > 5 else ''}"
        )

    except Exception as e:
        return ActionResult(extracted_content=f"Form injection error: {str(e)}")


@controller.action('Solve CAPTCHA (Cloudflare Turnstile, reCAPTCHA, or hCaptcha)')
async def solve_captcha(browser_session: BrowserSession) -> ActionResult:
    """Detect and solve CAPTCHAs using CapSolver API - supports Turnstile, reCAPTCHA, and hCaptcha"""
    if not CAPSOLVER_API_KEY:
        return ActionResult(extracted_content="No CAPSOLVER_API_KEY configured")

    try:
        # Get the current page from browser session
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        # Get URL via JavaScript
        page_url = await page.evaluate("() => window.location.href")

        async with aiohttp.ClientSession() as http_client:
            # ============ 1. Detect CAPTCHA Type ============
            captcha_type = None
            site_key = None

            # Check for hCaptcha FIRST (commonly missed)
            hcaptcha_elements = await page.get_elements_by_css_selector('.h-captcha, iframe[src*="hcaptcha"], [data-hcaptcha-widget-id]')
            if hcaptcha_elements:
                print(f"  [CapSolver] hCaptcha detected on {page_url[:50]}...")
                site_key = await page.evaluate("""
                    () => {
                        const el = document.querySelector('.h-captcha, [data-sitekey]');
                        if (el) return el.getAttribute('data-sitekey');
                        // Try iframe src
                        const frame = document.querySelector('iframe[src*="hcaptcha"]');
                        if (frame) {
                            const match = frame.src.match(/sitekey=([^&]+)/);
                            return match ? match[1] : null;
                        }
                        return null;
                    }
                """)
                if site_key:
                    captcha_type = "HCaptchaTaskProxyLess"

            # Check for Cloudflare Turnstile
            if not captcha_type:
                turnstile_elements = await page.get_elements_by_css_selector('iframe[src*="challenges.cloudflare.com"], [data-turnstile-sitekey], .cf-turnstile')
                if turnstile_elements:
                    print(f"  [CapSolver] Cloudflare Turnstile detected on {page_url[:50]}...")
                    site_key = await page.evaluate("""
                        () => {
                            const el = document.querySelector('[data-turnstile-sitekey], .cf-turnstile');
                            if (el) return el.getAttribute('data-turnstile-sitekey') || el.getAttribute('data-sitekey');
                            const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
                            if (iframe) {
                                const match = iframe.src.match(/[?&]k=([^&]+)/);
                                return match ? match[1] : null;
                            }
                            return null;
                        }
                    """)
                    if site_key:
                        captcha_type = "AntiTurnstileTaskProxyLess"

            # Check for reCAPTCHA v2
            if not captcha_type:
                recaptcha_elements = await page.get_elements_by_css_selector('.g-recaptcha, [data-sitekey], iframe[src*="recaptcha"]')
                if recaptcha_elements:
                    print(f"  [CapSolver] reCAPTCHA detected on {page_url[:50]}...")
                    site_key = await page.evaluate("""
                        () => {
                            const el = document.querySelector('.g-recaptcha, [data-sitekey]');
                            if (el) return el.getAttribute('data-sitekey');
                            const iframe = document.querySelector('iframe[src*="recaptcha"]');
                            if (iframe) {
                                const match = iframe.src.match(/[?&]k=([^&]+)/);
                                return match ? match[1] : null;
                            }
                            return null;
                        }
                    """)
                    if site_key:
                        captcha_type = "ReCaptchaV2TaskProxyLess"

            if not captcha_type or not site_key:
                return ActionResult(extracted_content="No supported CAPTCHA found or sitekey missing")

            # ============ 2. Create Task (async) ============
            print(f"  [CapSolver] Creating task: {captcha_type} with key {site_key[:20]}...")

            payload = {
                "clientKey": CAPSOLVER_API_KEY,
                "task": {
                    "type": captcha_type,
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
            }

            async with http_client.post("https://api.capsolver.com/createTask", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()
                task_id = data.get("taskId")
                if not task_id:
                    return ActionResult(extracted_content=f"Task creation failed: {data.get('errorDescription', data)}")

            print(f"  [CapSolver] Task created: {task_id}")

            # ============ 3. Poll for Result (async) ============
            solution = None
            for i in range(24):  # 120 seconds max
                await asyncio.sleep(5)
                async with http_client.post("https://api.capsolver.com/getTaskResult",
                                           json={"clientKey": CAPSOLVER_API_KEY, "taskId": task_id},
                                           timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    result = await resp.json()

                    if result.get("status") == "ready":
                        solution = result.get("solution", {}).get("gRecaptchaResponse") or \
                                   result.get("solution", {}).get("token")
                        break
                    elif result.get("status") == "failed":
                        return ActionResult(extracted_content=f"Solving failed: {result.get('errorDescription')}")

                    print(f"  [CapSolver] Waiting... ({i*5}s)")

            if not solution:
                return ActionResult(extracted_content="Timeout waiting for CAPTCHA solution")

            print(f"  [CapSolver] Got solution! Injecting...")

            # ============ 4. Inject Solution ============
            escaped_solution = solution.replace("'", "\\'").replace("\n", "\\n")

            if captcha_type == "HCaptchaTaskProxyLess":
                await page.evaluate(f"""
                    () => {{
                        const token = '{escaped_solution}';
                        // Update hidden textareas
                        const fields = document.querySelectorAll('[name="h-captcha-response"], [name="g-recaptcha-response"]');
                        fields.forEach(el => {{
                            el.value = token;
                            // Dispatch events for React/Vue forms
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }});
                        // Try callback
                        if (window.hcaptcha) {{
                            const widget = document.querySelector('.h-captcha');
                            if (widget && widget.getAttribute('data-callback')) {{
                                const cbName = widget.getAttribute('data-callback');
                                if (typeof window[cbName] === 'function') window[cbName](token);
                            }}
                        }}
                        // Also try global hcaptcha callback
                        if (typeof window.onHCaptchaSuccess === 'function') {{
                            window.onHCaptchaSuccess(token);
                        }}
                    }}
                """)
                print(f"  [CapSolver] hCaptcha solved successfully!")
                return ActionResult(extracted_content="CAPTCHA solved - hCaptcha token injected. Click verify/submit.")

            elif captcha_type == "AntiTurnstileTaskProxyLess":
                await page.evaluate(f"""
                    () => {{
                        const token = '{escaped_solution}';
                        const responseField = document.querySelector('[name="cf-turnstile-response"]') ||
                                             document.querySelector('input[name*="turnstile"]');
                        if (responseField) {{
                            responseField.value = token;
                            // Dispatch events for React/Vue forms
                            responseField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            responseField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        // Try Turnstile callback
                        if (window.turnstile && window.turnstile.getResponse) {{
                            // Turnstile widget exists
                        }}
                        // Check for custom callback
                        const widget = document.querySelector('.cf-turnstile');
                        if (widget && widget.getAttribute('data-callback')) {{
                            const cbName = widget.getAttribute('data-callback');
                            if (typeof window[cbName] === 'function') window[cbName](token);
                        }}
                    }}
                """)
                print(f"  [CapSolver] Turnstile solved successfully!")
                return ActionResult(extracted_content="CAPTCHA solved - Turnstile bypassed. Refresh or click verify.")

            elif captcha_type == "ReCaptchaV2TaskProxyLess":
                await page.evaluate(f"""
                    () => {{
                        const token = '{escaped_solution}';
                        const responseFields = document.querySelectorAll('[name="g-recaptcha-response"], #g-recaptcha-response, textarea[id*="recaptcha-response"]');
                        responseFields.forEach(field => {{
                            field.value = token;
                            field.innerHTML = token;
                            // Dispatch events for React/Vue forms
                            field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }});
                        // Try callbacks
                        if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {{
                            Object.keys(___grecaptcha_cfg.clients).forEach(key => {{
                                const client = ___grecaptcha_cfg.clients[key];
                                if (client) {{
                                    ['callback', 'O', 'response'].forEach(prop => {{
                                        if (client[prop] && typeof client[prop] === 'function') {{
                                            try {{ client[prop](token); }} catch(e) {{}}
                                        }}
                                    }});
                                    // Also check nested objects
                                    Object.keys(client).forEach(subKey => {{
                                        const sub = client[subKey];
                                        if (sub && typeof sub === 'object') {{
                                            ['callback', 'O'].forEach(prop => {{
                                                if (sub[prop] && typeof sub[prop] === 'function') {{
                                                    try {{ sub[prop](token); }} catch(e) {{}}
                                                }}
                                            }});
                                        }}
                                    }});
                                }}
                            }});
                        }}
                        // Also try grecaptcha global callback
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.callback) {{
                            try {{ grecaptcha.callback(token); }} catch(e) {{}}
                        }}
                        // IMPROVEMENT: Click the checkbox to trigger visual update
                        const checkbox = document.querySelector('.recaptcha-checkbox-border, .recaptcha-checkbox, [role="checkbox"]');
                        if (checkbox) checkbox.click();
                    }}
                """)
                print(f"  [CapSolver] reCAPTCHA solved successfully!")
                # Also try clicking the checkbox via Playwright for extra reliability
                try:
                    checkbox = await page.query_selector('.recaptcha-checkbox-border, .recaptcha-checkbox')
                    if checkbox:
                        await checkbox.click()
                        print(f"  [CapSolver] Clicked reCAPTCHA checkbox")
                except:
                    pass
                return ActionResult(extracted_content="CAPTCHA solved - reCAPTCHA token injected and checkbox clicked. Submit button should now be enabled.")

            return ActionResult(extracted_content=f"Solution injected for {captcha_type}")

    except Exception as e:
        return ActionResult(extracted_content=f"CAPTCHA solving error: {str(e)}")


# ============ URL GUARD - Stop if leaving Indeed ============
ALLOWED_DOMAINS = ['indeed.com', 'indeed.co', 'indeed.ca', 'indeed.co.uk']
EXTERNAL_ATS_INDICATORS = ['greenhouse.io', 'lever.co', 'workday', 'icims.com', 'taleo', 'brassring', 'ultipro', 'successfactors', 'oraclecloud']


@controller.action('Check if still on Indeed Easy Apply (IMPORTANT: Call this before clicking Apply)')
async def verify_indeed_easy_apply(browser_session: BrowserSession) -> ActionResult:
    """
    CRITICAL: Verifies we are still on Indeed and this is a true Easy Apply job.
    If redirected to external site, returns ABORT instruction.
    """
    try:
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        current_url = await page.evaluate("() => window.location.href")
        url_lower = current_url.lower()

        # Check if we left Indeed
        is_on_indeed = any(domain in url_lower for domain in ALLOWED_DOMAINS)

        if not is_on_indeed:
            # Check which external ATS we landed on
            for ats in EXTERNAL_ATS_INDICATORS:
                if ats in url_lower:
                    return ActionResult(
                        extracted_content=f"ABORT: Redirected to external ATS ({ats}). Say 'EXTERNAL_SITE' and stop."
                    )
            return ActionResult(
                extracted_content=f"ABORT: Left Indeed domain. Current URL: {current_url[:80]}. Say 'EXTERNAL_SITE' and stop."
            )

        # Check if the button says "Apply on company site" (not true Easy Apply)
        is_external_button = await page.evaluate("""() => {
            const buttons = document.querySelectorAll('button, a');
            for (const btn of buttons) {
                const text = btn.innerText.toLowerCase();
                if (text.includes('apply on company site') || text.includes('apply externally')) {
                    return true;
                }
            }
            return false;
        }""")

        if is_external_button:
            return ActionResult(
                extracted_content="WARNING: This job requires 'Apply on company site'. NOT Easy Apply. Consider skipping."
            )

        return ActionResult(extracted_content="CONFIRMED: On Indeed, appears to be Easy Apply. Proceed with application.")

    except Exception as e:
        return ActionResult(extracted_content=f"URL check error: {str(e)}")


@controller.action('Check for form validation errors before clicking Continue/Submit')
async def check_validation_errors(browser_session: BrowserSession) -> ActionResult:
    """
    CRITICAL: Call this BEFORE clicking Continue/Submit/Apply.
    Scans for validation errors, red text, empty required fields.
    Also checks inside iframes (Indeed Easy Apply uses iframes).
    """
    try:
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        errors = await page.evaluate("""() => {
            function getErrors(doc) {
                let foundErrors = [];

                // 1. Check for HTML5 validation errors
                const invalidInputs = doc.querySelectorAll('input:invalid, select:invalid, textarea:invalid');
                if (invalidInputs.length > 0) {
                    foundErrors.push(`${invalidInputs.length} invalid HTML inputs`);
                }

                // 2. Check for ARIA invalid attributes (React apps)
                const ariaInvalid = doc.querySelectorAll('[aria-invalid="true"]');
                ariaInvalid.forEach(f => {
                    const label = f.getAttribute('aria-label') || f.placeholder || f.name || 'field';
                    foundErrors.push(`Invalid: ${label}`);
                });

                // 3. Check for error classes (visible only)
                const errorElements = doc.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert-danger"], [class*="invalid"]');
                errorElements.forEach(el => {
                    const text = el.innerText.trim();
                    if (text.length > 2 && text.length < 150 && el.offsetParent !== null) {
                        foundErrors.push(`Error: ${text.substring(0, 60)}`);
                    }
                });

                // 4. Check for red "Required" text
                const spans = doc.querySelectorAll('span, div, p');
                for (let el of spans) {
                    try {
                        const style = window.getComputedStyle(el);
                        const color = style.color;
                        if ((color.includes('rgb(2') || color.includes('red')) &&
                            (el.innerText.includes('Required') || el.innerText.includes('fix the error'))) {
                            foundErrors.push(`Required warning: ${el.innerText.substring(0, 50)}`);
                        }
                    } catch(e) {}
                }

                // 5. Check for empty required fields
                const requiredFields = doc.querySelectorAll('[required], [aria-required="true"]');
                requiredFields.forEach(f => {
                    if (!f.value || f.value.trim() === '') {
                        const label = f.getAttribute('aria-label') || f.placeholder || f.name || 'field';
                        foundErrors.push(`Empty required: ${label}`);
                    }
                });

                return foundErrors;
            }

            // Check main document
            let report = getErrors(document);

            // Check iframes (Indeed Easy Apply uses iframes)
            const frames = document.querySelectorAll('iframe');
            frames.forEach(frame => {
                try {
                    const frameDoc = frame.contentDocument || frame.contentWindow.document;
                    if (frameDoc) {
                        const frameErrors = getErrors(frameDoc);
                        frameErrors.forEach(e => report.push(`(iframe) ${e}`));
                    }
                } catch (e) {
                    // Cross-origin restriction - can't access
                }
            });

            return report;
        }""")

        if errors and len(errors) > 0:
            # Filter out empty/useless error messages
            meaningful_errors = [e for e in errors if e and len(e.strip()) > 3 and e.strip() not in [';', '[]', 'Error:', 'Invalid:']]
            if meaningful_errors:
                error_list = "; ".join(meaningful_errors[:5])  # First 5 meaningful errors
                return ActionResult(
                    extracted_content=f"VALIDATION ERRORS FOUND: {error_list}. FIX THESE before clicking Continue/Submit."
                )

        return ActionResult(extracted_content="No validation errors detected. Safe to proceed.")

    except Exception as e:
        return ActionResult(extracted_content=f"Validation check error: {str(e)}")


# ============ GEMINI TIERED RESCUE SYSTEM ============
# Based on Gemini 3 Pro deep analysis recommendations:
# - Tier 1: Flash with NO thinking for quick tactical fixes
# - Tier 2: Pro with 4K thinking for complex problems
# - WAF detection: "Something went wrong" on Indeed = bot block, not logic error
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Set in .env file

# Track rescue attempts per session to implement tiered escalation
_rescue_attempt_count = {}


@controller.action('Ask Gemini for help when stuck (RESCUE MODE - use when confused or stuck in a loop)')
async def ask_gemini_for_help(browser_session: BrowserSession, problem_description: str = "I am stuck") -> ActionResult:
    """
    TIERED RESCUE SYSTEM:
    - Tier 1 (first call): Gemini Flash, NO thinking - fast tactical fix
    - Tier 2 (repeat calls): Gemini 3 Pro, 4K thinking - deep analysis
    - WAF Detection: Identifies bot blocks vs logic errors
    """
    global _rescue_attempt_count

    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return ActionResult(extracted_content="Gemini not available - continue with best guess")

    try:
        page = await browser_session.get_current_page()
        if not page:
            return ActionResult(extracted_content="Could not get current page")

        # Get current URL
        current_url = await page.evaluate("() => window.location.href")

        # Track attempts for this URL pattern (strip query params for grouping)
        url_key = current_url.split('?')[0][:50]
        _rescue_attempt_count[url_key] = _rescue_attempt_count.get(url_key, 0) + 1
        attempt = _rescue_attempt_count[url_key]

        # Get visible text from the page
        visible_text = await page.evaluate("""() => {
            const body = document.body.innerText;
            return body.substring(0, 2000);
        }""")

        # Get error messages
        error_messages = await page.evaluate("""() => {
            const errors = [];
            const errorElements = document.querySelectorAll('.error, .invalid, [class*="error"], [aria-invalid="true"]');
            errorElements.forEach(el => {
                const text = el.innerText.trim();
                if (text && text.length < 200 && el.offsetParent !== null) {
                    errors.push(text);
                }
            });
            return errors.slice(0, 5).join(' | ');
        }""")

        # Get interactive elements
        buttons = await page.evaluate("""() => {
            const btns = document.querySelectorAll('button, input[type="submit"], a[role="button"]');
            const visible = [];
            btns.forEach((b, i) => {
                if (b.offsetParent !== null && i < 10) {
                    visible.push(b.innerText.trim().substring(0, 30));
                }
            });
            return visible.join(', ');
        }""")

        # ============ WAF/BOT DETECTION ============
        # "Something went wrong" on Indeed is usually a WAF block, not logic error
        error_lower = (error_messages or '').lower()
        problem_lower = problem_description.lower()
        is_waf_block = (
            ('something went wrong' in error_lower or 'something went wrong' in problem_lower) and
            'indeed' in current_url.lower() and
            attempt >= 2  # Only flag as WAF after multiple attempts
        )

        if is_waf_block:
            print(f"  [GEMINI RESCUE] WAF/Bot detection suspected (attempt {attempt})")
            return ActionResult(
                extracted_content="GEMINI ADVICE: STOP: WAF_DETECTED - Indeed bot protection triggered. Save and try another job."
            )

        # Build context
        context = f"""URL: {current_url}
Problem: {problem_description}
Errors: {error_messages or 'None'}
Buttons: {buttons or 'None'}
Page: {visible_text[:1000]}"""

        client = genai.Client(api_key=GEMINI_API_KEY)

        # ============ TIER 1: Fast Tactical (Flash, no thinking) ============
        if attempt == 1:
            print(f"  [GEMINI RESCUE] Tier 1: Flash (no thinking)")
            prompt = f"""UI navigator for job application bot. Quick fix needed.

{context}

Output ONE action: CLICK: [button] / TYPE: [field]=[value] / SCROLL: [up/down] / WAIT: [reason] / STOP: [reason]"""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={'temperature': 0.2}  # No thinking config = no thinking
            )

        # ============ TIER 2: Deep Analysis (Pro, 4K thinking) ============
        else:
            print(f"  [GEMINI RESCUE] Tier 2: Pro with thinking (attempt {attempt})")
            prompt = f"""You are debugging a stuck job application bot. Tier 1 fast fix failed.

{context}

DEEP ANALYZE: Why is the form not progressing? Consider:
- Hidden validation errors
- Form state not updating (React hydration)
- Modal/overlay blocking interaction
- Wrong element being clicked

Output ONE action: CLICK: [button] / TYPE: [field]=[value] / SCROLL: [up/down] / WAIT: [reason] / STOP: [reason]
Only STOP if truly unrecoverable."""

            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'thinking_config': {'thinking_budget': 4096}  # Capped at 4K per Gemini's recommendation
                }
            )

        advice = response.text.strip() if response.text else "WAIT: No response from Gemini"
        print(f"  [GEMINI RESCUE] Advice: {advice}")

        return ActionResult(extracted_content=f"GEMINI ADVICE: {advice}")

    except Exception as e:
        error_msg = str(e)
        print(f"  [GEMINI RESCUE] ERROR: {error_msg}")
        if "PERMISSION_DENIED" in error_msg or "leaked" in error_msg.lower():
            return ActionResult(extracted_content="GEMINI ERROR: API key invalid or revoked. Please update GEMINI_API_KEY in .env file.")
        return ActionResult(extracted_content=f"Gemini error: {error_msg[:150]}")


# Email verification code reader
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "brandonlruiz98@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

@controller.action('Get email verification code from inbox (for account verification)')
async def get_verification_code(sender_hint: str = "") -> ActionResult:
    """Check Gmail inbox for recent verification codes"""
    import imaplib
    import email
    from email.header import decode_header

    if not GMAIL_APP_PASSWORD:
        return ActionResult(extracted_content="No GMAIL_APP_PASSWORD configured")

    try:
        print(f"  [Email] Checking {GMAIL_EMAIL} for verification code...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("INBOX")

        _, messages = mail.search(None, "UNSEEN")
        if not messages[0]:
            _, messages = mail.search(None, "ALL")

        email_ids = messages[0].split()[-10:] if messages[0] else []

        for email_id in reversed(email_ids):
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors='ignore')

                    sender = msg.get("From", "").lower()
                    if sender_hint and sender_hint.lower() not in sender:
                        continue

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')

                    codes = re.findall(r'\b(\d{4,8})\b', body)
                    if codes:
                        code = codes[0]
                        print(f"  [Email] Found code: {code} from {sender[:30]}")
                        mail.logout()
                        return ActionResult(extracted_content=f"Verification code: {code}")

        mail.logout()
        return ActionResult(extracted_content="No verification code found. Wait and try again.")

    except Exception as e:
        return ActionResult(extracted_content=f"Email error: {str(e)}")


# ============ CONFIG ============
QUEUE_DIR = Path("/root/job_bot/queue")
OUTPUT_DIR = Path("/root/output")
COOKIES_FILE = Path("/root/job_bot/agent/cookies.json")
STORAGE_STATE_FILE = Path("/root/job_bot/agent/storage_state.json")

# Applicant info
APPLICANT = {
    "name": "Brandon Ruiz",
    "email": "brandonruizmarketing@gmail.com",
    "email_external": "brandonlruiz98@gmail.com",
    "password_external": os.getenv("INDEED_PASSWORD_EXTERNAL", ""),
    "phone": "775-530-8234",
    "location": "Anaheim, CA",
    "street_address": "1602 Juneau Ave",
    "city": "Anaheim",
    "state": "CA",
    "zip_code": "92805",
    "current_job_title": "IT Support Specialist",
    "current_company": "Geek Squad",
    "years_experience": "5",
    "previous_job_title": "IT Support Specialist",
    "previous_company": "Fusion Contact Centers",
}

DELAY_BETWEEN_JOBS = 10
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/incoming-job')


def is_valid_job(job: dict) -> tuple[bool, str]:
    """Check if job data is valid (not NaN, has required fields)"""
    company = str(job.get('company', '')).strip().lower()
    title = str(job.get('title', '')).strip().lower()
    url = str(job.get('url', '')).strip()

    # Check for NaN or empty values
    if company in ['nan', 'none', ''] or not company:
        return False, "invalid_company"
    if title in ['nan', 'none', ''] or not title:
        return False, "invalid_title"
    if not url or 'indeed.com' not in url.lower():
        return False, "invalid_url"

    return True, "valid"


def is_blocked_ats(url: str) -> tuple[bool, str]:
    """Check if URL redirects to a blocked ATS domain"""
    url_lower = url.lower()
    for domain in BLOCKED_ATS_DOMAINS:
        if domain in url_lower:
            return True, domain
    return False, ""


def load_cookies_as_storage_state() -> str:
    """Convert cookies.json to Playwright storage state file"""
    if not COOKIES_FILE.exists():
        return None

    raw_cookies = json.loads(COOKIES_FILE.read_text())
    pw_cookies = []
    for cookie in raw_cookies:
        pw_cookie = {
            "name": cookie.get("name"),
            "value": cookie.get("value"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
        }
        if cookie.get("expirationDate"):
            pw_cookie["expires"] = cookie.get("expirationDate")
        # Normalize sameSite value - Playwright only accepts Strict|Lax|None
        same_site = cookie.get("sameSite", "Lax")
        same_site_lower = str(same_site).lower()
        if same_site_lower in ["no_restriction", "none"]:
            same_site = "None"
        elif same_site_lower in ["strict"]:
            same_site = "Strict"
        elif same_site_lower in ["lax", "unspecified", ""]:
            same_site = "Lax"
        else:
            same_site = "Lax"  # Default fallback
        pw_cookie["sameSite"] = same_site
        pw_cookies.append(pw_cookie)

    storage_state = {"cookies": pw_cookies, "origins": []}
    STORAGE_STATE_FILE.write_text(json.dumps(storage_state, indent=2))
    return str(STORAGE_STATE_FILE)


def load_queue(name: str) -> list:
    path = QUEUE_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_queue(name: str, data: list):
    path = QUEUE_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))


async def upload_file_to_cloud_session(session_id: str, file_path: str) -> str | None:
    """Upload a local file to Browser-Use Cloud session"""
    api_key = os.getenv("BROWSER_USE_API_KEY")
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        print(f"  Upload skipped: {file_path} does not exist")
        return None

    file_size = file_path_obj.stat().st_size
    file_name = file_path_obj.name

    try:
        client = AsyncBrowserUse(api_key=api_key)
        presigned = await client.files.browser_session_upload_file_presigned_url(
            session_id=session_id,
            file_name=file_name,
            content_type="application/pdf",
            size_bytes=file_size,
        )

        form_data = aiohttp.FormData()
        for key, value in presigned.fields.items():
            form_data.add_field(key, value)
        form_data.add_field('file', open(file_path, 'rb'), filename=file_name, content_type='application/pdf')

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(presigned.url, data=form_data) as resp:
                if resp.status in [200, 201, 204]:
                    print(f"  Uploaded {file_name} to cloud session ({file_size} bytes)")
                    return presigned.file_name
                else:
                    body = await resp.text()
                    print(f"  Upload failed: HTTP {resp.status} - {body[:200]}")
                    return None

    except Exception as e:
        print(f"  Cloud upload error: {e}")
        return None


async def send_to_factory_async(job: dict) -> dict | None:
    """Send job to n8n resume factory (async version)"""
    payload = {
        'title': str(job.get('title', 'Unknown')),
        'company': str(job.get('company', 'Unknown')),
        'description': str(job.get('description', '')),
        'url': str(job.get('url', '')),
        'location': str(job.get('location', '')),
    }

    try:
        print(f"  Sending to n8n factory for resume generation...")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                if response.status in [200, 202]:
                    result = await response.json()
                    print(f"  Factory success: app #{result.get('application_number')}")
                    return result
                else:
                    print(f"  Factory error: HTTP {response.status}")
                    return None
    except asyncio.TimeoutError:
        print(f"  Factory timeout (180s)")
        return None
    except Exception as e:
        print(f"  Factory connection failed: {e}")
        return None


def get_resume_path(job: dict) -> str | None:
    """Find resume PDF for this job"""
    company = str(job.get('company', '')).replace(' ', '_').replace('/', '_')[:30]
    app_num = job.get('application_number', '')

    patterns = [
        f"{company}_{app_num}_Resume.pdf",
        f"{company}_*_Resume.pdf",
        f"*_{app_num}_Resume.pdf",
    ]

    for pattern in patterns:
        matches = list(OUTPUT_DIR.glob(pattern))
        if matches:
            return str(sorted(matches, key=lambda x: x.stat().st_mtime, reverse=True)[0])
    return None


def is_indeed_url(url: str) -> bool:
    return "indeed.com" in url.lower()


def check_success(content: str) -> bool:
    """Check if content indicates successful application (flexible matching)"""
    content_lower = content.lower()
    for keyword in SUCCESS_KEYWORDS:
        if keyword in content_lower:
            return True
    return False


def build_task(job: dict, resume_path: str | None) -> str:
    """Build task prompt for Browser-Use agent"""

    resume_instruction = ""
    if resume_path:
        resume_instruction = f"""
RESUME UPLOAD (CRITICAL):
Do NOT use any pre-filled or saved resume from the Indeed account.
You MUST upload this specific custom resume file: {resume_path}
- If a resume is already attached/pre-filled, click "Replace resume" or "Remove" to delete it first
- Then click "Upload resume" or "Upload new resume" and select: {resume_path}
- If there is also a cover letter upload option, skip it
- Make sure the uploaded filename shows the custom file, NOT a default Indeed resume
"""

    job_url = job.get('url', '')
    is_external = 'indeed.com' not in job_url.lower()
    email_to_use = APPLICANT.get('email_external', APPLICANT['email']) if is_external else APPLICANT['email']

    # Common success criteria (FLEXIBLE)
    success_criteria = """
SUCCESS CRITERIA (FLEXIBLE - IMPORTANT):
You are done when you see ANY of these confirmations:
- "Application submitted" or "Application has been submitted"
- "Application sent" or "Application has been sent"
- "Thank you for applying" or "Thanks for applying"
- "Successfully applied" or "Application complete"
- "We received your application" or "Application received"
- Any green checkmark with a thank you message
- Any confirmation page after clicking final Submit/Apply

Do NOT require exact text matching. If the page clearly shows the application went through, report SUCCESS.
"""

    if is_external:
        task = f"""
Go to this job posting and complete the application: {job_url}

{success_criteria}

APPLICANT INFO - Use these details for ALL form fields:
- Full Name: {APPLICANT['name']}
- Email: {email_to_use}
- Password: {APPLICANT.get('password_external', '')}
- Phone: {APPLICANT['phone']}
- City/Location: {APPLICANT['location']}
- Street Address: {APPLICANT.get('street_address', '1602 Juneau Ave')}
- City: {APPLICANT.get('city', 'Anaheim')}
- State: {APPLICANT.get('state', 'CA')}
- Zip Code: {APPLICANT.get('zip_code', '92805')}

WORK HISTORY - Use for experience questions:
- Current Job Title: {APPLICANT.get('current_job_title', 'IT Support Technician')}
- Current Company: {APPLICANT.get('current_company', 'Geek Squad')}
- Years of Experience: {APPLICANT.get('years_experience', '5')}
- Previous Job Title: {APPLICANT.get('previous_job_title', 'IT Support Specialist')}
- Previous Company: {APPLICANT.get('previous_company', 'Fusion Contact Centers')}

IMPORTANT RULES:
- If asked to create an account or sign in, use the email and password above
- If a dialog box or popup appears, close it immediately
- Complete ALL pages of the application form
- Answer Yes/No qualification questions with "Yes" unless clearly unqualified
- For work authorization: "Yes, authorized to work in the US"
- For sponsorship: "No, do not require sponsorship"

CAPTCHA HANDLING:
- If you encounter ANY CAPTCHA (reCAPTCHA, hCaptcha, Cloudflare), use the solve_captcha action
- After calling solve_captcha, wait then click Submit/Continue
- Do NOT give up on CAPTCHAs - always try solve_captcha first

RESCUE MODE (IMPORTANT - USE WHEN STUCK):
- If you are stuck, confused, or have tried the same action 2+ times without progress, use ask_gemini_for_help
- Call it with a description of your problem, e.g., ask_gemini_for_help("Form keeps showing error")
- Gemini will analyze the page and give you ONE specific action to take
- Follow Gemini's advice exactly

EMAIL VERIFICATION:
- If asked for a verification code, use the get_verification_code action
- Enter the code and continue

{resume_instruction}

STEPS:
1. Go to the job URL and click Apply/Apply Now
2. If given option, choose "Apply as Guest" or "Continue without account"
3. Fill in all required fields using the applicant info above
4. Upload the resume when prompted
5. Complete all pages, clicking Continue/Next after each
6. On voluntary self-identification pages, select "I do not want to answer"
7. Review and submit the application
8. Report SUCCESS if you see any confirmation

When done, say "SUCCESS" if you see any confirmation that the application was submitted/sent/received.
If the job is unavailable or expired, say "JOB_UNAVAILABLE".
Otherwise explain what went wrong.
"""
    else:
        task = f"""
Go to this job posting and apply using Easy Apply: {job_url}

{success_criteria}

=== STRICT OPERATIONAL PROTOCOL (MANDATORY) ===

**1. FORM FILLING STRATEGY - BATCH FIRST (High Priority)**
- Your **FIRST** move when seeing ANY form inputs must be `inject_form_data`
- Do NOT click and type into individual fields unless injection fails completely
- If you must fill manually, use `humanize_form_field` immediately after to trigger React events

**2. VALIDATION GATE - PRE-FLIGHT CHECK (MANDATORY)**
- You are FORBIDDEN from clicking "Continue", "Next", "Submit", or "Apply" without first running `check_validation_errors`
- If errors found, FIX the specific fields listed before attempting to proceed again

**3. THE 3-STRIKE RULE**
- If you attempt the exact same action 3 times and it fails or the page does not change, you MUST call `ask_gemini_for_help`

**Execution Flow:**
1. Detect Form -> 2. `inject_form_data` -> 3. `check_validation_errors` -> 4. If Clean: Click Next. If Dirty: Fix -> Go to 3.

=== END PROTOCOL ===

CRITICAL URL CHECK:
- After clicking Apply, call verify_indeed_easy_apply to check you're still on Indeed
- If it says "ABORT" or "EXTERNAL_SITE", IMMEDIATELY stop and say "EXTERNAL_SITE"
- Do NOT continue if the URL leaves indeed.com

IMPORTANT RULES:
- ONLY proceed if you see "Easy Apply" or a simple "Apply" button on Indeed
- If button says "Apply on company site" - STOP and say "EXTERNAL_SITE"
- If you're on Indeed and asked to login - STOP and say "NEEDS_LOGIN"
- If a dialog box or popup appears, close it immediately
- Complete ALL pages of the application form
- Answer all Yes/No qualification questions with "Yes"

HUMAN-LIKE PACING:
- Wait 1-2 seconds after page loads before clicking
- After clicking radio buttons or checkboxes, call humanize_form_field to ensure React registers the change
- If you see "Something went wrong" repeatedly, try waiting longer between actions

CAPTCHA HANDLING:
- If you see "Additional Verification Required" or any CAPTCHA, use the solve_captcha action
- The solve_captcha action supports Cloudflare Turnstile, reCAPTCHA, AND hCaptcha
- After calling solve_captcha, wait then refresh or click verify/continue
- Do NOT give up on CAPTCHAs - always try solve_captcha first

RESCUE MODE (IMPORTANT - USE WHEN STUCK):
- If you are stuck, confused, or have tried the same action 2+ times without progress, use ask_gemini_for_help
- Call it with a description of your problem, e.g., ask_gemini_for_help("Cannot find the Submit button")
- Gemini will analyze the page and give you ONE specific action to take
- Follow Gemini's advice exactly

APPLICANT INFO (for Indeed):
- Full Name: {APPLICANT['name']}
- Email: {APPLICANT['email']}
- Phone: {APPLICANT['phone']}
- City/Location: {APPLICANT['location']}
- Street Address: {APPLICANT.get('street_address', '')}
- City: {APPLICANT.get('city', 'Anaheim')}
- State: {APPLICANT.get('state', 'CA')}
- Zip Code: {APPLICANT.get('zip_code', '92805')}

WORK HISTORY (for "relevant experience" questions):
- Job Title: IT Support Specialist
- Company: Geek Squad
- Years of Experience: 5

{resume_instruction}

STEPS:
1. Go to the job URL
2. Find and click "Easy Apply" or "Apply now" button
3. Call verify_indeed_easy_apply - if it says ABORT, stop and say "EXTERNAL_SITE"
4. When you see a form with input fields, call inject_form_data to fill ALL fields at once (FAST)
5. If inject_form_data succeeded, verify fields are filled, then call check_validation_errors
6. Click Continue on each page (only after validation passes)
7. On voluntary self-identification pages, select "I do not want to answer"
8. Repeat steps 4-6 for each new form page
9. Click Submit/Apply until done
10. Report SUCCESS when you see confirmation

When done, say "SUCCESS" if you see any confirmation (submitted, sent, received, thank you).
If the job redirects to external site, say "EXTERNAL_SITE".
If the job is unavailable or expired, say "JOB_UNAVAILABLE".
If Indeed requires login, say "NEEDS_LOGIN".
Otherwise explain what went wrong.
"""
    return task


async def apply_to_job(job: dict) -> tuple[bool, str]:
    """Apply to a single job using Browser-Use Cloud"""

    job_url = job.get('url', '')
    job_title = job.get('title', 'Unknown')
    job_company = job.get('company', 'Unknown')

    print(f"\n{'='*60}")
    print(f"Job: {job_title} at {job_company}")
    print(f"URL: {job_url}")
    is_external = not is_indeed_url(job_url)
    print(f"Type: {'External ATS' if is_external else 'Indeed Easy Apply'}")
    print(f"{'='*60}")

    # Get or generate resume
    resume_path = get_resume_path(job)
    if not resume_path:
        print("No resume found — sending to n8n factory...")
        factory_result = await send_to_factory_async(job)
        if factory_result and factory_result.get('files', {}).get('resume'):
            resume_filename = factory_result['files']['resume']
            resume_path = str(OUTPUT_DIR / resume_filename)
            print(f"Resume generated: {resume_path}")
        else:
            print("WARNING: Factory failed to generate resume, continuing without one")

    if resume_path:
        print(f"Resume: {resume_path}")
    else:
        print("Resume: None found")

    # Load cookies
    storage_state_path = load_cookies_as_storage_state()
    if storage_state_path:
        print(f"Loaded cookies from {storage_state_path}")
    else:
        print("WARNING: No cookies found - may need to login")

    # Create cloud browser session
    browser_use_api_key = os.getenv("BROWSER_USE_API_KEY")
    os.environ["BROWSER_USE_API_KEY"] = browser_use_api_key

    browser = BrowserSession(
        use_cloud=True,
        cloud_proxy_country_code='us',
        storage_state=storage_state_path,
    )

    # Rate limit retry logic (Gemini Priority 1.3 recommendation)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await browser.start()
            break  # Success
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                wait_time = 30 * (attempt + 1)  # Exponential: 30s, 60s, 90s
                print(f"  [RATE LIMIT] Browser-Use 429 error. Waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                if attempt == max_retries - 1:
                    return False, "rate_limit_exceeded"
            else:
                raise  # Re-raise non-rate-limit errors

    # Upload resume to cloud
    cloud_resume_name = None
    if resume_path:
        cdp_url = browser.browser_profile.cdp_url or ""
        session_match = re.search(r'wss://([^.]+)\.cdp', cdp_url)
        if session_match:
            cloud_session_id = session_match.group(1)
            print(f"Cloud session: {cloud_session_id}")
            cloud_resume_name = await upload_file_to_cloud_session(cloud_session_id, resume_path)

    file_paths = []
    if cloud_resume_name:
        file_paths.append(cloud_resume_name)
    elif resume_path:
        file_paths.append(resume_path)

    agent_resume_path = cloud_resume_name if cloud_resume_name else resume_path
    if cloud_resume_name:
        print(f"Using cloud resume path for agent: {cloud_resume_name}")
    task = build_task(job, agent_resume_path)

    # Create screenshots directory
    screenshots_dir = Path("/root/job_bot/screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    job_id = job.get('id', job.get('application_number', 'unknown'))
    gif_path = str(screenshots_dir / f"{job_company.replace(' ', '_')[:20]}_{job_id}.gif")

    agent = Agent(
        task=task,
        browser_session=browser,
        controller=controller,
        use_vision=True,
        available_file_paths=file_paths,
        max_failures=10,
        max_actions_per_step=5,
        max_steps=50,
        generate_gif=gif_path,
    )
    print(f"Recording session to: {gif_path}")

    try:
        print("Starting Browser-Use Cloud agent...")
        result = await agent.run()

        result_str = str(result)
        final_content = ""

        # Improved regex - handles quotes and longer content
        done_pattern = r"is_done=True.*?extracted_content=['\"](.+?)['\"]"
        matches = re.findall(done_pattern, result_str, re.DOTALL)
        if matches:
            final_content = matches[-1]
        else:
            # Fallback: look for any extracted_content
            status_match = re.search(r"extracted_content=['\"]([^'\"]+)['\"]", result_str)
            if status_match:
                final_content = status_match.group(1)

        print(f"Result: {final_content or 'No clear status found'}")

        # ============ IMPROVED SUCCESS DETECTION (Phase 2) ============
        # Try to get the current page for URL/content analysis
        try:
            current_page = await browser.get_current_page()
            if current_page:
                success_check = await detect_application_success(current_page)
                if success_check['is_success'] and success_check['confidence'] >= 70:
                    print(f"  [SUCCESS] Detected via page analysis: {success_check['matched_pattern']} (confidence: {success_check['confidence']}%)")
                    return True, "applied"
        except Exception as e:
            print(f"  [DEBUG] Page-based success detection skipped: {e}")

        # Also check the full result string for success indicators
        result_str_lower = result_str.lower()

        # FAST-FAIL: Check for job unavailable in full result
        for keyword in JOB_UNAVAILABLE_KEYWORDS:
            if keyword in result_str_lower:
                print(f"  [FAST-FAIL] Job unavailable detected: '{keyword}'")
                return False, "job_unavailable"

        # Check for success in the full result string (catches more cases)
        for keyword in SUCCESS_KEYWORDS:
            if keyword in result_str_lower:
                print(f"  [SUCCESS] Found in full result: '{keyword}'")
                return True, "applied"

        final_upper = final_content.upper()

        if "NEEDS_LOGIN" in final_upper:
            return False, "needs_login"
        elif "JOB_UNAVAILABLE" in final_upper or "NO LONGER EXISTS" in final_upper or "JOB POST NO LONGER" in final_upper:
            return False, "job_unavailable"
        elif "EXTERNAL_SITE" in final_upper or "EXTERNAL ATS" in final_upper or "COMPANY SITE" in final_upper:
            return False, "external_site"  # Special status for separate queue

        # FLEXIBLE SUCCESS MATCHING
        if check_success(final_content):
            return True, "applied"
        if "SUCCESS" in final_upper:
            return True, "applied"

        if final_content:
            return False, final_content[:200]
        else:
            return False, "incomplete"

    except Exception as e:
        print(f"Error: {e}")
        return False, str(e)[:200]

    finally:
        try:
            await browser.close()
        except:
            pass


async def main(max_jobs: int = 1, dry_run: bool = False, skip_blocked: bool = True, skip_health_check: bool = False):
    """Main entry point"""

    print("\n" + "="*60)
    print("Indeed Easy Apply Bot v2.0 - OPTIMIZED")
    print("Features: Form injection, validation gates, stuck detection")
    print("="*60)

    pending = load_queue("pending")
    applied = load_queue("applied")
    failed = load_queue("failed")
    skipped = load_queue("skipped")
    external = load_queue("external")  # Separate queue for external ATS jobs

    print(f"\nQueue status:")
    print(f"  Pending: {len(pending)}")
    print(f"  Applied: {len(applied)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  External: {len(external)}")

    if not pending:
        print("\nNo jobs in pending queue!")
        return

    # ============ COOKIE HEALTH CHECK ============
    if not dry_run and not skip_health_check:
        print("\n[HEALTH CHECK] Validating Indeed session...")
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            storage_state_path = load_cookies_as_storage_state()
            context = await browser.new_context(
                storage_state=storage_state_path if storage_state_path else None,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            session_valid = await check_cookie_health(page)
            await browser.close()

        if not session_valid:
            print("\n" + "!"*60)
            print("WARNING: Indeed session appears EXPIRED!")
            print("Action required: Re-export cookies from browser")
            print("File: /root/job_bot/agent/cookies.json")
            print("!"*60)
            print("\nContinuing anyway (some jobs may fail with needs_login)...")
        else:
            print("[HEALTH CHECK] Session VALID - Cookies are fresh")

    if dry_run:
        print("\n[DRY RUN MODE - No actual applications]")
        for job in pending[:max_jobs]:
            valid, reason = is_valid_job(job)
            blocked, domain = is_blocked_ats(job.get('url', ''))
            print(f"\n{job.get('title')} at {job.get('company')}")
            print(f"  URL: {job.get('url')}")
            print(f"  Valid: {valid} ({reason})")
            print(f"  Blocked ATS: {blocked} ({domain})")
            print(f"  Resume: {get_resume_path(job) or 'None found'}")
        return

    jobs_processed = 0
    jobs_skipped = 0

    while pending and jobs_processed < max_jobs:
        job = pending.pop(0)

        # ============ VALIDATION CHECKS ============
        valid, reason = is_valid_job(job)
        if not valid:
            print(f"\n[SKIP] Invalid job data: {reason} - {job.get('title', 'Unknown')}")
            job['skip_reason'] = reason
            skipped.append(job)
            save_queue("pending", pending)
            save_queue("skipped", skipped)
            jobs_skipped += 1
            continue

        if skip_blocked:
            blocked, domain = is_blocked_ats(job.get('url', ''))
            if blocked:
                print(f"\n[SKIP] Blocked ATS ({domain}): {job.get('title', 'Unknown')}")
                job['skip_reason'] = f"blocked_ats:{domain}"
                skipped.append(job)
                save_queue("pending", pending)
                save_queue("skipped", skipped)
                jobs_skipped += 1
                continue

        # ============ APPLY ============
        success, result_reason = await apply_to_job(job)

        job['apply_result'] = result_reason
        job['apply_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

        if success:
            print(f"\n[SUCCESS] Applied to {job.get('company')}")
            applied.append(job)
        elif result_reason == "external_site":
            print(f"\n[EXTERNAL] {job.get('company')}: Redirects to external ATS (saved for later)")
            external.append(job)
        else:
            print(f"\n[FAILED] {job.get('company')}: {result_reason}")
            failed.append(job)

        save_queue("pending", pending)
        save_queue("applied", applied)
        save_queue("failed", failed)
        save_queue("external", external)

        jobs_processed += 1

        if pending and jobs_processed < max_jobs:
            print(f"\nWaiting {DELAY_BETWEEN_JOBS}s before next job...")
            await asyncio.sleep(DELAY_BETWEEN_JOBS)

    print("\n" + "="*60)
    print("Session Complete")
    print("="*60)
    print(f"Processed: {jobs_processed}")
    print(f"Skipped: {jobs_skipped}")
    print(f"Applied: {len(applied)}")
    print(f"External: {len(external)} (saved for later - need different approach)")
    print(f"Failed: {len(failed)}")
    print(f"Remaining: {len(pending)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Indeed Easy Apply Bot v2.0 - OPTIMIZED")
    parser.add_argument("--max", type=int, default=1, help="Max jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip blocked ATS domains")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip cookie health check at startup")
    args = parser.parse_args()

    asyncio.run(main(
        max_jobs=args.max,
        dry_run=args.dry_run,
        skip_blocked=not args.no_skip,
        skip_health_check=args.skip_health_check
    ))
