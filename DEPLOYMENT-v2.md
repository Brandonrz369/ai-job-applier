# 🚀 COMPLETE DEPLOYMENT GUIDE v2
## Building on Your Existing n8n Setup

**You already have working:**
- ✅ n8n at http://5.161.45.43:5678
- ✅ Gotenberg PDF printer
- ✅ File server at http://5.161.45.43:8080
- ✅ DeepSeek API credential
- ✅ Output folder with permissions fixed

**This guide ADDS:**
- Full resume + cover letter generation (complete documents)
- Dynamic filenames with application counter
- The "You are employer #X" hook
- Browser Use for auto-submission
- Self-improvement tracking
- GitHub auto-updates

---

## PHASE 1: Upgrade Your n8n Workflow (5 minutes)

You're NOT starting over. You're importing an upgraded workflow.

### Step 1: Import the New Workflow

1. Go to http://5.161.45.43:5678
2. Click **Workflows** → **+ Add Workflow** → **Import from File**
3. Upload `infrastructure/n8n-workflow-v3.json`
4. You'll see a workflow with 12 nodes

### Step 2: Connect Your Existing Credential

The new workflow has placeholder credential IDs. You need to link your existing DeepSeek credential:

1. Double-click **Resume Writer** node
2. Under Authentication → Credential → Click dropdown
3. Select your existing **"DeepSeek API"** credential
4. Close
5. Repeat for **Cover Letter Writer** node

### Step 3: Activate & Test

1. Toggle workflow to **Active** (green switch, top right)
2. SSH into your server and run:

```bash
ssh root@5.161.45.43

curl -X POST http://localhost:5678/webhook/incoming-job \
  -H "Content-Type: application/json" \
  -d '{
    "title": "IT Support Specialist",
    "company": "TestCompany",
    "description": "Looking for IT professional with Active Directory experience, firewall management (FortiGate preferred), and backup administration (Veeam). Must have strong customer service skills and Windows Server experience.",
    "url": "https://indeed.com/viewjob?id=test123",
    "location": "Anaheim, CA"
  }'
```

3. Check http://5.161.45.43:8080 - you should see:
   - `TestCompany_1_Resume.pdf` (COMPLETE resume, not just summary)
   - `TestCompany_1_CoverLetter.pdf` (with "employer #1" line)

### What Changed in the New Workflow

| Old Workflow | New Workflow |
|--------------|--------------|
| Generated summary only | Generates COMPLETE resume with all experience |
| Single DeepSeek call | Two parallel calls (resume + cover letter) |
| Static filename | Dynamic: `{Company}_{AppNumber}_Resume.pdf` |
| No counter | Application counter tracks #1, #2, #3... |
| No tracking | Logs to CSV + creates manifest for Browser Use |
| No meta-play | Cover letter includes "You are employer #X" |

---

## PHASE 2: Install the Complete Agent (15 minutes)

### Step 1: Upload Agent Files

From your LOCAL computer:

```bash
# Navigate to where you extracted the zip
cd job-agent

# Upload agent files
scp agent/complete_agent.py root@5.161.45.43:~/job_bot/agent/
scp agent/requirements.txt root@5.161.45.43:~/job_bot/agent/
```

### Step 2: Install Dependencies

SSH into server:

```bash
ssh root@5.161.45.43
cd ~/job_bot/agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install base requirements
pip install requests pandas python-jobspy python-dotenv

# For FULL auto-submission (optional but recommended):
pip install browser-use langchain-openai playwright
playwright install chromium
```

### Step 3: Configure Environment

```bash
cat > ~/job_bot/.env << 'EOF'
DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE
N8N_WEBHOOK_URL=http://localhost:5678/webhook/incoming-job
TARGET_LOCATION=Anaheim, CA
REMOTE_RATIO=0.25
OUTPUT_DIR=/root/job_bot/output
LOGS_DIR=/root/job_bot/logs
EOF
```

### Step 4: Test the Agent

```bash
cd ~/job_bot/agent
source venv/bin/activate
export $(cat ../.env | xargs)

# Run single test cycle
python complete_agent.py --once
```

You should see:
- Jobs being scraped from Indeed
- Each sent to n8n
- PDFs appearing in output folder
- (If Browser Use installed) Applications being submitted

---

## PHASE 3: Choose Your Mode

### Mode A: Semi-Automatic (Recommended to Start)

Agent scrapes jobs and generates PDFs. YOU manually submit.

```bash
# Run when you want
python complete_agent.py --once
```

Then:
1. Check http://5.161.45.43:8080 for new PDFs
2. Open the applications.csv to see job URLs
3. Go to each URL and upload the matching PDF

**Why start here:** Browser Use can be flaky. Indeed/LinkedIn fight automation. This mode guarantees you get tailored documents without risk of getting blocked.

### Mode B: Fully Automatic

Agent scrapes, generates, AND submits applications autonomously.

Requires Browser Use to be installed and working.

```bash
# Run continuously
python complete_agent.py
```

The agent will:
1. Search for jobs
2. Filter by 75/25 ratio
3. Send to n8n for document generation
4. Pick up the PDFs
5. Navigate to job posting
6. Fill out application form
7. Upload resume + cover letter
8. Click submit
9. Log the result
10. Move to next job

