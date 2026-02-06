# Bright Data Browser API
BROWSER_WS = "wss://REDACTED_BRIGHTDATA_CREDENTIALS:REDACTED_PASSWORD@brd.superproxy.io:9222"

# Models
MODEL_FAST = "google/gemini-2.0-flash-001"
MODEL_SMART = "google/gemini-2.5-flash-preview"

# Candidate Profile
CANDIDATE = {
    "name": "Brandon Ruiz",
    "email": "brandonlruiz98@gmail.com",
    "phone": "(213) 349-6790",
    "location": "Anaheim, CA",
    "summary": "IT Support professional with 6+ years experience in help desk, desktop support, Windows/Linux administration, networking, and customer service."
}

# Paths
ACCOUNTS_FILE = "/root/job_bot/agent/accounts.json"
PENDING_FILE = "/root/job_bot/queue/pending.json"
APPLIED_FILE = "/root/job_bot/queue/applied.json"
FAILED_FILE = "/root/job_bot/queue/failed.json"
