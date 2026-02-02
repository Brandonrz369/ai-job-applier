# Job Application Bot - Architecture Design Document

Generated: Feb 2026 by Gemini 3 Pro (High Thinking Mode)

## Executive Summary

This document outlines the comprehensive architecture for an intelligent job application automation system. The system uses a **tiered AI approach** with form injection, pattern learning, and self-improvement capabilities.

---

## 1. Form Injection System ("Speed Layer")

### Problem
Current: 30-50 steps per application (click field → type → click next)
Target: 1-5 steps using JavaScript injection

### Solution: React-Aware Injection Script

```javascript
async function injectFormData(fieldMapping) {
    const setNativeValue = (element, value) => {
        const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
        const prototype = Object.getPrototypeOf(element);
        const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

        if (valueSetter && valueSetter !== prototypeValueSetter) {
            prototypeValueSetter.call(element, value);
        } else if (valueSetter) {
            valueSetter.call(element, value);
        }

        // Dispatch events React/Vue expect
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
    };

    for (const [selector, value] of Object.entries(fieldMapping)) {
        const el = document.querySelector(selector);
        if (!el) continue;

        if (el.type === 'checkbox' || el.type === 'radio') {
            if (el.checked !== value) el.click();
        } else if (el.type === 'file') {
            console.log(`__FILE_UPLOAD_NEEDED__:${selector}`);
        } else {
            setNativeValue(el, value);
        }

        // Random micro-delay for anti-bot
        await new Promise(r => setTimeout(r, 50 + Math.random() * 100));
    }
    return "Injection Complete";
}
```

### Form Analysis Flow
1. Extract simplified HTML (inputs/labels only)
2. Send to LLM: "Map user profile to CSS selectors"
3. Execute injection script
4. Click Submit

---

## 2. Pattern Matching / Learning ("Memory Layer")

### Form Fingerprinting
```python
def calculate_form_hash(form_html):
    """Generate unique hash for form structure"""
    inputs = extract_inputs(form_html)
    signature = "|".join([f"{i.name}:{i.type}" for i in inputs])
    return hashlib.sha256(signature.encode()).hexdigest()[:16]
```

### Knowledge Base Schema
```sql
CREATE TABLE form_patterns (
    hash VARCHAR(16) PRIMARY KEY,
    domain VARCHAR(255),
    selector_map JSONB,
    success_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    last_used TIMESTAMP
);
```

### Execution Flow
1. Calculate form hash
2. Query DB for existing pattern
3. If found with high success rate → use cached selectors (skip LLM)
4. If not found → call Tier 1 LLM
5. On success → save/update pattern

---

## 3. Multi-Tier Rescue Architecture

| Tier | Name | Model | Thinking | Trigger | Cost |
|------|------|-------|----------|---------|------|
| 0 | Cache Lookup | None | N/A | Form hash found in DB | $0 |
| 1 | Fast Tactical | Gemini 2.5 Flash | 0 | Unknown form, first attempt | ~$0.001 |
| 2 | DOM Analyst | Gemini 2.5 Flash | 2048 | Injection failed | ~$0.005 |
| 3 | Visual Tactician | Gemini 3 Pro | 0 | Need screenshot analysis | ~$0.01 |
| 4 | Deep Thinker | Gemini 3 Pro | 4096 | Complex logic, cover letter | ~$0.02 |
| 5 | Human Escalation | N/A | N/A | 3 failures at Tier 4 | N/A |

### WAF Detection
```python
def detect_waf_block(error_text, url, attempt_count):
    """Detect bot blocks vs logic errors"""
    waf_indicators = [
        'something went wrong',
        'please try again later',
        'access denied',
        'rate limit'
    ]
    is_job_site = any(s in url for s in ['indeed', 'linkedin', 'greenhouse'])
    has_indicator = any(i in error_text.lower() for i in waf_indicators)

    return is_job_site and has_indicator and attempt_count >= 2
```

---

## 4. Self-Improving Agent

### Session Recording
```python
@dataclass
class ApplicationAttempt:
    job_url: str
    form_hash: str
    selectors_used: dict
    actions_taken: list
    outcome: str  # 'success' | 'failed' | 'waf_blocked'
    error_message: str
    timestamp: datetime
```

