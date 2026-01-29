#!/bin/bash
ACCOUNTS_FILE="/root/job_bot/config/google_accounts.json"
MAX_ACCOUNTS=10

echo "🤖 INITIALIZING ANTIGRAVITY BRAIN LAYER (Manual Mode)"
echo "---------------------------------------------------"

for ((i=0; i<$MAX_ACCOUNTS; i++)); do
    EMAIL=$(jq -r ".[$i].email" $ACCOUNTS_FILE)
    
    echo "🔄 Account #$((i+1)): Logging in $EMAIL..."
    echo "👉 Please select 'Google' -> 'Antigravity' in the menu."
    
    # Run opencode auth login interactively
    # The user interacts directly with this process
    opencode auth login
    
    if [ $? -eq 0 ]; then
        echo "✅ Account #$((i+1)) finished."
    else
        echo "❌ Account #$((i+1)) exited with error."
    fi
    
    echo "---------------------------------------------------"
    echo "✅ Done. Press Enter for next account..."
    read -r
done

echo "🎉 All $MAX_ACCOUNTS Accounts Processed!"