**Warning:** Indeed/LinkedIn may block automated submissions. The agent handles CAPTCHAs by marking them as "BLOCKED" and moving on.

### Mode C: Hybrid (Best of Both)

Run the agent to scrape and generate, but only auto-submit to "easy" targets:

Edit `complete_agent.py` and modify the `ApplicationSubmitter.submit()` method to only attempt submission for certain sites (like LinkedIn Easy Apply).

---

## PHASE 4: The Self-Improvement System

The agent tracks what works and adjusts over time.

### What It Tracks

- `output/.counter.json` - Total applications, remote/local split
- `output/.feedback.json` - Keywords from successful applications
- `output/applications.csv` - Full history

### Recording Responses (Manual Step)

When you get a response (email, call), run:

```bash
python -c "
from complete_agent import StatsTracker
stats = StatsTracker()
stats.record_response('https://indeed.com/job/xxx', 'interview')  # or 'response'
"
```

### Viewing Insights

```bash
python complete_agent.py --report
```

After 50+ applications, you'll get insights like:
- "Remote positions performing better. Consider increasing REMOTE_RATIO"
- "Low response rate. Consider more specific job titles"

---

## PHASE 5: GitHub Portfolio Auto-Updates

### Step 1: Create GitHub Repo

1. Go to github.com → New Repository
2. Name: `job-agent`
3. Make it **PUBLIC**
4. Don't initialize with README

### Step 2: Initialize on Server

```bash
cd ~/job_bot
git init
git remote add origin https://github.com/YOUR_USERNAME/job-agent.git

# Configure git
git config --global user.email "brandonlruiz98@gmail.com"
git config --global user.name "Brandon Ruiz"
```

### Step 3: Get a Personal Access Token

1. GitHub → Settings → Developer Settings → Personal Access Tokens → Generate
2. Give it `repo` permissions
3. Save the token

### Step 4: Upload Update Script

```bash
scp scripts/update_github.sh root@5.161.45.43:~/job_bot/
chmod +x ~/job_bot/update_github.sh
```

### Step 5: Run First Update

```bash
cd ~/job_bot
./update_github.sh
```

Enter your token when prompted for password.

### Step 6: Schedule Nightly Updates

```bash
crontab -e

# Add this line (4 AM daily):
0 4 * * * /root/job_bot/update_github.sh >> /root/job_bot/logs/github.log 2>&1
```

---

## 📊 Complete Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        YOUR HETZNER VPS                                  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    complete_agent.py                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │    │
│  │  │  JobScraper  │  │ StatsTracker │  │ ApplicationSubmitter │   │    │
│  │  │  (jobspy)    │  │ (75/25 ratio)│  │    (Browser Use)     │   │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │    │
│  │         │                 │                      │               │    │
│  │         ▼                 │                      │               │    │
│  │  ┌──────────────┐         │                      │               │    │
│  │  │DocumentFactory├────────┴──────────────────────┘               │    │
│  │  │  (HTTP POST) │                                                │    │
│  │  └──────┬───────┘                                                │    │
│  └─────────┼────────────────────────────────────────────────────────┘    │
│            │                                                             │
│            ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         n8n                                      │    │
│  │  Webhook → Counter → Resume Writer ──┐                          │    │
│  │                    → Cover Writer ───┼→ Prepare → PDF → Save    │    │
│  │                                      │         ↓                 │    │
│  │                               DeepSeek API   Gotenberg          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│            ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                       /output/                                   │    │
│  │  ├── TestCompany_1_Resume.pdf                                   │    │
│  │  ├── TestCompany_1_CoverLetter.pdf                              │    │
│  │  ├── applications.csv (full log)                                │    │
│  │  ├── .counter.json (stats)                                      │    │
│  │  └── .pending_submissions.json (queue for Browser Use)          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│            │                                                             │
│            │  (Browser Use picks up PDFs and submits)                   │
│            ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Indeed / LinkedIn                             │    │
│  │                    (Applications submitted)                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 💰 Total Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Hetzner VPS | ~$5 |
| DeepSeek API | ~$3-5 (heavy use) |
| **Total** | **~$8-10/month** |

Cost per application: ~$0.003 - $0.005

---

## 🎯 Success Checklist

After setup, verify:

- [ ] n8n workflow generates COMPLETE resume (all sections)
- [ ] Cover letter includes "employer #X" line
- [ ] Counter increments with each application
- [ ] Files save with dynamic names (Company_X_Resume.pdf)
- [ ] Agent scrapes jobs without errors
- [ ] 75/25 ratio is being enforced
- [ ] (Optional) Browser Use submits applications
- [ ] GitHub repo updates automatically

---

## 🐛 Troubleshooting

### "Workflow not found" when testing
→ Workflow not activated. Toggle to Active.

### Resume only shows summary, not full experience
→ You imported the old workflow. Use `n8n-workflow-v3.json`

### Browser Use errors
→ Try running without it first (agent still generates PDFs)
→ Check `playwright install chromium` ran successfully

### Rate limited by Indeed/LinkedIn
→ Increase `DELAY_BETWEEN_SCRAPES` in config
→ Use VPN or wait 24 hours

### DeepSeek "insufficient balance"
→ Add credit at platform.deepseek.com

---

Good luck! 🚀
