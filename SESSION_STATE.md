# Job Bot - Session State (Jan 27, 2026)

## Current Architecture (WORKING)

```
Scraper (agent/simple_hunter.py)
    |
    v
n8n Webhook (localhost:5678/webhook/incoming-job)
    |-- Anthropic API generates tailored resume HTML
    |-- Gotenberg converts HTML -> PDF
    |-- Saves to /root/output/
    v
Queue (queue/pending.json)
    v
Applier (bot/applier.py)
    |-- Sends job to n8n factory if no PDF exists
    |-- Pre-starts Browser-Use Cloud session (US residential proxy)
    |-- Uploads custom resume PDF to cloud session via SDK presigned URL
    |-- Agent fills Indeed Easy Apply form with vision
    |-- Uses Browser-Use native model (bu-1-0) -- NOT DeepSeek
    v
Indeed Easy Apply
```

## What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| n8n factory | WORKING | Generates tailored resume PDFs via Anthropic API |
| Gotenberg PDF | WORKING | Docker container on localhost |
| Queue system | WORKING | pending/applied/failed JSON files |
| Browser-Use Cloud | WORKING | `use_cloud=True, cloud_proxy_country_code='us'` |
| Cloud file upload | WORKING | SDK presigned URL -> upload PDF to cloud session |
| Native model (bu-1-0) | WORKING | Vision enabled, handles dialogs, qualification Qs |
| Indeed cookies | WORKING | Loaded via `storage_state` on BrowserSession |

## Key Decisions Made

1. **Removed DeepSeek LLM** - Was blind (no vision), got stuck on dialogs. Native model sees screenshots.
2. **Cloud not local Playwright** - Local Chromium gets cert errors + Cloudflare blocked. Cloud has stealth.
3. **US residential proxy** - `cloud_proxy_country_code='us'` instead of Bright Data proxy (which caused SSL issues locally).
4. **Resume upload via SDK** - Local file paths don't exist on cloud browser. Must use `browser_session_upload_file_presigned_url()` to push PDF to cloud session first.
5. **max_failures=10** - Default was 3. Transient LLM API errors killed a 100%-complete application on the Submit step.
6. **Removed catch-all resume pattern** - `*_Resume.pdf` was matching wrong resumes. Now only company/app-specific patterns.

## How to Run

```bash
# SSH in
ssh root@5.161.45.43
cd /root/job_bot

# Scrape fresh jobs
python3 agent/simple_hunter.py

# Apply to jobs
python3 bot/applier.py --max 1     # 1 job
python3 bot/applier.py --max 5     # 5 jobs
python3 bot/applier.py --dry-run   # preview only

# Test n8n factory
curl -X POST http://localhost:5678/webhook/incoming-job \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","company":"TestCo","description":"Test job","url":"https://indeed.com/test","location":"Long Beach, CA"}'
```

## Queue Status (end of session)

- **Pending: 0** (all processed)
- **Applied: 2** (DSI Systems confirmed success)
- **Failed: 30** (mix of: not Easy Apply, external site, needs login, Indeed errors)

## Files Modified This Session

| File | Changes |
|------|---------|
| `bot/applier.py` | Major rewrite: Cloud mode, native model, factory integration, SDK file upload, improved task prompt |
| `CLAUDE.md` | Existed before (project docs) |
| `SESSION_STATE.md` | This file - session handoff |

## applier.py Pipeline (per job)

1. Pop job from `queue/pending.json`
2. `get_resume_path()` - check if PDF already exists in `/root/output/`
3. If no PDF: `send_to_factory()` - POST to n8n webhook, get back PDF path
4. `build_task()` - construct natural language prompt with applicant info + resume instructions
5. `load_cookies_as_storage_state()` - convert cookies.json to Playwright format
6. Create `BrowserSession(use_cloud=True, cloud_proxy_country_code='us')`
7. `browser.start()` - pre-start to get cloud session ID
8. `upload_file_to_cloud_session()` - SDK presigned URL upload of resume PDF
9. Create `Agent(task, browser_session, use_vision=True, available_file_paths, max_failures=10)`
10. `agent.run()` - Browser-Use native model fills the application
11. Parse result: SUCCESS / NEEDS_LOGIN / EXTERNAL_SITE / incomplete
12. Move job to `applied.json` or `failed.json`

## Known Issues

- **Indeed "Something went wrong" errors** - Indeed's own UI bugs, not bot-related
- **City/State field** - Sometimes concatenates old + new values. Agent usually recovers.
- **Cookies may expire** - If all jobs return NEEDS_LOGIN, re-export cookies from browser.
- **LLM API transient failures** - Browser-Use's API occasionally fails. `max_failures=10` helps.
- **pending.json may include non-Easy-Apply jobs** - Scraper filter isn't 100%. Bot handles gracefully.

## Environment

- Server: 5.161.45.43 (Hetzner)
- Python: 3.12.3
- browser-use: 0.11.3
- browser-use-sdk: 2.0.13
- n8n: Docker container
- Gotenberg: Docker container

## API Keys (in /root/job_bot/agent/.env)

- `BROWSER_USE_API_KEY` - Browser-Use Cloud
- `ANTHROPIC_API_KEY` - Used by n8n for resume generation
- `DEEPSEEK_API_KEY` - No longer used by applier (kept for other scripts)
- `N8N_WEBHOOK_URL` - defaults to localhost:5678

## Next Steps

- Scrape a fresh batch of Easy Apply jobs: `python3 agent/simple_hunter.py`
- Run applier on the batch: `python3 bot/applier.py --max 5`
- Consider updating cookies if NEEDS_LOGIN errors appear
- Could add LinkedIn support to simple_hunter.py
