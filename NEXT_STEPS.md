# NEXT STEPS: Job Bot Recovery Plan

## Where We Left Off

The Gemini chat ended mid-sentence. The user said:
> "its only 10 accoutns and do"

Gemini had just provided a "final" version of `setup_google_accounts.sh` but:
1. It was still hardcoded to 12 accounts (user has 10)
2. User was about to point this out
3. Chat died before correction was made

---

## Current Blockers (In Order of Priority)

### BLOCKER 1: `setup_google_accounts.sh` Not Updated
**Status:** CRITICAL - Nothing works until this is fixed  
**Location:** `/root/job_bot/setup_google_accounts.sh`

**Current File Contains (WRONG):**
```bash
BRIGHT_USER="brd-customer-hl_1ee7d566-zone-auth_rotator"
BRIGHT_PASS="v5yc4br8b2bf"
PROXY_HOST="brd.superproxy.io:33335"
export NODE_TLS_REJECT_UNAUTHORIZED=0
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
for i in {1..12}; do  # <-- WRONG: Should be 10
```

**Needs To Be Replaced With:**
```bash
#!/bin/bash
ACCOUNTS_FILE="/root/job_bot/config/google_accounts.json"
MAX_ACCOUNTS=10  # <-- CORRECT: 10 accounts
SLEEP_TIME=10

# NO PROXY VARIABLES

for ((i=0; i<$MAX_ACCOUNTS; i++)); do
    EMAIL=$(jq -r ".[$i].email" $ACCOUNTS_FILE)
    PASSWORD=$(jq -r ".[$i].password" $ACCOUNTS_FILE)
    
    opencode auth login \
        --email "$EMAIL" \
        --password "$PASSWORD" \
        --browser "headless" \
        --save-session
    
    sleep $SLEEP_TIME
done
```

---

### BLOCKER 2: File Location Mismatch
**Status:** HIGH - Script won't find credentials

The script expects: `/root/job_bot/config/google_accounts.json`  
User created file at: `/root/job_bot/bot/accounts.json`

**Action Required:**
```bash
mkdir -p /root/job_bot/config
mv /root/job_bot/bot/accounts.json /root/job_bot/config/google_accounts.json
```

---

### BLOCKER 3: jq May Not Be Installed
**Status:** MEDIUM - Script will fail on first line

**Check:**
```bash
command -v jq
```

**Install if missing:**
```bash
apt install jq -y
```

---

### BLOCKER 4: JSON Field Name Mismatch
**Status:** MEDIUM - Script expects "password", JSON may have "pass"

Gemini's script uses: `jq -r ".[$i].password"`  
Earlier JSON examples used: `"pass": "value"`

**Verify the actual field name in the JSON file and update either the script or the JSON to match.**

---

## What Is NOT Broken (Already Done)

| Item | Status | Notes |
|------|--------|-------|
| `accounts.json` created | ✅ Done | Contains 10 personal accounts |
| OpenCode installed | ✅ Done | CLI tool is available |
| Bright Data account | ✅ Done | Credentials exist (for later use) |
| Architecture decision | ✅ Done | Two-layer system defined |

---

## Immediate Action Checklist

```
[ ] 1. Verify accounts.json exists and has correct format
      Command: cat /root/job_bot/bot/accounts.json | jq .

[ ] 2. Move accounts.json to correct location
      Command: mkdir -p /root/job_bot/config && mv /root/job_bot/bot/accounts.json /root/job_bot/config/google_accounts.json

[ ] 3. Install jq if missing
      Command: apt install jq -y

[ ] 4. Backup old setup script
      Command: cp /root/job_bot/setup_google_accounts.sh /root/job_bot/setup_google_accounts.sh.bak

[ ] 5. Rewrite setup_google_accounts.sh (see corrected version above)

[ ] 6. Make script executable
      Command: chmod +x /root/job_bot/setup_google_accounts.sh

[ ] 7. Unset any lingering proxy variables
      Command: unset HTTP_PROXY HTTPS_PROXY

[ ] 8. Run the auth script
      Command: cd /root/job_bot && ./setup_google_accounts.sh

[ ] 9. Verify success for all 10 accounts
```

---

## After Layer 1 Is Complete

Once all 10 accounts are authenticated, the next phase is:

### Phase 2A: Create proxies.json
```bash
cat > /root/job_bot/config/proxies.json << 'EOF'
[
  {
    "protocol": "http",
    "host": "YOUR_PROXY_HOST",
    "port": "YOUR_PORT",
    "username": "YOUR_USER",
    "password": "YOUR_PASS"
  }
]
EOF
```

### Phase 2B: Build the Bot
```bash
opencode run @MIGRATION_BLUEPRINT.md "The accounts are authenticated. Write the smart_applier.py script now."
```

### Phase 2C: Implement Proxy Switching in Bot Code
The bot needs logic to:
- Use LOCAL IP for Google API calls
- Use PROXY for Indeed/LinkedIn requests
- Rotate proxies per application

---

## Open Questions (Need User Input)

1. **What is the exact field name in your JSON?** (`password` or `pass`)
2. **Does the opencode CLI actually support `--email`, `--password`, `--browser`, `--save-session` flags?** (Gemini assumed this but never verified)
3. **Do you have residential proxies ready for Layer 2?** Or do you need to complete Bright Data KYC first?
4. **Is MIGRATION_BLUEPRINT.md a real file?** Or was it a placeholder Gemini referenced?

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Google flags personal accounts | Low | HIGH | Use safety sleep, space out logins |
| opencode flags don't exist as expected | Medium | HIGH | Test manually first with 1 account |
| JSON parsing fails | Medium | LOW | Verify JSON format before running |
| Bright Data KYC blocks Layer 2 | High | MEDIUM | Find alternative proxy provider |

---

## Recovery Commands (Copy-Paste Ready)

### Full Reset Sequence
```bash
# 1. Kill any running processes
pkill -f opencode

# 2. Clear old auth cache
rm -rf ~/.config/opencode/auth.json
opencode auth logout 2>/dev/null

# 3. Unset proxy variables
unset HTTP_PROXY HTTPS_PROXY NODE_TLS_REJECT_UNAUTHORIZED

# 4. Verify clean environment
env | grep -i proxy  # Should return nothing

# 5. Check file locations
ls -la /root/job_bot/
ls -la /root/job_bot/config/
ls -la /root/job_bot/bot/
```

---

## Summary

**You are stuck at:** Layer 1 Authentication (Step 0 of the build)  
**Reason:** setup_google_accounts.sh has wrong code  
**Fix:** Rewrite the script to remove proxy config and read from JSON  
**Time to fix:** ~10 minutes  
**Next milestone:** See "✅ Account #10 configured" in terminal output
