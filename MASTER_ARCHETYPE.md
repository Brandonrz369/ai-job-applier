# AI Job Applier - Master Archetype Document

**Purpose**: This document serves as the comprehensive blueprint for the AI Job Applier system. It captures all architectural decisions, learned patterns, and future roadmap so development can continue seamlessly.

**Last Updated**: February 2026
**Version**: 2.0

---

## Table of Contents
1. [System Vision](#1-system-vision)
2. [Current Architecture](#2-current-architecture)
3. [Platform Handlers](#3-platform-handlers)
4. [Tiered AI System](#4-tiered-ai-system)
5. [Form Injection System](#5-form-injection-system)
6. [Pattern Learning](#6-pattern-learning)
7. [Humanization Layer](#7-humanization-layer)
8. [Self-Improvement Loop](#8-self-improvement-loop)
9. [Roadmap](#9-roadmap)
10. [Lessons Learned](#10-lessons-learned)

---

## 1. System Vision

### Goal
Build an intelligent job application system that can:
- Apply to jobs across ALL major platforms (Indeed, LinkedIn, Greenhouse, Lever, Workday, etc.)
- Learn from each application attempt
- Minimize cost while maximizing success rate
- Operate autonomously with minimal human intervention

### Principles
1. **Platform-Native**: Don't fight the platform - learn its patterns
2. **Tiered Intelligence**: Use the cheapest effective solution first
3. **Learn & Cache**: Never solve the same problem twice
4. **Human-Like**: Avoid detection through behavioral mimicry
5. **Graceful Degradation**: Always have a fallback

---

## 2. Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                              │
│  (Decides platform, tier, and execution strategy)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   INDEED     │ │  LINKEDIN    │ │  EXTERNAL    │
│   Handler    │ │   Handler    │ │  ATS Handler │
│ (Easy Apply) │ │ (Easy Apply) │ │ (Greenhouse, │
│              │ │              │ │  Lever, etc) │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  TIERED AI SYSTEM                            │
│  Tier 0: Cache → Tier 1: Flash → Tier 2: Pro → Tier N: Human│
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 BROWSER-USE CLOUD                            │
│  (Residential proxy, stealth browser, vision capabilities)  │
└─────────────────────────────────────────────────────────────┘
```

### Current Components
| Component | Status | Technology |
|-----------|--------|------------|
| Indeed Handler | ✅ Active | Browser-Use Cloud |
| LinkedIn Handler | 🔜 Planned | TBD |
| Greenhouse Handler | 🔜 Planned | Pattern-based |
| Lever Handler | 🔜 Planned | Pattern-based |
| Workday Handler | ⚠️ Complex | Needs research |
| Tiered Rescue | ✅ Active | Gemini Flash/Pro |
| Pattern Cache | 🔜 Planned | JSON → PostgreSQL |
| Form Injection | 🔜 Planned | JavaScript |

---

## 3. Platform Handlers

### 3.1 Indeed Easy Apply
**Status**: Active
**Complexity**: Medium
**Bot Detection**: High (Cloudflare, behavioral)

**Flow**:
1. Navigate to job URL
2. Click "Easy Apply" or detect "Apply on company site"
3. Fill multi-page form
4. Handle reCAPTCHA
5. Submit

**Known Issues**:
- "Something went wrong" = Usually WAF/bot detection
- Radio buttons need React event dispatching
- Resume upload requires cloud file transfer

**Success Indicators**:
- "Application submitted"
- "Application has been sent"
- "Thank you for applying"

### 3.2 LinkedIn Easy Apply
**Status**: Planned
**Complexity**: High
**Bot Detection**: Very High

**Key Differences from Indeed**:
- Requires authenticated session
- More aggressive bot detection
- Different form structure
- "Easy Apply" modal vs full page

**Research Needed**:
- Session management
- Cookie persistence
- Rate limiting patterns

### 3.3 Greenhouse (boards.greenhouse.io)
**Status**: Planned
**Complexity**: Medium
**Bot Detection**: Low-Medium

**Characteristics**:
- Consistent form structure across companies
- Usually: Name, Email, Phone, Resume, Cover Letter, Custom Questions
- Standard HTML forms (easier than React)

**Strategy**:
- Build ONE Greenhouse handler
- Pattern cache selectors
- Works for 1000s of companies

### 3.4 Lever (jobs.lever.co)
**Status**: Planned
**Complexity**: Medium
**Bot Detection**: Low

**Characteristics**:
- Similar to Greenhouse
- Cleaner form structure
- Good candidate for form injection

### 3.5 Workday (myworkdayjobs.com)
**Status**: Blocked/Complex
**Complexity**: Very High
**Bot Detection**: High

**Challenges**:
- Multi-step wizard with state
- Session-based authentication
- Complex iframe structure
- Account creation often required

**Strategy**: Consider skipping or human-assist only

---

## 4. Tiered AI System

### Philosophy
> "Use the cheapest tool that can solve the problem"

### Tier Definitions

| Tier | Name | Model | Thinking | Use Case | Cost |
|------|------|-------|----------|----------|------|
| 0 | Cache Lookup | None | N/A | Known form pattern | $0 |
| 1 | Heuristic | Regex/Rules | N/A | Standard fields (name, email) | $0 |
| 2 | Fast Tactical | Gemini 2.5 Flash | 0 | Unknown simple forms | ~$0.001 |
| 3 | Smart Tactical | Gemini 2.5 Flash | 2048 | Form with validation errors | ~$0.003 |
| 4 | Visual Analysis | Gemini 3 Pro | 0 | Need screenshot understanding | ~$0.01 |
| 5 | Deep Reasoning | Gemini 3 Pro | 4096 | Complex logic, cover letters | ~$0.02 |
| 6 | Human Escalation | N/A | N/A | CAPTCHA, account creation | N/A |

### Escalation Logic
```python
def select_tier(context):
    # Tier 0: Check cache first
    if form_hash in pattern_cache:
        return Tier.CACHE

    # Tier 1: Try heuristics for standard fields
    if all_fields_are_standard(context.form):
        return Tier.HEURISTIC

    # Tier 2: First LLM attempt - fast
    if context.attempt == 1:
        return Tier.FAST_TACTICAL

    # Tier 3: Second attempt - add thinking
    if context.attempt == 2:
        return Tier.SMART_TACTICAL

    # Tier 4: Need visual understanding
    if context.has_complex_layout or context.attempt == 3:
        return Tier.VISUAL_ANALYSIS

    # Tier 5: Complex reasoning needed
    if context.needs_custom_content:
        return Tier.DEEP_REASONING

    # Tier 6: Give up, escalate
    return Tier.HUMAN_ESCALATION
```

### WAF/Bot Detection Handling
```python
def detect_and_handle_waf(error_text, url, attempts):
    """
    "Something went wrong" on job sites is usually bot detection,
    not a logic error. Don't waste tokens trying to reason about it.
    """
    waf_phrases = [
        'something went wrong',
        'please try again later',
        'unusual activity',
        'verify you are human'
    ]

    if any(phrase in error_text.lower() for phrase in waf_phrases):
        if attempts >= 2:
            return Action.SKIP_JOB  # Move to next job
        else:
            return Action.WAIT_AND_RETRY  # Wait 30s, try once more

    return Action.CONTINUE  # Not WAF, continue normal flow
```

---

## 5. Form Injection System

### Why Injection?
Traditional automation:
- Click field 1 → Type name (5 keystrokes) → Click field 2 → Type email (20 keystrokes)...
- **30-50 browser interactions per form**

Form injection:
- Analyze form → Generate mapping → Execute single JS → Click submit
- **3-5 browser interactions per form**

### The Injection Script
```javascript
/**
 * Universal React-aware form filler
 * Works with React, Vue, Angular, and vanilla HTML forms
 */
async function injectFormData(fieldMapping, options = {}) {
    const { delayMin = 30, delayMax = 80 } = options;

    // React-aware value setter
    const setNativeValue = (element, value) => {
        // Get the native value setter (bypasses React's synthetic events)
        const descriptor = Object.getOwnPropertyDescriptor(element, 'value');
        const prototype = Object.getPrototypeOf(element);
        const protoDescriptor = Object.getOwnPropertyDescriptor(prototype, 'value');

        // Use prototype setter to trigger React state update
        if (descriptor?.set && protoDescriptor?.set && descriptor.set !== protoDescriptor.set) {
            protoDescriptor.set.call(element, value);
        } else if (descriptor?.set) {
            descriptor.set.call(element, value);
        } else {
            element.value = value;
        }

        // Dispatch events React/Vue listen for
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
    };

    const results = { filled: [], failed: [], files: [] };

    for (const [selector, value] of Object.entries(fieldMapping)) {
        const el = document.querySelector(selector);

        if (!el) {
            results.failed.push({ selector, reason: 'not_found' });
            continue;
        }

        try {
            const tagName = el.tagName.toLowerCase();
            const inputType = el.type?.toLowerCase();

            // Handle different input types
            if (inputType === 'file') {
                // File inputs can't be set via JS - flag for Browser-Use
                results.files.push({ selector, value });
            } else if (inputType === 'checkbox') {
                if (el.checked !== Boolean(value)) el.click();
            } else if (inputType === 'radio') {
                if (!el.checked && el.value === value) el.click();
            } else if (tagName === 'select') {
                el.value = value;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                // Text, email, tel, textarea, etc.
                setNativeValue(el, value);
            }

            results.filled.push(selector);

            // Human-like micro-delay between fields
            await new Promise(r => setTimeout(r, delayMin + Math.random() * (delayMax - delayMin)));

        } catch (err) {
            results.failed.push({ selector, reason: err.message });
        }
    }

    return results;
}
```

### Field Mapping Generation
```python
def generate_field_mapping(form_html: str, user_profile: dict) -> dict:
    """
    Use LLM to map user profile fields to form selectors
    """
    # First, try heuristics (free)
    mapping = {}
    heuristic_patterns = {
        'first_name': ['first_name', 'fname', 'firstName', 'given_name'],
        'last_name': ['last_name', 'lname', 'lastName', 'family_name', 'surname'],
        'email': ['email', 'e-mail', 'emailAddress'],
        'phone': ['phone', 'tel', 'telephone', 'mobile', 'phoneNumber'],
        'linkedin': ['linkedin', 'linkedinUrl', 'linkedin_url'],
    }

    for field, patterns in heuristic_patterns.items():
        for pattern in patterns:
            # Check name, id, placeholder attributes
            if f'name="{pattern}"' in form_html or f'id="{pattern}"' in form_html:
                mapping[f'[name="{pattern}"], [id="{pattern}"]'] = user_profile.get(field)
                break

    # If heuristics didn't find everything, use LLM
    unfilled_fields = extract_empty_required_fields(form_html, mapping)
    if unfilled_fields:
        llm_mapping = call_gemini_for_mapping(form_html, user_profile, unfilled_fields)
        mapping.update(llm_mapping)

    return mapping
```

---

## 6. Pattern Learning

### Form Fingerprinting
Every form has a "signature" based on its structure:

```python
import hashlib

def calculate_form_signature(form_html: str) -> str:
    """
    Generate a unique signature for a form structure.
    Same form on different job postings = same signature.
    """
    # Extract input elements
    inputs = []
    for match in re.finditer(r'<(input|select|textarea)[^>]*>', form_html):
        tag = match.group(0)
        name = re.search(r'name=["\']([^"\']+)["\']', tag)
        type_ = re.search(r'type=["\']([^"\']+)["\']', tag)
        inputs.append(f"{name.group(1) if name else 'unnamed'}:{type_.group(1) if type_ else 'text'}")

    # Sort for consistency
    inputs.sort()
    signature_string = "|".join(inputs)

    return hashlib.sha256(signature_string.encode()).hexdigest()[:16]
```

### Pattern Storage Schema
```python
# patterns.json (simple) or PostgreSQL (production)
{
    "patterns": {
        "a1b2c3d4e5f6g7h8": {  # Form signature hash
            "domain": "boards.greenhouse.io",
            "company_examples": ["Stripe", "Notion", "Figma"],
            "selector_map": {
                "#first_name": "first_name",
                "#last_name": "last_name",
                "#email": "email",
                "input[name='phone']": "phone",
                "#resume": "__FILE__"
            },
            "success_count": 47,
            "fail_count": 2,
            "last_success": "2026-02-01T10:30:00Z",
            "notes": "Standard Greenhouse form, no custom questions"
        }
    }
}
```

### Learning Flow
```
Application Attempt
        │
        ▼
┌───────────────────┐
│ Calculate form    │
│ signature hash    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     ┌─────────────────┐
│ Hash exists in    │ YES │ Use cached      │
│ pattern cache?    │────▶│ selector map    │
└─────────┬─────────┘     └─────────────────┘
          │ NO
          ▼
┌───────────────────┐
│ Generate mapping  │
│ via Tier 2+ LLM   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Execute & track   │
│ success/failure   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ SUCCESS?          │
│ Save to cache     │
└───────────────────┘
```

---

## 7. Humanization Layer

### Why Humanization?
Bot detection systems analyze:
1. Mouse movement patterns (linear = bot)
2. Keystroke timing (uniform = bot)
3. Navigation patterns (too fast = bot)
4. Browser fingerprint (headless indicators)

### Mouse Movement (Bezier Curves)
```python
import random
import math

def generate_human_mouse_path(start: tuple, end: tuple, num_points: int = 50) -> list:
    """
    Generate a curved path that mimics human mouse movement.
    Humans don't move in straight lines - they curve and adjust.
    """
    # Random control points for bezier curve
    ctrl1 = (
        start[0] + (end[0] - start[0]) * 0.3 + random.randint(-100, 100),
        start[1] + (end[1] - start[1]) * 0.1 + random.randint(-100, 100)
    )
    ctrl2 = (
        start[0] + (end[0] - start[0]) * 0.7 + random.randint(-100, 100),
        start[1] + (end[1] - start[1]) * 0.9 + random.randint(-100, 100)
    )

    points = []
    for i in range(num_points):
        t = i / num_points
        # Cubic bezier formula
        x = (1-t)**3 * start[0] + 3*(1-t)**2*t * ctrl1[0] + 3*(1-t)*t**2 * ctrl2[0] + t**3 * end[0]
        y = (1-t)**3 * start[1] + 3*(1-t)**2*t * ctrl1[1] + 3*(1-t)*t**2 * ctrl2[1] + t**3 * end[1]

        # Add micro-jitter (hand tremor)
        x += random.gauss(0, 1)
        y += random.gauss(0, 1)

        points.append((int(x), int(y)))

    return points
```

### Timing Randomization
```python
import random
import asyncio

async def human_delay(action_type: str):
    """
    Add human-like delays based on action type.
    """
    delays = {
        'before_click': (0.3, 0.8),      # Think before clicking
        'between_keystrokes': (0.05, 0.15),  # Typing speed variation
        'after_page_load': (1.0, 3.0),    # "Reading" the page
        'before_submit': (0.5, 1.5),      # Review before submit
        'between_fields': (0.2, 0.5),     # Moving between inputs
    }

    min_delay, max_delay = delays.get(action_type, (0.1, 0.3))

    # Gaussian distribution for more natural timing
    delay = random.gauss((min_delay + max_delay) / 2, (max_delay - min_delay) / 4)
    delay = max(min_delay, min(max_delay, delay))  # Clamp to range

    await asyncio.sleep(delay)
```

### Idle Behaviors
```python
async def simulate_reading(page, duration_seconds: float = 2.0):
    """
    Simulate a human reading a page - random scrolls, pauses.
    """
    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        action = random.choice(['scroll_down', 'scroll_up', 'pause', 'mouse_move'])

        if action == 'scroll_down':
            await page.mouse.wheel(0, random.randint(100, 300))
        elif action == 'scroll_up':
            await page.mouse.wheel(0, random.randint(-150, -50))
        elif action == 'mouse_move':
            # Random mouse movement in viewport
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await page.mouse.move(x, y)

        await asyncio.sleep(random.uniform(0.3, 0.8))
```

---

## 8. Self-Improvement Loop

### Session Recording
```python
@dataclass
class ApplicationSession:
    """Record everything about an application attempt"""
    session_id: str
    timestamp: datetime

    # Job info
    job_url: str
    job_title: str
    company: str
    platform: str  # 'indeed', 'linkedin', 'greenhouse', etc.

    # Form info
    form_signature: str
    selector_map_used: dict

    # Execution
    tiers_used: list[int]
    total_steps: int
    total_cost_usd: float

    # Outcome
    outcome: str  # 'success', 'failed', 'waf_blocked', 'skipped'
    error_message: str
    final_screenshot: bytes

    # Learning
    new_patterns_discovered: list[dict]
    questions_encountered: list[str]
```

### Feedback Processing
```python
async def process_session_feedback(session: ApplicationSession):
    """
    After each application, update our knowledge base.
    """
    if session.outcome == 'success':
        # Promote selector map to cache
        await pattern_cache.upsert(
            signature=session.form_signature,
            selector_map=session.selector_map_used,
            increment_success=True
        )

        # Learn any new question-answer pairs
        for qa in session.questions_encountered:
            await user_profile.add_learned_qa(qa['question'], qa['answer'])

    elif session.outcome == 'failed':
        # Demote pattern confidence
        await pattern_cache.increment_failure(session.form_signature)

        # If pattern has >50% failure rate, delete it
        pattern = await pattern_cache.get(session.form_signature)
        if pattern and pattern.failure_rate > 0.5:
            await pattern_cache.delete(session.form_signature)
            logger.info(f"Deleted unreliable pattern: {session.form_signature}")

    elif session.outcome == 'waf_blocked':
        # Record platform-specific block
        await waf_tracker.record_block(
            platform=session.platform,
            timestamp=session.timestamp
        )
```

### Continuous Improvement Metrics
```python
# Track these metrics over time
metrics = {
    'success_rate': 'applications_successful / applications_attempted',
    'avg_cost_per_app': 'total_llm_cost / applications_attempted',
    'avg_steps_per_app': 'total_steps / applications_attempted',
    'cache_hit_rate': 'tier0_uses / applications_attempted',
    'waf_block_rate': 'waf_blocks / applications_attempted',
    'platform_success_rates': {
        'indeed': 0.72,
        'greenhouse': 0.89,
        'lever': 0.91,
        'linkedin': 0.0,  # Not implemented yet
    }
}
```

---

## 9. Roadmap

### Phase 1: Foundation (Current)
- [x] Indeed Easy Apply handler
- [x] Tiered Gemini rescue (Flash → Pro)
- [x] WAF detection
- [x] Basic humanization
- [ ] Form injection system

### Phase 2: Pattern Learning
- [ ] Form fingerprinting
- [ ] Pattern cache (JSON file)
- [ ] Success/failure tracking
- [ ] Heuristic field matching

### Phase 3: External ATS
- [ ] Greenhouse handler
- [ ] Lever handler
- [ ] iCIMS handler (if feasible)

### Phase 4: Advanced Humanization
- [ ] Bezier mouse movements
- [ ] Gaussian timing
- [ ] Idle behaviors
- [ ] Viewport randomization

### Phase 5: LinkedIn
- [ ] Session management research
- [ ] Easy Apply handler
- [ ] Rate limit handling
- [ ] Connection request automation (?)

### Phase 6: Self-Improvement
- [ ] Session recording
- [ ] Feedback processing
- [ ] Pattern promotion/demotion
- [ ] Metrics dashboard

### Phase 7: Scale
- [ ] PostgreSQL for patterns
- [ ] Redis for session state
- [ ] Queue management (multiple jobs in parallel)
- [ ] Human escalation interface

---

## 10. Lessons Learned

### What Works
1. **Residential proxies are essential** - Datacenter IPs are blocked instantly
2. **Browser-Use Cloud** - Good stealth out of the box
3. **Tiered approach** - Don't use expensive models for simple tasks
4. **WAF detection** - Don't waste tokens on bot blocks

### What Doesn't Work
1. **Workday** - Too complex, requires account creation, skip for now
2. **Fighting React forms with clicks** - Use event dispatching instead
3. **Reasoning about "Something went wrong"** - It's WAF, not logic
4. **High thinking for simple tasks** - Overkill and expensive

### Key Insights
1. **Form injection is the biggest win** - 10x step reduction
2. **Pattern caching is the second biggest win** - Near-zero cost for known forms
3. **LinkedIn needs dedicated research** - Can't just adapt Indeed handler
4. **Humanization is table stakes** - Without it, nothing else matters

---

## Appendix A: Environment Variables

```bash
# Required
BROWSER_USE_API_KEY=bu_xxx
GEMINI_API_KEY=AIzaSyXxx
CAPSOLVER_API_KEY=CAP-xxx

# Optional
N8N_WEBHOOK_URL=http://localhost:5678/webhook/incoming-job
GMAIL_EMAIL=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

## Appendix B: File Structure

```
/job_bot
├── bot/
│   └── applier.py          # Main application bot
├── agent/
│   ├── simple_hunter.py    # Job scraper
│   └── storage_state.json  # Browser cookies
├── queue/
│   ├── pending.json        # Jobs to apply
│   ├── applied.json        # Successful applications
│   ├── failed.json         # Failed attempts
│   └── external.json       # External ATS (for later)
├── output/
│   └── *.pdf               # Generated resumes
├── screenshots/
│   └── *.gif               # Session recordings
├── MASTER_ARCHETYPE.md     # This document
├── ARCHITECTURE_DESIGN.md  # Technical design
└── CLAUDE.md               # Claude Code instructions
```

---

*This document should be updated after each major feature addition or architectural change.*
