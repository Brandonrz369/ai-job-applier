# Job Bot - Automated Job Application System

## Project Purpose
Automated job application bot that:
1. Scrapes job listings from Indeed/LinkedIn using JobSpy
2. Generates tailored resumes/cover letters via n8n workflows
3. Applies to jobs using Browser-Use 1.0 cloud browser automation

## Current Architecture

```
JobSpy (agent/simple_hunter.py)
    ↓
n8n Webhook → PDF Generation (Gotenberg)
    ↓
Queue (queue/pending.json)
    ↓
Browser-Use 1.0 Cloud (bot/applier.py)
    ↓
Indeed Easy Apply
```

## Key Files

| File | Purpose |
|------|---------|
| `agent/simple_hunter.py` | JobSpy scraper, sends jobs to n8n webhook |
| `bot/applier.py` | Main applier using Browser-Use 1.0 cloud API |
| `config.py` | Central config (paths, applicant info) |
| `queue/pending.json` | Jobs waiting to be applied |
| `queue/applied.json` | Successfully applied jobs |
| `queue/failed.json` | Failed application attempts |
| `output/` | Generated resume/cover letter PDFs |
| `agent/.env` | API keys (BROWSER_USE_API_KEY, etc.) |

## How to Run

### 1. Scrape Jobs
```bash
cd /root/job_bot
python3 agent/simple_hunter.py
```

### 2. Apply to Jobs
```bash
# Dry run (preview without applying)
python3 bot/applier.py --dry-run

# Apply to 1 job
python3 bot/applier.py --max 1

# Apply to multiple jobs
python3 bot/applier.py --max 5
```

## API Keys Required

Store in `/root/job_bot/agent/.env`:
```
BROWSER_USE_API_KEY=bu_xxx    # Browser-Use cloud API
ANTHROPIC_API_KEY=sk-ant-xxx  # Optional: for Claude
DEEPSEEK_API_KEY=sk-xxx       # Optional: for DeepSeek
OPENROUTER_API_KEY=sk-or-xxx  # Optional: for OpenRouter
```

## Applicant Info

Currently configured for:
- Name: Brandon Ruiz
- Email: brandonhewitt886@gmail.com
- Phone: 714-598-3651
- Location: Long Beach, CA

Edit `bot/applier.py` APPLICANT dict to change.

## Job Application Rules

The bot only handles Indeed Easy Apply jobs:
- Skips non-Indeed URLs
- Stops if login required → records as `needs_login`
- Stops if external site redirect → records as `external_site`
- Stops if complex multi-page form → records as `complex_form`

## Rate Limiting

10 second delay between applications (configurable in `bot/applier.py`)

## Browser-Use Cloud

- Uses Browser-Use 1.0 cloud browser (no local Chrome needed)
- Automatic US residential proxy
- Vision-enabled for screenshot analysis
- $0.005 per task (~200 tasks per $1)
- Dashboard: https://browser-use.com
