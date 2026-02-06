# Autonomous Job Application Bot

An AI-powered system that automatically finds, evaluates, and applies to jobs at scale.

## What It Does

1. **Scrapes** job listings from Indeed & LinkedIn (JobSpy, 44 search terms)
2. **Scores** each job using Gemini 2.5 Flash (fit analysis, 1-10 scale)
3. **Generates** tailored resume + cover letter PDFs (Gemini + Gotenberg)
4. **Applies** automatically using Browser-Use Cloud with Gemini rescue system

---

## Project Status

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| 1 | Core Pipeline | COMPLETE | Scraper + n8n + Gotenberg PDF |
| 2 | Smart Scoring | COMPLETE | Gemini 2.5 Flash scores 1-10, filters >= 6 |
| 3 | Queue System | COMPLETE | pending/applied/failed/manual/external/skipped |
| 4 | Browser-Use Cloud | COMPLETE | Cloud browser + US residential proxy |
| 5 | Form Injection | COMPLETE | JS-based React-aware form filling |
| 6 | CAPTCHA Solving | COMPLETE | CapSolver (hCaptcha, Turnstile, reCAPTCHA v2) |
| 7 | Gemini Rescue | COMPLETE | Tiered: Flash (fast) -> Gemini 3 Pro (deep thinking) |
| 8 | Cookie Health | COMPLETE | Auto-validates Indeed session before runs |
| 9 | Stuck Detection | COMPLETE | 3-strike rule + loop/stagnation scoring |
| 10 | External ATS | COMPLETE | Guest apply for non-Indeed portals |
| 11 | LinkedIn Auto-Apply | BLOCKED | Datacenter IP detected |
| 12 | Notifications | TODO | Discord webhooks |

---

