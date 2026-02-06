# Job Bot Project - JUMPSTART FILE
## Last Updated: February 4, 2026
## Purpose: Resume work after any interruption - just say "view the codebase"

---

## QUICK STATUS DASHBOARD

| System | Status | Notes |
|--------|--------|-------|
| Bot (applier.py) | READY | Cookie fixes applied, stuck detection added |
| Strategic Queue | 150 JOBS | $100k+, OC/keyword match - BOT PRIORITY |
| Easy Apply Queue | 289 JOBS | Full Easy Apply queue for volume |
| High Value Targets | 107 JOBS | $120k+ manual SNIPER applications |
| External Queue | 58 JOBS | External ATS, manual with Simplify |
| n8n Factory | READY | Resume/cover letter generation operational |
| Strategic Plan | v2 ACTIVE | Ownership = Asset, target $125k+ |
| GitHub Portfolio | NEEDS WORK | README drafted, repo needs cleanup |

---

## CURRENT STRATEGY (v2 - Ownership as Asset)

**Philosophy:** MSP ownership is a FILTER, not a liability. Companies that don't value it aren't worth working for.

**Target Salary:** $125k-$135k base (not $80k - that's Tier 2 Help Desk)

**Hybrid Approach:**
- **SHOTGUN (20% effort):** Bot runs Easy Apply for volume/backup
- **SNIPER (80% effort):** Manual applications to $120k+ roles via browser extensions

**Key Target Companies:**
| Company | Location | Role Type | Why They Want You |
|---------|----------|-----------|-------------------|
| Rewst | Remote | Automation Evangelist | Python + MSP lived experience |
| Huntress | Remote | Partner Enablement | Community trust with MSPs |
| Ingram Micro | Irvine (HQ) | Solutions Architect | Sell to people like you |
| Trace3 | Irvine | Solutions Architect | Enterprise consulting |
| Anduril | Costa Mesa | Technical Operations | Defense tech, values hackers |

**Critical Event:** ASCII Edge 2026 - February 25-26, Costa Mesa
- ConnectWise, Pax8, Huntress, Rewst all sponsor
- Network with Channel Chiefs
- This is where $120k+ jobs get filled through relationships

---

## FILE MAP (What Lives Where)

```
/root/job_bot/
├── JUMPSTART.md          # THIS FILE - start here after any crash
├── STRATEGIC_PLAN.md     # Original plan (hide ownership) - DEPRECATED
├── STRATEGIC_PLAN_v2.md  # Active plan (ownership = asset) - USE THIS
├── GITHUB_README.md      # Portfolio README for GitHub repo
│
├── bot/
│   ├── applier.py        # Main application bot (Browser-Use Cloud + Gemini rescue)
│   └── utils.py          # StuckDetectionSystem, cookie health, success detection
│
├── agent/
│   ├── candidate_profile.py  # Brandon's full profile for resume generation
│   ├── storage_state.json    # Indeed session cookies (needs periodic refresh)
│   └── main.py               # Agent entry point
│
├── queue/
│   ├── dry_run.json              # 454 pre-scored jobs (original source)
│   ├── strategic_easy_apply.json # 150 jobs - $100k+, OC/keyword (BOT PRIORITY)
│   ├── easy_apply_queue.json     # 289 jobs - all Easy Apply candidates
│   ├── high_value_targets.json   # 107 jobs - $120k+ for manual SNIPER
│   ├── external_queue.json       # 58 jobs - external ATS sites
│   ├── pending.json              # Jobs with resumes ready
│   ├── applied.json              # Successfully submitted
│   └── failed.json               # Failed (for debugging)
│
├── test_results/         # Individual test run JSONs
│
└── n8n/
    └── workflow.json     # n8n workflow for resume/cover letter generation
```

---

## BOT IMPROVEMENTS APPLIED (This Session)

1. **Cookie sameSite Fix:** Normalized values to exact Playwright format (Strict|Lax|None)
2. **Stuck Detection System:** Detects validation loops after 3 repeated states
3. **Cookie Health Check:** Validates session before starting browser
4. **Success Detection:** Multi-method verification of application submission
5. **Optimized Task Prompt:** Clear operational protocol with validation gates

---

## JOB QUEUE STATUS

### SPLIT COMPLETE (Feb 4, 2026)

| Queue File | Count | Purpose |
|------------|-------|---------|
| `easy_apply_queue.json` | 289 | Bot auto-apply (likely Easy Apply) |
| `strategic_easy_apply.json` | 150 | Bot priority ($100k+, OC/keyword match) |
| `external_queue.json` | 58 | Manual apply (external ATS) |
| `high_value_targets.json` | 107 | Manual SNIPER ($120k+ at big companies) |

### Easy Apply Salary Breakdown
```
$80k+:  210 jobs
$100k+: 157 jobs
$120k+: 89 jobs
```

### High Value Targets Preview
Top companies in high_value_targets.json:
- Amazon/AWS (multiple $200k+ roles)
- Google ($200k Cloud Solutions Architect)
- Anduril ($180k Senior Security Engineer)
- Providence ($190k Senior Data Engineer)

### Strategic Easy Apply Preview (OC-Area, $100k+)
- Western Digital (Irvine) - $200k Principal Engineer
- Turion Space (Irvine) - $195k Security Threat Engineer
- Chipotle (Newport Beach) - $180k Enterprise Architect
- Zoom (Remote) - $175k Partner Solutions Engineer
- Vast (Long Beach) - $170k Staff Product Security Engineer
- Pacific Life (Newport Beach) - $150k Sr Solution Adoption Engineer
- Planet DDS (Irvine) - $150k Senior Product Manager (AI)

### pending.json (11 jobs)
```
Status: STALE - tested jobs 0,1,3,4,5 all failed (expired/external)
Action: Generate fresh batch from strategic_easy_apply.json
```

---

## ACTION ITEMS (Continual Checklist)

### Immediate (This Week)
- [x] Split dry_run.json into Easy Apply vs External piles (DONE - Feb 4)
- [ ] Run bot on strategic_easy_apply.json (150 jobs, $100k+, target: 100+ apps)
- [ ] Register for ASCII Edge (Feb 25-26, Costa Mesa)
- [ ] Update LinkedIn headline: "MSP Founder → Solutions Architect | Python Automation"
- [ ] Clean up GitHub job-agent repo with professional README

### High-Value Manual Applications
- [ ] Ingram Micro (Irvine) - Solutions Architect
- [ ] Trace3 (Irvine) - Solutions Architect
- [ ] Huntress - Partner Enablement (remote)
- [ ] Rewst - Automation Evangelist (remote)
- [ ] Anduril (Costa Mesa) - Technical Operations

### Bot Maintenance
- [ ] Refresh Indeed cookies if bot starts failing auth
- [ ] Check dry_run.json freshness (filter jobs >7 days old)
- [ ] Monitor test_results/ for new failure patterns

### Portfolio
- [ ] Push GITHUB_README.md to actual GitHub repo
- [ ] Add QR code to portfolio linking to GitHub (for ASCII Edge)
- [ ] Record 2-minute Loom demo of bot in action

---

## RESUME POSITIONING

**Title:** Founder & Technical Director (NOT "Owner")

**30-Second Pitch:**
> "I'm a Technical Solutions Architect with a unique background—I founded and ran my own MSP in Orange County, managing the full IT stack for over 130 customers and securing enterprise contracts.
>
> Because I've signed the front AND the back of the check, I have a different perspective than most engineers. I know how to align technical requirements—like multi-vendor firewalls and Python automation—with actual business ROI.
>
> I've decided to move away from the administrative side of business ownership to focus purely on what I do best: designing complex technical solutions and helping clients scale."

**"Why leaving your business?" Answer:**
> "I realized I love the engineering and architecture—building automation, securing infrastructure, solving complex technical challenges. But I found myself spending 60% of my time on invoicing, HR, and client acquisition.
>
> I want to focus 100% on what I do best: designing solutions and automating operations. I'm looking for a role where my business experience is valued, but I can go deep on the technical work rather than running payroll."

---

## INTERVIEW QUESTIONS TO ASK (Filter for Good Employers)

**Green Flags (Ask these):**
1. "How much autonomy does this role have regarding tool selection and process automation?"
2. "How does the technical roadmap align with the company's revenue targets?"
3. "What's your philosophy on senior technical staff making decisions independently?"
4. "Do you have engineers who've built their own tools or automations here?"

**Red Flags (Run away if they say):**
- "We follow the ticket SOP strictly"
- "All decisions go through the manager"
- "We don't really do automation here"
- Seem threatened by your decision-making history

---

## HOW TO RESUME AFTER A CRASH

1. **Start new Claude session**
2. **Say:** "View the codebase and read JUMPSTART.md"
3. **Claude will:** Read this file and understand full context
4. **Then say:** "Continue with [specific task from Action Items above]"

**Key files to read for full context:**
- `/root/job_bot/JUMPSTART.md` (this file)
- `/root/job_bot/STRATEGIC_PLAN_v2.md` (active strategy)
- `/root/job_bot/agent/candidate_profile.py` (Brandon's profile)
- `/root/job_bot/queue/dry_run.json` (job queue)

---

## METRICS TO TRACK

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Bot Success Rate | 17% | 25%+ | With stuck detection fixes |
| Easy Apply Volume | 0 | 200+ | From dry_run split |
| Manual Applications | 0 | 20+ | High-value $120k+ roles |
| Phone Screens | 0 | 5+ | Week 2-4 goal |
| Final Interviews | 0 | 2+ | Week 2-4 goal |

---

## CHANGELOG (Update This Section)

### February 4, 2026
- Created JUMPSTART.md (this file)
- Created STRATEGIC_PLAN_v2.md (ownership = asset approach)
- Created GITHUB_README.md (portfolio README)
- Applied bot fixes: cookie sameSite, stuck detection
- Analyzed 454 jobs in dry_run.json
- Identified $125k+ target salary based on Gemini research
- Identified ASCII Edge networking event (Feb 25-26)
- **SPLIT COMPLETE:** Created 4 queue files:
  - easy_apply_queue.json (289 jobs)
  - strategic_easy_apply.json (150 jobs - $100k+, OC/keyword match)
  - external_queue.json (58 jobs)
  - high_value_targets.json (107 jobs - $120k+ at big companies)

---

*This file is designed to be continually updated. After completing tasks, check them off and add new items as they arise.*