### Learning Loop
1. Log every attempt
2. Nightly batch: analyze success patterns
3. Promote high-success selectors to Tier 0 cache
4. Demote/delete failed patterns
5. Build "semantic memory" for unusual questions

### Profile Building
When agent encounters new question types:
```python
# Agent learns: "T-Shirt Size" → "Large"
user_profile.add_learned_field("t_shirt_size", "Large", confidence=0.9)
```

---

## 5. Anti-Bot Humanization

### Mouse Movement (Bezier Curves)
```python
def bezier_mouse_move(start, end, steps=50):
    """Generate human-like curved mouse path"""
    # Control points for natural curve
    ctrl1 = (start[0] + random.randint(-50, 50),
             start[1] + random.randint(-50, 50))
    ctrl2 = (end[0] + random.randint(-50, 50),
             end[1] + random.randint(-50, 50))

    points = []
    for t in range(steps):
        t = t / steps
        x = (1-t)**3 * start[0] + 3*(1-t)**2*t * ctrl1[0] + \
            3*(1-t)*t**2 * ctrl2[0] + t**3 * end[0]
        y = (1-t)**3 * start[1] + 3*(1-t)**2*t * ctrl1[1] + \
            3*(1-t)*t**2 * ctrl2[1] + t**3 * end[1]
        points.append((x, y))
    return points
```

### Timing Randomization
- Keystroke delay: Gaussian(mean=80ms, std=30ms)
- Click delay: 200-600ms random
- Page load wait: 1-3s random
- Idle scrolling before major actions

### Viewport Variation
```python
viewport_width = 1920 + random.randint(-50, 50)
viewport_height = 1080 + random.randint(-50, 50)
```

---

## 6. Code Structure

```
/job_bot
├── /core
│   ├── orchestrator.py      # Main loop, tier routing
│   ├── browser_driver.py    # Browser-Use wrapper
│   └── state_machine.py     # Application flow states
├── /tiers
│   ├── tier0_cache.py       # Pattern DB lookup
│   ├── tier1_injector.py    # Fast form injection
│   ├── tier2_visual.py      # Screenshot-based fixes
│   ├── tier3_reasoning.py   # Complex logic handler
│   └── tier4_human.py       # Escalation handler
├── /skills
│   ├── form_filler.js       # React-aware injection
│   ├── dom_parser.py        # HTML cleaning
│   └── humanizer.py         # Mouse/timing randomization
├── /memory
│   ├── pattern_store.py     # Form pattern CRUD
│   ├── user_profile.py      # Dynamic user data
│   └── session_log.py       # Attempt recording
└── /config
    ├── applicant.json       # User profile data
    └── selectors.json       # Known form patterns
```

---

## 7. Implementation Phases

### Phase 1: Form Injection (Week 1)
- [ ] Implement React-aware JS injection
- [ ] HTML cleaning for LLM input
- [ ] Basic field mapping via Gemini

### Phase 2: Pattern Cache (Week 2)
- [ ] Form fingerprinting
- [ ] Pattern storage (JSON initially, then DB)
- [ ] Cache lookup before LLM calls

### Phase 3: Multi-Tier Orchestrator (Week 3)
- [ ] State machine for application flow
- [ ] Tier escalation logic
- [ ] WAF detection and skip

### Phase 4: Humanization (Week 4)
- [ ] Bezier mouse movements
- [ ] Timing randomization
- [ ] Viewport variation

### Phase 5: Self-Learning (Week 5+)
- [ ] Session recording
- [ ] Success pattern promotion
- [ ] Profile building from learned fields

---

## 8. Cost Projections

| Scenario | Steps | LLM Calls | Est. Cost |
|----------|-------|-----------|-----------|
| Cached form (Tier 0) | 3 | 0 | $0.00 |
| New simple form (Tier 1) | 5 | 1 | ~$0.005 |
| Complex form (Tier 2-3) | 10 | 3 | ~$0.02 |
| Cover letter needed (Tier 4) | 15 | 5 | ~$0.05 |

**Target:** 80% of applications via Tier 0-1 = avg cost < $0.01/application