## Architecture
```
+------------------------------------------------------------------------+
|                       JOB APPLICATION PIPELINE                          |
+------------------------------------------------------------------------+
|                                                                          |
|  +-----------+    +-------------+    +-------------+    +-------------+ |
|  |  SCRAPER  |--->|   SCORER    |--->|  GENERATOR  |--->|   APPLIER   | |
|  |  JobSpy   |    | Gemini 2.5  |    | Gemini 3    |    | Browser-Use | |
|  |           |    |   Flash     |    |   Flash     |    |    Cloud    | |
|  +-----------+    +-------------+    +-------------+    +-------------+ |
|       |                 |                  |                  |          |
|       v                 v                  v                  v          |
|  +-----------+    +-------------+    +-------------+    +-------------+ |
|  | Indeed    |    | Score 1-10  |    | Resume.pdf  |    | Form Inject | |
|  | LinkedIn  |    | Filter >= 6 |    | Cover.pdf   |    | CAPTCHA     | |
|  | 44 terms  |    | $60K+ floor |    | via n8n +   |    | Gemini      | |
|  | 3 regions |    | 75/25 ratio |    | Gotenberg   |    |   Rescue    | |
|  +-----------+    +-------------+    +-------------+    +-------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Components

### 1. Job Scraper (`agent/simple_hunter.py`)
- **Library**: JobSpy
- **Sources**: Indeed, LinkedIn
- **Searches**: 44 IT-focused search terms (IT Support, Help Desk, DevOps, Security, etc.)
- **Locations**: Anaheim CA, Irvine CA, Orange County CA + remote
- **Filter**: Jobs posted in last 72 hours, $60K+ salary floor
- **Ratio**: 75% local / 25% remote enforcement
- **Parallelism**: 3 concurrent scrapes + 20 parallel scoring threads
- **Output**: Writes to queue + triggers n8n for PDF generation

### 2. AI Scorer (`agent/scorer.py`)
- **Model**: Gemini 2.5 Flash (Google AI)
- **Input**: Job title, company, description, location, salary
- **Output**: Score 1-10, YES/NO recommendation, estimated salary
- **Profile**: Comprehensive 497-line candidate profile (`candidate_profile.py`)
- **Filter**: Only score >= 6 proceeds to PDF generation
- **Salary Floor**: $60K minimum (auto-reject below)

### 3. PDF Generator (n8n workflow)
- **Model**: Gemini 3 Pro (via n8n HTTP nodes)
- **Generates**: Tailored resume + cover letter HTML
- **Converter**: Gotenberg (HTML -> PDF, containerized)
- **Naming**: `Company_AppNumber_Resume.pdf`
- **Parallel**: Resume + Cover generated simultaneously

### 4. Queue System
```
/root/job_bot/queue/
|-- pending.json              # Jobs ready for auto-apply
|-- applied.json              # Successfully submitted
|-- failed.json               # Errors - retry later
|-- external.json             # External ATS redirects
|-- skipped.json              # Filtered out by scorer
|-- manual.json               # Needs human intervention
|-- strategic_easy_apply.json # High-value $100k+ targets
|-- easy_apply_queue.json     # All Easy Apply candidates
+-- high_value_targets.json   # $120k+ at major companies
```

### 5. Browser Applier (`bot/applier.py`)
- **Platform**: Browser-Use Cloud (no local Chrome needed)
- **Proxy**: Automatic US residential proxy
- **Vision**: Screenshot analysis for decision-making
- **Max Steps**: 50 per application
- **Features**:
  - JS-based form injection (React/Vue-aware, fills entire form in 1 step)
  - Mandatory validation gate before Submit/Continue
  - CAPTCHA solving: hCaptcha, Cloudflare Turnstile, reCAPTCHA v2 (via CapSolver)
  - Tiered Gemini rescue when stuck (3-strike trigger)
  - Email verification code extraction (Gmail IMAP)
  - Cookie health check at startup
  - Stuck detection system (loop + stagnation scoring)
  - Multi-method success detection (URL patterns + text confidence)
  - GIF session recording for debugging

### 6. Gemini Rescue System
- **Trigger**: After 3 consecutive identical failed actions
- **Tier 1**: Gemini 2.5 Flash (no thinking) - fast tactical fix
- **Tier 2**: Gemini 3 Pro Preview (4K thinking budget) - deep analysis
- **WAF Detection**: Identifies Indeed bot protection, auto-aborts
- **Output**: Single action recommendation (CLICK/TYPE/SCROLL/WAIT/STOP)

---

## Cost Breakdown (500 apps/month)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Gemini Scoring | 1500 jobs x ~$0.001 | ~$1.50 |
| Gemini PDF Gen | 500 apps x ~$0.005 | ~$2.50 |
| Browser-Use Cloud | 500 apps x $0.08 | ~$40.00 |
| CapSolver | ~25 solves x $0.10 | ~$2.50 |
| Hetzner VPS | 2GB RAM | $4.00 |
| **TOTAL** | | **~$50/month** |

**ROI**: One job offer = months of salary.

---

## API Keys (`.env`)
```env
GEMINI_API_KEY=xxx               # Gemini (scoring, rescue, n8n generation)
BROWSER_USE_API_KEY=bu_xxx       # Browser-Use Cloud
CAPSOLVER_API_KEY=CAP-xxx        # CAPTCHA solving (hCaptcha, Turnstile, reCAPTCHA)
OPENROUTER_API_KEY=sk-or-xxx     # Multi-model access (fallback tiers)
GMAIL_EMAIL=xxx                  # Verification code extraction
GMAIL_APP_PASSWORD=xxx           # Gmail app password
ANTHROPIC_API_KEY=sk-ant-xxx     # Optional: Claude (tier 3 fallback)
DEEPSEEK_API_KEY=sk-xxx          # Optional: DeepSeek (tier 1 alt)
```

---

## File Structure
```
/root/job_bot/
|-- orchestrator.py              # Full pipeline orchestration
|-- config.py                    # Central config (paths, models, applicant)
|-- test_external.py             # External ATS testing
|-- agent/
|   |-- simple_hunter.py         # JobSpy scraper + Gemini scoring
|   |-- scorer.py                # Gemini 2.5 Flash scoring engine
|   |-- candidate_profile.py     # Full candidate profile (497 lines)
|   |-- ai_applier.py            # Legacy Playwright applier
|   |-- cloudflare_handler.py    # CapSolver integration
|   |-- refresh_cookies.py       # Cookie refresh via Browser-Use
|   |-- .env                     # API keys
|   +-- venv/                    # Python environment
|-- bot/
|   |-- applier.py               # Main applier (Browser-Use Cloud, 1620+ lines)
|   |-- utils.py                 # Stuck detection, cookie health, success detection
|   |-- email_helper.py          # Gmail/Outlook verification codes
|   |-- config.py                # Bot-specific config
|   |-- orchestrator.py          # Legacy bot orchestrator
|   +-- test_single_job.py       # Single job test runner
|-- queue/                       # JSON-based job state machine
|-- output/                      # Generated resume/cover letter PDFs
|-- screenshots/                 # Debug screenshots + GIF recordings
|-- infrastructure/
|   |-- docker-compose.yml       # n8n + Gotenberg + file server
|   |-- n8n-workflow-v3.json     # Latest n8n workflow (Gemini)
|   +-- n8n-feedback-workflow.json
|-- skills/                      # Form handling JS/Python skills
|-- prompts/                     # System prompts for AI models
+-- logs/                        # Execution logs
```

---

## Usage

### Start Infrastructure
```bash
cd /root/job_bot/infrastructure
docker-compose up -d
```

### Run Scraper (Find + Score + Generate PDFs)
```bash
cd /root/job_bot
python3 agent/simple_hunter.py           # Single run
python3 agent/simple_hunter.py --loop    # Continuous (every 4 hrs)
python3 agent/simple_hunter.py --dry-run # Score only, no factory cost
python3 agent/simple_hunter.py --max 10  # Limit factory submissions
```

### Run Applier
```bash
python3 bot/applier.py --max 5                    # Apply to 5 jobs
python3 bot/applier.py --max 10 --skip-health-check  # Skip cookie check
python3 bot/applier.py --dry-run                   # Preview without applying
```

### Full Pipeline
```bash
python3 orchestrator.py --max-factory 30 --max-apply 10
python3 orchestrator.py --skip-scrape --max-apply 15 --parallel 2
python3 orchestrator.py --dry-run
```

### Check Queues
```bash
python3 -m json.tool /root/job_bot/queue/pending.json
python3 -m json.tool /root/job_bot/queue/applied.json
```

---

## Known Issues

| Issue | Cause | Status |
|-------|-------|--------|
| LinkedIn blocks automation | Datacenter IP detected | Move to manual queue |
| Indeed Cloudflare challenge | Bot detection | CapSolver auto-solve |
| Cookies expire | Session timeout | refresh_cookies.py |
| Complex ATS forms | Multi-page + account required | Blocked ATS domain list |
| WAF detection on Indeed | Repeated automation patterns | Gemini rescue auto-aborts |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Scraping | JobSpy (Python, parallel threads) |
| Job Scoring | Gemini 2.5 Flash (Google AI) |
| Document Generation | Gemini 3 Pro (via n8n) |
| PDF Conversion | Gotenberg (containerized) |
| Browser Automation | Browser-Use Cloud (US residential proxy) |
| Rescue AI | Gemini 2.5 Flash (Tier 1) + Gemini 3 Pro (Tier 2) |
| Form Injection | Custom JS (React/Vue-aware) |
| CAPTCHA Solving | CapSolver (hCaptcha, Turnstile, reCAPTCHA v2) |
| Workflow Engine | n8n (self-hosted) |
| Verification | Gmail IMAP (auto code extraction) |
| File Server | Static File Server |
| Hosting | Hetzner VPS (Ashburn, VA) |
| Fallback Models | DeepSeek V3, Claude Sonnet (via OpenRouter) |

---

## Metrics

- **Jobs Scraped per Run**: ~200
- **Pass Gemini Filter**: ~15-30 (score >= 6)
- **PDFs Generated**: ~15-30 per run
- **Auto-Apply Success Rate**: ~17% on Indeed Easy Apply
- **External ATS Success**: ~33% on tested platforms

---

## Development Timeline

| Date | Milestone |
|------|-----------|
| Dec 2024 | Server setup, n8n, JobSpy scraper, PDF generation |
| Dec 2024 | Scoring system, queue management, AI browser agent |
| Jan 2025 | Browser-Use Cloud migration, form injection, CAPTCHA solving |
| Feb 2026 | Gemini rescue system, stuck detection, cookie health checks |
| Feb 2026 | External ATS support, tiered model escalation, validation gates |

---

## Roadmap

- [x] Core scraping pipeline (JobSpy)
- [x] AI job scoring (Gemini 2.5 Flash)
- [x] Quality PDF generation (Gemini + Gotenberg)
- [x] Queue management system (6 queues)
- [x] Browser-Use Cloud automation
- [x] Form injection (React/Vue-aware)
- [x] CAPTCHA solving (hCaptcha, Turnstile, reCAPTCHA)
- [x] Gemini rescue system (tiered)
- [x] Stuck detection + validation gates
- [x] Cookie health checks
- [x] External ATS guest apply
- [ ] Discord notifications
- [ ] Response/interview tracking
- [ ] A/B test resume formats
- [ ] Self-improving feedback loop

---

## Author

Brandon Ruiz - Built with AI assistance

December 2024 - February 2026
