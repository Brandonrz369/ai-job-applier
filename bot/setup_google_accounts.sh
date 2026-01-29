#!/bin/bash
# setup_google_accounts.sh
# Automates the 12-account rotation setup using RESIDENTIAL PROXY

# --- YOUR CREDENTIALS ---
BRIGHT_USER="brd-customer-hl_1ee7d566-zone-auth_rotator"
BRIGHT_PASS="v5yc4br8b2bf"
PROXY_HOST="brd.superproxy.io:33335"

# --- THE FIX: DISABLE SSL VERIFICATION ---
# This stops the "self signed certificate" error caused by the proxy
export NODE_TLS_REJECT_UNAUTHORIZED=0

echo "🤖 INITIALIZING ARCHITECT LAYER (SSL Verification Disabled)"
echo "---------------------------------------------------"

for i in {1..12}; do
    SESSION_ID=$RANDOM
    PROXY_URL="http://${BRIGHT_USER}-session-${SESSION_ID}:${BRIGHT_PASS}@${PROXY_HOST}"
    
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    
    echo "🔄 Account #$i: New IP Generated (Session: $SESSION_ID)"
    
    # Launch Auth (Select Google -> Login -> EXIT)
    opencode auth login
    
    unset HTTP_PROXY
    unset HTTPS_PROXY
    
    echo "✅ Account #$i configured."
    echo "---------------------------------------------------"
    sleep 3
done

echo "🎉 All 12 Accounts Configured!"
