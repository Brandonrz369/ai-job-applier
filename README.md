# 🤖 Autonomous Job Application Bot

An AI-powered system that automatically finds, evaluates, and applies to jobs.

## 🎯 What It Does

1. **Scrapes** job listings from Indeed & LinkedIn
2. **Scores** each job using AI (fit analysis)
3. **Generates** tailored resume + cover letter PDFs
4. **Applies** automatically using browser AI agent

---

## 📊 Project Status

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| 1 | Core Pipeline | ✅ COMPLETE | Scraper + n8n + Gotenberg PDF |
| 2 | Smart Scoring | ✅ COMPLETE | Haiku scores 1-10, filters ≥6 |
| 3 | Queue System | ✅ COMPLETE | pending/applied/failed/manual |
| 4 | Notifications | ⬜ TODO | Discord webhooks |
| 5 | GitHub Portfolio | ⬜ TODO | Public repo + stats |
| 6 | AI Browser Agent | 🔄 IN PROGRESS | Gemini 2.0 Flash via OpenRouter |
| 7 | LinkedIn Auto-Apply | ❌ BLOCKED | Datacenter IP detected |
| 8 | Detection Avoidance | ⬜ TODO | Residential proxies |
| 9 | Monitoring | ⬜ TODO | Health checks + alerts |

---

## 🏗️ Architecture
```
┌──────────────────────────────────────────────────────────────────────────┐
│                         JOB APPLICATION PIPELINE                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌───────────┐ │
│  │   SCRAPER   │───▶│   SCORER    │───▶│  GENERATOR  │───▶│  APPLIER  │ │
│  │   JobSpy    │    │   Haiku     │    │   Opus 4.5  │    │  Gemini   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └───────────┘ │
│        │                  │                  │                  │        │
│        ▼                  ▼                  ▼                  ▼        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌───────────┐ │
│  │ Indeed      │    │ Score 1-10  │    │ Resume.pdf  │    │ Browser   │ │
│  │ LinkedIn    │    │ Filter ≥6   │    │ Cover.pdf   │    │ Automation│ │
│  │ ~200 jobs   │    │ ~$0.001/job │    │ ~$0.03/app  │    │ ~$0.01/app│ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └───────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Components

### 1. Job Scraper (`simple_hunter_v2.py`)
- **Library**: JobSpy
- **Sources**: Indeed, LinkedIn
- **Searches**: IT Support, Help Desk, Desktop Support, IT Technician, System Administrator, Network Technician
- **Locations**: Anaheim CA, Irvine CA, Orange County CA
- **Filter**: Jobs posted in last 72 hours
- **Output**: Writes to queue + triggers n8n

### 2. AI Scorer (`scorer.py`)
- **Model**: Claude Haiku ($0.25/1M tokens)
- **Input**: Job title, company, description, location
- **Output**: Score 1-10, YES/MAYBE/NO recommendation
- **Uses**: Comprehensive candidate profile with work history
- **Filter**: Only score ≥6 proceeds to PDF generation

### 3. PDF Generator (n8n workflow)
- **Model**: Claude Opus 4.5 (highest quality)
- **Generates**: Tailored resume + cover letter HTML
- **Converter**: Gotenberg (HTML → PDF)
- **Naming**: `Company_AppNumber_Resume.pdf`
- **Parallel**: Resume + Cover generated simultaneously

### 4. Queue System
```
/root/job_bot/queue/
├── pending.json    # Jobs ready for auto-apply
├── applied.json    # Successfully submitted
├── failed.json     # Errors - retry later
└── manual.json     # Needs human (LinkedIn, CAPTCHA)
```

### 5. AI Browser Agent (`ai_applier.py`)
- **Vision Model**: Gemini 2.0 Flash via OpenRouter
- **Fallback**: Gemini 2.5 Flash when stuck
- **Browser**: Playwright (headless Chrome)
- **Features**:
  - Screenshot → AI decides action → Execute → Verify
  - Self-correcting loop (checks if page changed)
  - Separate cookie sessions for Indeed/LinkedIn
  - CapSolver integration for Cloudflare Turnstile
  - Human-like delays between actions

---

## 💰 Cost Breakdown (500 apps/month)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Haiku Scoring | 1500 jobs × $0.001 | $1.50 |
| Opus PDF Gen | 500 apps × $0.03 | $15.00 |
| Gemini Browser AI | 500 apps × $0.01 | $5.00 |
| CapSolver | 500 solves × $0.002 | $1.00 |
| Hetzner VPS | 2GB RAM | $4.00 |
| **TOTAL** | | **~$27/month** |

**ROI**: One job offer = months of salary. Investment: ~$50 total.

---

## 🔑 API Keys (`.env`)
```env
ANTHROPIC_API_KEY=sk-ant-...     # Haiku + Opus
OPENROUTER_API_KEY=sk-or-...     # Gemini 2.0/2.5 Flash
CAPSOLVER_API_KEY=CAP-...        # Cloudflare bypass
DEEPSEEK_API_KEY=sk-...          # Backup (optional)
```

---

## 📁 File Structure
```
/root/job_bot/
├── agent/
│   ├── simple_hunter_v2.py    # Scraper + Haiku scoring
│   ├── scorer.py              # Scoring logic + profile
│   ├── ai_applier.py          # Gemini browser agent
│   ├── indeed_applier.py      # Original rule-based (backup)
│   ├── cookies.json           # Indeed session
│   ├── cookies2.json          # LinkedIn session
│   ├── .env                   # API keys
│   ├── .app_counter.json      # Application numbering
│   └── venv/                  # Python environment
├── queue/
│   ├── pending.json
│   ├── applied.json
│   ├── failed.json
│   └── manual.json
├── output/                    # Generated PDFs
├── screenshots/               # Debug screenshots
├── logs/
│   └── hunter.log
└── infrastructure/
    └── docker-compose.yml     # n8n + Gotenberg + file server
