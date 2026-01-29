# Job Application Bot - Complete Project Documentation

## Executive Summary

**What:** Autonomous system that applies to jobs on Indeed using AI agents controlling a browser.

**Why:** Automate the tedious job application process at scale.

**Status:** Core system built, needs account setup + testing.

**End Goal:** 100+ applications per day, fully autonomous, ~$50-100/month total cost.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Infrastructure](#2-infrastructure)
3. [Credentials & Environment](#3-credentials--environment)
4. [All Files Created](#4-all-files-created)
5. [System Components](#5-system-components)
6. [Current Status](#6-current-status)
7. [What's Left To Do](#7-whats-left-to-do)
8. [Cost Breakdown](#8-cost-breakdown)
9. [How To Run](#9-how-to-run)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR VPS                                        │
│                         (Hetzner $4/month)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │    │
│  │   │   n8n        │    │  Job Queue   │    │  AI Agent    │          │    │
│  │   │  Workflows   │───▶│   (JSON)     │───▶│ (browser-use)│          │    │
│  │   │              │    │              │    │              │          │    │
│  │   └──────────────┘    └──────────────┘    └──────┬───────┘          │    │
│  │         │                                         │                  │    │
│  │         ▼                                         ▼                  │    │
│  │   ┌──────────────┐                        ┌──────────────┐          │    │
│  │   │   Resume     │                        │   Cookies    │          │    │
│  │   │  Generator   │                        │   Storage    │          │    │
│  │   └──────────────┘                        └──────────────┘          │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      │ WebSocket                             │
│                                      ▼                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BRIGHT DATA                                         │
│                    (Browser API - $97 credit)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │   Remote Chrome Browser with Residential Proxy                       │    │
│  │   - Rotating residential IPs                                         │    │
│  │   - CAPTCHA solving built-in                                         │    │
│  │   - Fingerprint randomization                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      │ HTTPS (residential IP)                │
│                                      ▼                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             ┌──────────┐       ┌──────────┐       ┌──────────┐
             │  Indeed  │       │  Gmail   │       │  Other   │
             │          │       │          │       │  Sites   │
             └──────────┘       └──────────┘       └──────────┘
```

---

## 2. Infrastructure

### 2.1 VPS (Hetzner)

| Property | Value |
|----------|-------|
| Provider | Hetzner |
| IP | `5.161.45.43` |
| OS | Ubuntu |
| Cost | ~$4/month |
| SSH | `ssh root@5.161.45.43` |

### 2.2 Bright Data (Browser API)

| Property | Value |
|----------|-------|
| Zone | `jobbot` |
| WebSocket URL | `wss://brd-customer-$CUSTOMER_ID-zone-$ZONE:$PASSWORD@brd.superproxy.io:9222` |
| Credit | $97 remaining |
| Cost | ~$0.08 per browser minute |
| Estimated capacity | ~1,200 applications |

### 2.3 OpenRouter (AI API)

| Property | Value |
|----------|-------|
| API Base | `https://openrouter.ai/api/v1` |
| Primary Model | `google/gemini-2.5-flash-preview-05-20` |
| Cost | $0.15 per 1M tokens |
| API Key Location | `/root/job_bot/agent/.env` |

### 2.4 n8n (Workflow Automation)

| Property | Value |
|----------|-------|
| URL | `http://5.161.45.43:5678` |
| Purpose | Job scraping, resume generation, queue management |
| Status | Installed, workflows need setup |

---

## 3. Credentials & Environment

### 3.1 Environment File

**Location:** `/root/job_bot/agent/.env`

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3.2 Burner Account

| Property | Value |
|----------|-------|
| Email | Set in `.env` as `INDEED_EMAIL` |
| Gmail Password | Set in `.env` as `GMAIL_PASSWORD` |
| Indeed Password | Set in `.env` as `INDEED_PASSWORD` |
| Phone | `714-598-3651` |
| Name | `Brandon Ruiz` |
| Location | `Long Beach, CA` |
| Work Authorization | Yes |
| Sponsorship Required | No |
| Years Experience | 3 |

### 3.3 Resume

**Location:** Dynamically selected from `/root/output/`

### 3.4 Bright Data Credentials

Set in `.env`:
- `BRIGHT_DATA_CUSTOMER_ID`
- `BRIGHT_DATA_ZONE`
- `BRIGHT_DATA_PASSWORD`

---

## 4. All Files Created

### 4.1 Directory Structure

```
/root/job_bot/
├── agent/
│   └── .env                          # OpenRouter API key
│
├── bot/
│   ├── unified_bot.py                # ⭐ MAIN SCRIPT - everything in one file
│   ├── autonomous_applier.py         # Advanced version with shared memory
│   ├── simple_job_bot.py             # Simplified version
│   ├── gmail_verification_agent.py   # Handles Gmail verification
│   ├── cookie_manager.py             # Cookie utilities
│   ├── antigravity_integration.py    # Free Gemini 3 Pro via Antigravity
│   └── install_opencode_antigravity.sh  # Antigravity setup script
│
├── cookies/
│   ├── indeed_matwukagw527292.json   # Indeed cookies (after setup)
│   └── gmail_matwukagw527292.json    # Gmail cookies (after setup)
│
├── logs/
│   ├── apply_YYYYMMDD_HHMMSS.json    # Application logs
│   └── learned_solutions.json         # What worked (for learning)
│
├── queue/
│   ├── pending.json                  # Jobs to apply to
│   ├── applied.json                  # Successful applications
│   └── manual.json                   # Needs human intervention
│
└── output/
    └── ExecutivePlacements_com_38_Resume.pdf
```

### 4.2 File Descriptions

| File | Purpose | Status |
|------|---------|--------|
| `unified_bot.py` | Main script, all credentials embedded, handles everything | ✅ Ready |
| `autonomous_applier.py` | Advanced version with shared memory between model swaps | ✅ Ready |
| `cookie_manager.py` | Save/load browser cookies for persistent login | ✅ Ready |
| `gmail_verification_agent.py` | Automated Gmail verification through proxy | ✅ Ready |
| `antigravity_integration.py` | Free Gemini 3 Pro via Google Antigravity | ✅ Ready |
| `install_opencode_antigravity.sh` | Install OpenCode + Antigravity plugin | ✅ Ready |
| `.env` | API keys | ✅ Exists |

---

## 5. System Components

### 5.1 AI Agent (browser-use)

**What it does:**
- Controls Chrome browser through CDP protocol
- Reads page, decides what to click/type
- Fills forms, uploads files, navigates

**Library:** `browser-use` (Python)

**How it works:**
```python
from browser_use import Agent, BrowserSession
from browser_use.llm import ChatOpenAI

browser = BrowserSession(cdp_url=BRIGHT_DATA_WS)
llm = ChatOpenAI(model="google/gemini-2.5-flash-preview-05-20")
agent = Agent(task="Apply to this job...", llm=llm, browser_session=browser)
result = await agent.run(max_steps=30)
```

### 5.2 Cookie System

**Purpose:** Login once, reuse session forever

**Flow:**
```
First run:
  Agent logs into Indeed → Cookies saved to /cookies/indeed_xxx.json

Future runs:
  Load cookies → Already logged in → Skip login → Apply directly
```

### 5.3 Gmail Verification

**Problem:** Indeed sometimes requires email verification code

**Solution:** Agent handles it automatically:
1. Indeed says "enter verification code"
2. Agent opens new tab → Gmail
3. Agent logs into Gmail (through Bright Data proxy)
4. Agent finds Indeed email, extracts code
5. Agent returns to Indeed, enters code
6. Done

**Your IP never touches Gmail or Indeed** - all through Bright Data residential proxies.

### 5.4 Model Selection

**Current:** Single best model (Gemini 2.5 Flash)
- Smart enough for the task
- Cheap ($0.15/1M tokens)
- No escalation logic needed

**Optional upgrade:** Gemini 3 Pro via Antigravity (FREE)
- Requires OpenCode CLI setup
- Uses Google OAuth through Antigravity IDE
- $0 cost

### 5.5 Shared Memory (Advanced)

**Purpose:** When swapping between models, preserve context

**How:**
```python
# All models read/write to shared memory
memory = {
    "completed_steps": ["Navigate", "Click Apply", "Enter email"],
    "failed_approaches": ["Google SSO → popup uncontrollable"],
    "current_phase": "login",
    "page_elements": ["button:Continue", "input:password", "link:forgot"],
}
```

**Benefit:** Models don't repeat failed attempts, don't redo completed steps.

---

## 6. Current Status

### 6.1 What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| VPS | ✅ Running | Ubuntu at 5.161.45.43 |
| Bright Data | ✅ Connected | $97 credit, WebSocket working |
| OpenRouter | ✅ Working | API key configured |
| browser-use | ✅ Installed | Python library ready |
| unified_bot.py | ✅ Ready | All credentials embedded |
| Cookie system | ✅ Ready | Code written, not yet used |

### 6.2 What's Blocked

| Issue | Blocker | Solution |
|-------|---------|----------|
| Indeed account | Not registered/verified | Run `python3 unified_bot.py setup` |
| No cookies | Need first login | Will be created during setup |
| Antigravity | Optional, not set up | Run install script if you want free Gemini 3 |

### 6.3 Test Results (Last Run)

```
Gemini Flash: Navigate ✓ → Click Apply ✓ → Login page ✓ → Enter email ✓ → STUCK
Reason: Indeed requires verification code, account not fully set up
```

---

## 7. What's Left To Do

### Phase 1: Account Setup (5 minutes)

```bash
ssh root@5.161.45.43
cd /root/job_bot/bot
python3 unified_bot.py setup
```

This will:
1. Connect to Bright Data browser
2. Go to Indeed, start signup
3. If verification needed → open Gmail, get code
4. Complete registration
5. Save cookies

### Phase 2: Test Single Application (2 minutes)

```bash
# Find an Easy Apply job on Indeed, get URL
python3 unified_bot.py apply "https://indeed.com/viewjob?jk=XXXXX"
```

### Phase 3: Batch Applications

```bash
# Create file with job URLs (one per line)
echo "https://indeed.com/viewjob?jk=abc123" > jobs.txt
echo "https://indeed.com/viewjob?jk=def456" >> jobs.txt

# Run batch
python3 unified_bot.py batch jobs.txt
```

### Phase 4: Full Automation (Future)

1. n8n workflow scrapes Indeed for matching jobs
2. Adds to queue
3. Bot processes queue automatically
4. Logs results

---

## 8. Cost Breakdown

### 8.1 Current Costs (Per Application)

| Component | Cost | Notes |
|-----------|------|-------|
| Bright Data | ~$0.05 | ~30 seconds browser time |
| OpenRouter (Gemini 2.5 Flash) | ~$0.02 | ~100k tokens per app |
| **Total per application** | **~$0.07** | |

### 8.2 Monthly Projection

| Volume | Bright Data | AI | VPS | Total |
|--------|-------------|-----|-----|-------|
| 100 apps/month | $5 | $2 | $4 | **$11** |
| 500 apps/month | $25 | $10 | $4 | **$39** |
| 1,000 apps/month | $50 | $20 | $4 | **$74** |
| 3,000 apps/month | $150 | $60 | $4 | **$214** |

### 8.3 With Antigravity (Free AI)

| Volume | Bright Data | AI | VPS | Total |
|--------|-------------|-----|-----|-------|
| 1,000 apps/month | $50 | $0 | $4 | **$54** |
| 3,000 apps/month | $150 | $0 | $4 | **$154** |

---

## 9. How To Run

### Quick Start

```bash
# 1. SSH to VPS
ssh root@5.161.45.43

# 2. Go to bot directory
cd /root/job_bot/bot

# 3. Check status
python3 unified_bot.py status

# 4. Set up Indeed account (one time)
python3 unified_bot.py setup

# 5. Apply to a job
python3 unified_bot.py apply "https://indeed.com/viewjob?jk=XXXXX"
```

### Commands Reference

| Command | Purpose |
|---------|---------|
| `python3 unified_bot.py status` | Show accounts, cookies, API key status |
| `python3 unified_bot.py setup` | Set up Indeed account with Gmail verification |
| `python3 unified_bot.py setup email@gmail.com` | Set up specific account |
| `python3 unified_bot.py apply <url>` | Apply to single job |
| `python3 unified_bot.py batch <file>` | Apply to multiple jobs |

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Check `/root/job_bot/agent/.env` exists with `OPENROUTER_API_KEY=...` |
| "Connection refused" | Bright Data browser may be rate limited, wait and retry |
| "STUCK: verification code" | Gmail password may be wrong, check `unified_bot.py` line 34 |
| "STUCK: Google SSO only" | Indeed changed UI, may need prompt adjustment |

---

## 10. End Goal

### Vision

```
You: *sleeping*

Bot: 
  3:00 AM - Scraped 47 new job postings matching "software engineer"
  3:05 AM - Generated tailored resume for Company A
  3:06 AM - Applied to Company A ✓
  3:08 AM - Applied to Company B ✓
  3:10 AM - Applied to Company C ✓
  ...
  6:00 AM - Applied to 35 jobs, 3 failed (logged for review)

You: *wake up to interview requests*
```

### Success Metrics

| Metric | Target |
|--------|--------|
| Applications per day | 50-100 |
| Success rate | 90%+ |
| Cost per application | < $0.10 |
| Human intervention | < 5% of applications |
| Time investment | < 30 min/week (reviewing failures) |

### What "Done" Looks Like

1. ✅ Bot runs 24/7 on VPS
2. ✅ Automatically scrapes matching jobs
3. ✅ Generates tailored resumes
4. ✅ Applies with near-zero failures
5. ✅ Rotates between burner accounts
6. ✅ Self-heals from common errors
7. ✅ Learns from failures (shared memory)
8. ✅ Costs < $100/month for 1000+ applications

---

## Appendix A: File Contents Reference

### unified_bot.py - Key Sections

```python
# Lines 22-29: Bright Data config
BRIGHT_DATA = {
    "ws": "wss://brd-customer-$CUSTOMER_ID-zone-$ZONE:$PASSWORD@brd.superproxy.io:9222",
}

# Lines 31-45: Account credentials
ACCOUNTS = {
    "matwukagw527292@gmail.com": {
        "gmail_password": "$GMAIL_PASSWORD",
        "indeed_password": "$INDEED_PASSWORD",
        "name": "Brandon Ruiz",
        "phone": "714-598-3651",
        ...
    },
}

# Line 46: Resume path
RESUME_PATH = "/root/output/ExecutivePlacements_com_38_Resume.pdf"
```

### .env File

```bash
# /root/job_bot/agent/.env
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
```

---

## Appendix B: Adding More Accounts

Edit `unified_bot.py`, add to ACCOUNTS dict:

```python
ACCOUNTS = {
    "matwukagw527292@gmail.com": { ... },  # Existing
    
    # Add new account:
    "newburner@gmail.com": {
        "gmail_password": "$GMAIL_PASSWORD",
        "indeed_password": "$INDEED_PASSWORD", 
        "name": "John Smith",
        "phone": "555-123-4567",
        "location": "New York, NY",
        "work_auth": "Yes",
        "sponsorship": "No",
        "experience_years": "5",
    },
}
```

Then run setup:
```bash
python3 unified_bot.py setup newburner@gmail.com
```

---

## Appendix C: Antigravity Setup (Optional - Free AI)

If you want Gemini 3 Pro for free instead of paying OpenRouter:

```bash
# 1. Install OpenCode + Antigravity
bash install_opencode_antigravity.sh

# 2. Authenticate (requires browser - do on local machine, copy auth to VPS)
opencode auth login
# Select: Google → OAuth with Google (Antigravity)

# 3. Test
opencode run "Say hello" --model=google/gemini-3-pro-high
```

Then modify `unified_bot.py` to use OpenCode CLI instead of OpenRouter API.

---

*Last updated: December 19, 2024*
*Version: 1.0*
