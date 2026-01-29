# 🚀 DEPLOYMENT GUIDE
## Complete Setup for Job Application Agent

---

## PHASE 1: Fix Your Existing n8n (10 minutes)

Your n8n is at: `http://5.161.45.43:5678`

### Step 1: Import the New Workflow

1. Open n8n dashboard
2. Click **Workflows** → **Import from File**
3. Upload `infrastructure/n8n-workflow.json` (from this package)
4. You'll see a workflow with ~12 nodes

### Step 2: Connect Your DeepSeek Credential

1. Double-click **Resume Writer** node
2. Under Authentication → Credential → Click the dropdown
3. Select your existing "DeepSeek API" credential
4. Close
5. Do the same for **Cover Letter Writer** node

### Step 3: Activate & Test

1. Toggle workflow to **Active** (green)
2. Run this test from your server terminal:

```bash
curl -X POST http://localhost:5678/webhook/incoming-job \
  -H "Content-Type: application/json" \
  -d '{
    "title": "IT Support Specialist",
    "company": "TestCompany",
    "description": "Looking for IT support with Active Directory, firewall management, and Windows Server experience.",
    "url": "https://indeed.com/test",
    "location": "Long Beach, CA"
  }'
```

3. Check `http://5.161.45.43:8080` - you should see:
   - `TestCompany_1_Resume.pdf`
   - `TestCompany_1_CoverLetter.pdf`

---

## PHASE 2: Install the Job Hunter (15 minutes)

### Step 1: SSH into your server

```bash
ssh root@5.161.45.43
```

### Step 2: Create project structure

```bash
cd ~
mkdir -p job_bot/agent
mkdir -p job_bot/output
mkdir -p job_bot/logs
chmod 777 job_bot/output
```

### Step 3: Upload the agent files

From your LOCAL computer (not the server), upload the files:

```bash
# From the directory containing this package
scp agent/simple_hunter.py root@5.161.45.43:~/job_bot/agent/
scp agent/requirements.txt root@5.161.45.43:~/job_bot/agent/
```

### Step 4: Install Python dependencies

Back on the server:

```bash
cd ~/job_bot/agent
apt update
apt install python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Create environment file

```bash
cat > ~/job_bot/.env << 'EOF'
DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE
N8N_WEBHOOK_URL=http://localhost:5678/webhook/incoming-job
EOF
```

### Step 6: Test the hunter

```bash
cd ~/job_bot/agent
source venv/bin/activate
export $(cat ../.env | xargs)
python simple_hunter.py
```

Watch the output - it should:
1. Search Indeed for jobs
2. Send each to n8n
3. Report the generated PDFs

---

## PHASE 3: Set Up Auto-Run (5 minutes)

### Option A: Run manually when you want

```bash
cd ~/job_bot/agent
source venv/bin/activate
export $(cat ../.env | xargs)
python simple_hunter.py
```

### Option B: Run every hour automatically

```bash
# Create cron job
crontab -e

# Add this line (runs every hour):
0 * * * * cd /root/job_bot/agent && /root/job_bot/agent/venv/bin/python simple_hunter.py >> /root/job_bot/logs/cron.log 2>&1
```

---

## PHASE 4: GitHub Portfolio (10 minutes)

### Step 1: Create GitHub repo

1. Go to github.com → New Repository
2. Name: `job-agent`
3. Make it PUBLIC (this is the point!)
4. Don't initialize with README

### Step 2: Initialize local repo on server

```bash
cd ~/job_bot
git init
git remote add origin https://github.com/YOUR_USERNAME/job-agent.git
```

### Step 3: Upload the update script

```bash
scp scripts/update_github.sh root@5.161.45.43:~/job_bot/
chmod +x ~/job_bot/update_github.sh
```

### Step 4: Configure Git credentials

```bash
git config --global user.email "brandonlruiz98@gmail.com"
git config --global user.name "Brandon Ruiz"

# For pushing, you'll need a Personal Access Token
# Go to: GitHub → Settings → Developer Settings → Personal Access Tokens → Generate
# Store it:
git config --global credential.helper store
```

### Step 5: First push

```bash
cd ~/job_bot
./update_github.sh
```

### Step 6: Auto-update nightly

```bash
crontab -e

# Add this line (runs at 4 AM daily):
0 4 * * * /root/job_bot/update_github.sh >> /root/job_bot/logs/github.log 2>&1
```

---

## 📋 DAILY WORKFLOW

1. **Morning**: Hunter has run overnight, check `http://5.161.45.43:8080` for new PDFs
2. **Apply**: Open each PDF, see the job URL in the log, upload manually
3. **Evening**: Check GitHub for updated stats
4. **Repeat**: System runs while you sleep

---

## 🔧 TROUBLESHOOTING

### "Workflow not found" error
→ Make sure workflow is set to **Active** in n8n

### No PDFs generated
→ Check n8n Executions tab for errors
→ Verify DeepSeek API key is correct
→ Check DeepSeek balance (needs ~$5 credit)

### jobspy errors
→ Indeed/LinkedIn may be blocking
→ Try running less frequently
→ Consider VPN or rotating proxies

### Permission denied on output
```bash
chmod 777 ~/job_bot/output
chown -R 1000:1000 ~/job_bot/output
```

---

## 💰 COST ESTIMATE

| Service | Monthly Cost |
|---------|-------------|
| Hetzner VPS | ~$5 |
| DeepSeek API (heavy use) | ~$2-5 |
| **Total** | **~$7-10/month** |

For 100 applications/day = ~$0.003 per application

---

## 🎯 SUCCESS METRICS

After 30 days, you should have:
- 500-1000+ applications sent
- Response rate data
- A public GitHub repo showing the project
- Interview talking points about automation

Good luck! 🚀