```

---

## 🚀 Usage

### Start Services
```bash
cd /root/job_bot/infrastructure
docker-compose up -d
```

### Run Scraper (Find + Score + Generate PDFs)
```bash
cd /root/job_bot/agent
source venv/bin/activate
python simple_hunter_v2.py           # Single run
python simple_hunter_v2.py --loop    # Continuous (every 4 hrs)
```

### Run AI Applier
```bash
python ai_applier.py --max 5         # Apply to 5 jobs
python ai_applier.py --max 10        # Apply to 10 jobs
```

### Check Queues
```bash
cat /root/job_bot/queue/pending.json | python -m json.tool
cat /root/job_bot/queue/applied.json | python -m json.tool
cat /root/job_bot/queue/manual.json | python -m json.tool
```

### View Generated PDFs
http://5.161.45.43:8080

### View n8n Workflow
http://5.161.45.43:5678

---

## 🐛 Known Issues

| Issue | Cause | Status |
|-------|-------|--------|
| LinkedIn blocks automation | Datacenter IP detected | Move to manual queue |
| Indeed Cloudflare challenge | Bot detection | CapSolver + retry |
| Cookies expire | Session timeout | Re-export from browser |
| AI gives empty response | API rate limit | Check OpenRouter balance |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Scraping | JobSpy (Python) |
| Job Scoring | Claude Haiku |
| Document Generation | Claude Opus 4.5 |
| PDF Conversion | Gotenberg |
| Browser AI | Gemini 2.0 Flash (OpenRouter) |
| Browser Automation | Playwright |
| CAPTCHA Solving | CapSolver |
| Workflow Engine | n8n |
| File Server | Static File Server |
| Hosting | Hetzner VPS (Ashburn, VA) |

---

## 📈 Metrics

- **Jobs Scraped per Run**: ~200
- **Pass Haiku Filter**: ~15-30 (score ≥6)
- **PDFs Generated**: ~15-30 per run
- **Auto-Apply Success Rate**: TBD (Indeed working, LinkedIn blocked)

---

## 🗓️ Development Timeline

| Date | Milestone |
|------|-----------|
| Dec 10 | Server setup, n8n deployment |
| Dec 11 | JobSpy scraper, basic PDF generation |
| Dec 12 | Claude Opus 4.5 integration, parallel generation |
| Dec 13 | Haiku scoring, comprehensive profile |
| Dec 14 | Queue system, application numbering |
| Dec 15 | AI browser agent (Gemini), OpenRouter, CapSolver |

---

## 🔮 Roadmap

- [x] Core scraping pipeline
- [x] AI job scoring (Haiku)
- [x] Quality PDF generation (Opus)
- [x] Queue management system
- [x] AI browser agent (Gemini)
- [ ] Solve Indeed Cloudflare reliably
- [ ] Residential proxy for LinkedIn
- [ ] Discord notifications
- [ ] Auto cookie refresh
- [ ] Response/interview tracking
- [ ] A/B test resume formats
- [ ] GitHub stats badge

---

## 👨‍💻 Author

Brandon Ruiz - Built with Claude AI assistance

December 2024
