#!/bin/bash
# ─────────────────────────────────────────────────
# share.sh — Package the dashboard for leadership
# Usage:   ./share.sh           (saves to Desktop)
#          ./share.sh /path/to  (saves to custom dir)
# ─────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +"%B %-d, %Y")
OUT_DIR="${1:-$HOME/Desktop}"
BASE_NAME="HVAC-TnT-Dashboard-${DATE}"
SHARE_DIR="${OUT_DIR}/${BASE_NAME}"
ZIP_FILE="${OUT_DIR}/${BASE_NAME}.zip"

echo "📊 Packaging HVAC TnT Dashboard — ${TIMESTAMP}"
echo "──────────────────────────────────────────────"

# Create temp staging directory
rm -rf "${SHARE_DIR}"
mkdir -p "${SHARE_DIR}"

# Copy the self-contained dashboard
cp "${SCRIPT_DIR}/index.html" "${SHARE_DIR}/${BASE_NAME}.html"

# Generate a simple README for the recipient
cat > "${SHARE_DIR}/HOW-TO-VIEW.txt" << EOF
HVAC TnT + WTW + Leak Dashboard
Snapshot: ${TIMESTAMP}
═══════════════════════════════════════

HOW TO VIEW:
  1. Double-click "${BASE_NAME}.html"
  2. It opens in your browser — that's it!

NO installs, NO logins, NO internet required.
All data is embedded in the file.

TABS:
  • TnT Dashboard — Store-level Time-in-Target scores
  • Win-the-Winter — FY26 WTW work orders & PM readiness
  • Leak Management — CY2026 refrigerant leak rates

FEATURES:
  • Filter by Sr. Director, Director, RM, FSM, Market
  • Click any store row for full detail panel
  • Email Report button captures screenshot to clipboard
  • Banner filter (All / Walmart / Sam's Club)

LIVE VERSION (requires GHE access):
  https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/

QUESTIONS:
  James Savage (j0s028j)
EOF

# Zip it up
rm -f "${ZIP_FILE}"
cd "${OUT_DIR}"
zip -rq "${BASE_NAME}.zip" "${BASE_NAME}/"
rm -rf "${SHARE_DIR}"

# Stats
SIZE=$(du -h "${ZIP_FILE}" | cut -f1)
echo ""
echo "✅ Created: ${ZIP_FILE}"
echo "   Size: ${SIZE} (from $(du -h "${SCRIPT_DIR}/index.html" | cut -f1) uncompressed)"
echo ""
echo "📧 Share via:"
echo "   • Teams: Drop into a channel or chat"
echo "   • Email: Attach the ZIP (check size < 25MB)"
echo "   • OneDrive/SharePoint: Upload to a shared folder"
echo ""
echo "🐶 Woof!"
