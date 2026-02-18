#!/bin/bash
# daily-refresh.sh — Wrapper for launchd to run refresh.py with proper env
# Called by ~/Library/LaunchAgents/com.j0s028j.hvac-tnt-refresh.plist

set -euo pipefail

# ── Logging ──────────────────────────────────────────────────
LOG_DIR="$HOME/Documents/Projects/hvac-tnt-dashboard/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/refresh-$(date +%Y-%m-%d).log"

exec > "$LOG_FILE" 2>&1
echo "=== HVAC TnT Daily Refresh ==="
echo "Started: $(date)"
echo ""

# ── Environment (launchd doesn't load .zshrc/.bash_profile) ──
export HOME="/Users/j0s028j"
export PATH="$HOME/google-cloud-sdk/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Google Cloud SDK
if [ -f "$HOME/google-cloud-sdk/path.bash.inc" ]; then
    source "$HOME/google-cloud-sdk/path.bash.inc"
fi

# ── Network check (BQ needs Walmart network) ─────────────────
if ! curl -s --connect-timeout 5 https://gecgithub01.walmart.com > /dev/null 2>&1; then
    echo "❌ Cannot reach Walmart network — skipping refresh."
    echo "   (Mac may be off-network or VPN not connected)"
    exit 1
fi
echo "✅ Network reachable"

# ── Run the refresh ──────────────────────────────────────────
cd "$HOME/Documents/Projects/hvac-tnt-dashboard"
python3 refresh.py

echo ""
echo "Finished: $(date)"
echo "=== Done ==="

# ── Clean up old logs (keep 14 days) ─────────────────────────
find "$LOG_DIR" -name 'refresh-*.log' -mtime +14 -delete 2>/dev/null || true
