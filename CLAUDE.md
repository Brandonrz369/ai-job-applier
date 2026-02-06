# Job Bot - Automated Job Application System

## Project Purpose
AI-powered autonomous job application bot that:
1. Scrapes job listings from Indeed/LinkedIn using JobSpy
2. Scores job fit using Gemini 2.5 Flash (1-10 scale, threshold 6+)
3. Generates tailored resumes/cover letters via n8n + Gemini + Gotenberg
4. Applies to jobs using Browser-Use Cloud with Gemini-powered rescue system

## Current Architecture

```
JobSpy Scraper (agent/simple_hunter.py)
    ↓ Raw listings
Gemini 2.5 Flash Scorer (agent/scorer.py)
    ↓ Score >= 6 only
n8n Webhook → Gemini 3 Pro (resume/cover HTML) → Gotenberg (PDF)
    ↓ Tailored PDFs
Queue System (queue/pending.json)
    ↓
Browser-Use Cloud (bot/applier.py)
  ├── Form injection (JS-based, React-aware)
  ├── CAPTCHA solving (CapSolver: hCaptcha, Turnstile, reCAPTCHA)
  ├── Gemini Rescue: Tier 1 = 2.5 Flash, Tier 2 = Gemini 3 Pro (4K thinking)
  └── Success detection (URL + text + confidence scoring)
    ↓
Indeed Easy Apply + External ATS (with guest apply)
```

## Key Files

| File | Purpose |
|------|---------|
| `agent/simple_hunter.py` | JobSpy scraper + Gemini 2.5 Flash scoring, sends to n8n |
| `agent/scorer.py` | Gemini 2.5 Flash job fit scoring engine |
| `agent/candidate_profile.py` | Full candidate profile (497 lines) |
| `bot/applier.py` | Main applier - Browser-Use Cloud + Gemini rescue (1620+ lines) |
| `bot/utils.py` | Stuck detection, cookie health, success detection |
| `bot/email_helper.py` | Gmail/Outlook verification code extraction |
| `config.py` | Central config (paths, applicant info, model tiers) |
| `orchestrator.py` | Full pipeline orchestration (scrape + apply) |
| `queue/pending.json` | Jobs waiting to be applied |
| `queue/applied.json` | Successfully applied jobs |
| `queue/failed.json` | Failed application attempts |
| `output/` | Generated resume/cover letter PDFs |
| `infrastructure/` | Docker Compose (n8n, Gotenberg, file server) |
| `agent/.env` | API keys |

## AI Model Usage

| Purpose | Model | Provider |
|---------|-------|----------|
| Job Scoring | Gemini 2.5 Flash | Google AI |
| Resume/Cover Letter Gen | Gemini 3 Pro | Google AI (via n8n) |
| Browser Agent (primary) | Browser-Use Cloud | Browser-Use |
| Rescue Tier 1 (fast) | Gemini 2.5 Flash | Google AI |
| Rescue Tier 2 (deep) | Gemini 3 Pro Preview (4K thinking) | Google AI |
| Fallback (config.py tiers) | DeepSeek V3, Claude Sonnet | OpenRouter |

## How to Run

### 1. Start Infrastructure
```bash
cd /root/job_bot/infrastructure
docker-compose up -d  # n8n + Gotenberg + file server
```

### 2. Scrape + Score Jobs
```bash
cd /root/job_bot
python3 agent/simple_hunter.py          # Single run
python3 agent/simple_hunter.py --loop   # Continuous (every 4 hrs)
python3 agent/simple_hunter.py --dry-run  # Score only, no factory
```

### 3. Apply to Jobs
```bash
python3 bot/applier.py --dry-run        # Preview without applying
python3 bot/applier.py --max 1          # Apply to 1 job
python3 bot/applier.py --max 5          # Apply to multiple
python3 bot/applier.py --skip-health-check  # Skip cookie validation
```

### 4. Full Pipeline
```bash
python3 orchestrator.py --max-factory 30 --max-apply 10
python3 orchestrator.py --skip-scrape --max-apply 15 --parallel 2
```

## API Keys Required

Store in `/root/job_bot/agent/.env`:
```
GEMINI_API_KEY=xxx               # Gemini (scoring + rescue + n8n gen)
BROWSER_USE_API_KEY=bu_xxx       # Browser-Use Cloud
CAPSOLVER_API_KEY=CAP-xxx        # CAPTCHA solving
OPENROUTER_API_KEY=sk-or-xxx     # Multi-model access (fallback tiers)
GMAIL_EMAIL=xxx                  # Verification code extraction
GMAIL_APP_PASSWORD=xxx           # Gmail app password
ANTHROPIC_API_KEY=sk-ant-xxx     # Optional: Claude (tier 3 fallback)
DEEPSEEK_API_KEY=sk-xxx          # Optional: DeepSeek (tier 1 alt)
BROWSER_USE_PROFILE_ID=uuid      # Cloud browser profile (preserves Indeed login)
```

## Applicant Info

Currently configured for:
- Name: Brandon Ruiz
- Email: brandonlruiz98@gmail.com
- Phone: (213) 349-6790
- Location: Anaheim, CA

Edit `bot/applier.py` APPLICANT dict or `config.py` to change.

## Application Rules

- Primary: Indeed Easy Apply (form injection + vision-guided)
- External ATS: Guest apply supported (Workday, Greenhouse, etc. in blocked list)
- Skips if login required -> records as `needs_login`
- Skips if external redirect to blocked ATS -> records as `external_site`
- CAPTCHA auto-solved via CapSolver (hCaptcha, Turnstile, reCAPTCHA v2)
- Gemini rescue triggered after 3 consecutive identical failed actions

## Rate Limiting

10 second delay between applications (configurable in `bot/applier.py`)

## Browser-Use Cloud

- Uses Browser-Use 1.0 cloud browser (no local Chrome needed)
- Automatic US residential proxy
- Vision-enabled for screenshot analysis
- Max 50 steps per application
- GIF recording of sessions
- $0.005 per task (~200 tasks per $1)
- Dashboard: https://browser-use.com
