# Job Agent: Intelligent Application Automation Pipeline

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![n8n](https://img.shields.io/badge/Workflow-n8n-FF6D5A?style=for-the-badge&logo=n8n)
![Gemini](https://img.shields.io/badge/AI-Gemini-4285F4?style=for-the-badge&logo=google)
![Status](https://img.shields.io/badge/Status-Production-success?style=for-the-badge)

> **A scalable, full-cycle automation pipeline that scrapes, analyzes, and applies to job listings autonomously.**

This project demonstrates the application of complex workflow orchestration, large language models (LLMs) for decision-making, and cloud browser automation to solve a high-friction real-world problem: the time-intensive nature of job hunting.

---

## Business Value & Metrics

While technically complex, the primary goal of this system is **Operational ROI**. By automating the sourcing, qualification, and documentation phases of job applications, the system frees up human capital to focus solely on interview preparation and networking.

| Metric | Current Performance | Impact |
| :--- | :--- | :--- |
| **Throughput** | **454** Jobs Processed | Equivalent to ~100+ hours of manual sourcing |
| **Conversion** | **17%** Success Rate | Automated application submission rate |
| **Cost Efficiency** | < $0.15 per app | Drastic reduction compared to manual effort |
| **Latency** | ~2 mins per full cycle | From discovery to tailored application |

---

## Architecture & Tech Stack

The system is built on a modular architecture separating ingestion, cognitive processing, and execution.

### 1. Ingestion Layer (Sourcing)
- **Library:** `JobSpy` (Python)
- **Function:** Aggregates listings from Indeed and LinkedIn across 44 search terms.
- **Resilience:** Parallel scraping (3 concurrent), deduplication, 75/25 local/remote ratio enforcement.

### 2. Cognitive Layer (Decision & Generation)
- **Orchestration:** `n8n` workflow automation.
- **Scoring Engine (Gemini 2.5 Flash):** Analyzes job descriptions against a comprehensive candidate profile to generate a suitability score (1-10). Jobs scoring below 6 are filtered out. Enforces $60K salary floor.
- **Document Factory (Gemini + Gotenberg):** For qualifying roles, generates a context-aware resume and cover letter tailored to the job description, converted to ATS-friendly PDFs.

### 3. Execution Layer (Delivery)
- **Cloud Browser:** `Browser-Use Cloud` manages cloud browser sessions with US residential proxies for anti-detection.
- **Form Intelligence:** JS-based form injection (React/Vue-aware) fills entire forms in a single step.
- **CAPTCHA Solving:** CapSolver integration handles hCaptcha, Cloudflare Turnstile, and reCAPTCHA v2 automatically.
- **Rescue System:** Tiered Gemini AI rescue when agent gets stuck (Flash for fast fixes, Gemini 3 Pro with 4K thinking for deep analysis).

---

## Workflow Logic

```
+-------------------+
|  JobSpy Scraper   |
+--------+----------+
         | Raw Listings (44 search terms, 3 regions)
         v
+-------------------+
| Duplicate Check   |
+--------+----------+
         | New Lead
         v
+-------------------+     Score < 6     +---------+
| Gemini 2.5 Flash  |----------------->| Discard |
| (Job Scoring)     |                  +---------+
+--------+----------+
         | Score >= 6
         v
+-------------------+
| n8n + Gemini      |
| (Doc Generation)  |
+--------+----------+
         | Tailored Resume + Cover Letter
         v
+-------------------+
| Gotenberg PDF     |
+--------+----------+
         | PDF Assets
         v
+-------------------+
| Queue Manager     |
+--------+----------+
         | Pending
         v
+-------------------+
| Browser-Use Cloud |--+--> Success --> Log: Applied
| + Gemini Rescue   |  |
+-------------------+  +--> External ATS --> Log: External
                       |
                       +--> Fail --> Log: Failed / Manual Review
```

## Key Features

### Intelligent Queue Management
The system maintains a state machine for every job:
- `PENDING`: Scraped, scored, and documented. Awaiting browser slot.
- `APPLIED`: Successfully submitted.
- `FAILED`: Error in submission (GIF recordings saved for debugging).
- `EXTERNAL`: Redirected to external ATS portal.
- `SKIPPED`: Filtered out by scorer.
- `MANUAL`: Requires human intervention (login walls, complex flows).

### Dynamic Document Tailoring
Unlike simple "mass apply" scripts, this agent treats every application as unique.
* **Resume Optimization:** Reorders bullet points and highlights skills that match the specific JD.
* **Cover Letter Generation:** Writes a cohesive narrative connecting the candidate's history to the company's specific mission.

### Browser-Use Cloud Automation
- Cloud-managed browser with US residential proxy (no local Chrome needed)
- Vision-enabled: screenshot analysis drives decision-making
- JS-based form injection fills entire forms in one step (React/Vue-aware)
- Mandatory validation gate before every Submit/Continue click
- Up to 50 steps per application with GIF session recording

### Tiered AI Rescue System
When the browser agent gets stuck (3-strike detection):
- **Tier 1:** Gemini 2.5 Flash - fast tactical fix (no thinking)
- **Tier 2:** Gemini 3 Pro Preview - deep analysis with 4K thinking budget
- **WAF Detection:** Auto-identifies Indeed bot protection and aborts gracefully

### CAPTCHA Solving
Automatic solving via CapSolver API:
- hCaptcha
- Cloudflare Turnstile
- reCAPTCHA v2

### Anti-Detection Strategies
- US residential proxy via Browser-Use Cloud
- Human-like typing delays and form interaction patterns
- React/Vue event dispatching after form changes
- Randomized sleep intervals between actions

---

## Installation & Usage

*Note: This project requires API keys for Google Gemini, Browser-Use, CapSolver, and a local/cloud instance of n8n + Gotenberg.*

1. **Clone the repository**
   ```bash
   git clone https://github.com/brandonrz369/job-agent.git
   ```

2. **Set up Environment**
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Add your API keys (GEMINI_API_KEY, BROWSER_USE_API_KEY, CAPSOLVER_API_KEY)
   ```

3. **Start Infrastructure**
   ```bash
   cd infrastructure
   docker-compose up -d  # n8n + Gotenberg + file server
   ```

4. **Run the Scraper**
   ```bash
   python3 agent/simple_hunter.py --max 10
   ```

5. **Run the Applier**
   ```bash
   python3 bot/applier.py --max 5
   ```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Job Scraping | JobSpy (Python, parallel threads) |
| Job Scoring | Gemini 2.5 Flash (Google AI) |
| Document Generation | Gemini + Gotenberg (via n8n) |
| Browser Automation | Browser-Use Cloud (US residential proxy) |
| Form Intelligence | Custom JS injection (React/Vue-aware) |
| CAPTCHA Solving | CapSolver (hCaptcha, Turnstile, reCAPTCHA v2) |
| AI Rescue | Gemini 2.5 Flash (Tier 1) + Gemini 3 Pro (Tier 2) |
| Workflow Engine | n8n (self-hosted) |
| PDF Conversion | Gotenberg (containerized) |
| Hosting | Hetzner VPS |

---

## Future Improvements

- **Webhooks Integration:** Slack/Discord notifications upon successful application or interview request detection.
- **Interview Prep:** Using gathered job data to generate mock interview questions.
- **Feedback Loop:** Parsing rejection emails to adjust scoring weights automatically.
- **A/B Testing:** Test different resume formats and measure response rates.

---

### Author

**Brandon Ruiz**
*Infrastructure Engineer & Automation Developer*

[GitHub](https://github.com/brandonrz369)
