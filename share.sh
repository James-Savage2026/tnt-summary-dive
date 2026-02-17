#!/bin/bash
# ─────────────────────────────────────────────────────────
# share.sh — Package the dashboard for leadership
#
# Usage:
#   ./share.sh                 → Full unfiltered ZIP to Desktop
#   ./share.sh --laura         → Laura Moore + each director ZIPs
#   ./share.sh /path/to/dir    → Full unfiltered ZIP to custom dir
# ─────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +"%B %-d, %Y")
SOURCE_HTML="${SCRIPT_DIR}/index.html"

# ---- helpers ---------------------------------------------------------------

create_howto() {
    local dir="$1" person="$2" filter_desc="$3"
    cat > "${dir}/HOW-TO-VIEW.txt" << EOF
HVAC TnT + WTW + Leak Dashboard
Snapshot: ${TIMESTAMP}
View: ${person}
═══════════════════════════════════════

HOW TO VIEW:
  1. Double-click the .html file
  2. It opens in your browser — that's it!

NO installs, NO logins, NO internet required.
All data is embedded in the file.

PRE-FILTERED TO: ${filter_desc}
(You can still change filters in the dashboard)

TABS:
  • TnT Dashboard — Store-level Time-in-Target scores
  • Win-the-Winter — FY26 WTW work orders & PM readiness
  • Leak Management — CY2026 refrigerant leak rates

LIVE VERSION (requires GHE access):
  https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/

QUESTIONS: James Savage (j0s028j)
EOF
}

# Build a single personalized ZIP
# Args: out_dir, label (filename-safe), person_display, hash_fragment, filter_desc
build_zip() {
    local out_dir="$1" label="$2" person="$3" hash="$4" filter_desc="$5"
    local base_name="HVAC-Dashboard-${DATE}-${label}"
    local stage_dir="${out_dir}/${base_name}"
    local zip_file="${out_dir}/${base_name}.zip"
    local html_file="${stage_dir}/${base_name}.html"

    rm -rf "${stage_dir}" && mkdir -p "${stage_dir}"

    if [ -z "${hash}" ]; then
        # No filter — just copy
        cp "${SOURCE_HTML}" "${html_file}"
    else
        # Inject auto-filter script right before </body>
        # This sets window.location.hash on first load so decodeStateFromURL picks it up
        local inject_script="<script>if(!window.location.hash)window.location.hash='${hash}';<\/script>"
        sed "s|</body>|${inject_script}</body>|" "${SOURCE_HTML}" > "${html_file}"
    fi

    create_howto "${stage_dir}" "${person}" "${filter_desc}"

    rm -f "${zip_file}"
    (cd "${out_dir}" && zip -rq "${base_name}.zip" "${base_name}/")
    rm -rf "${stage_dir}"

    local size
    size=$(du -h "${zip_file}" | cut -f1)
    echo "  ✅ ${zip_file##*/}  (${size})"
    echo "     → ${filter_desc}"
}

# ---- main ------------------------------------------------------------------

LAURA_MODE=false
OUT_DIR="$HOME/Desktop"

for arg in "$@"; do
    case "$arg" in
        --laura) LAURA_MODE=true ;;
        *)       OUT_DIR="$arg" ;;
    esac
done

echo ""
echo "📊 HVAC TnT Dashboard — Packaging for ${TIMESTAMP}"
echo "─────────────────────────────────────────────────────────"
echo ""

if [ "$LAURA_MODE" = true ]; then
    SHARE_DIR="${OUT_DIR}/HVAC-Dashboard-${DATE}-Laura-Moore"
    mkdir -p "${SHARE_DIR}"

    echo "👩‍💼 Laura Moore (Sr. Director — all her stores)"
    build_zip "${SHARE_DIR}" "Laura-Moore" "Laura Moore" \
        "sr=Laura%20Moore" \
        "Sr. Director: Laura Moore (all stores)"
    echo ""

    echo "👥 Directors under Laura Moore:"
    echo ""

    build_zip "${SHARE_DIR}" "Brian-Conover" "Brian Conover" \
        "sr=Laura%20Moore&dir=Brian%20Conover" \
        "Director: Brian Conover (under Laura Moore)"

    build_zip "${SHARE_DIR}" "Donnie-Chester" "Donnie Chester" \
        "sr=Laura%20Moore&dir=Donnie%20Chester" \
        "Director: Donnie Chester (under Laura Moore)"

    build_zip "${SHARE_DIR}" "Jack-Grahek" "Jack Grahek" \
        "sr=Laura%20Moore&dir=Jack%20Grahek" \
        "Director: Jack Grahek (under Laura Moore)"

    build_zip "${SHARE_DIR}" "Josh-Thaxton" "Josh Thaxton" \
        "sr=Laura%20Moore&dir=Josh%20Thaxton" \
        "Director: Josh Thaxton (under Laura Moore)"

    build_zip "${SHARE_DIR}" "Sonya-Webster" "Sonya Webster" \
        "sr=Laura%20Moore&dir=Sonya%20Webster" \
        "Director: Sonya Webster (under Laura Moore)"

    echo ""
    echo "─────────────────────────────────────────────────────────"
    echo "📦 All ZIPs saved to: ${SHARE_DIR}/"
    TOTAL=$(du -sh "${SHARE_DIR}" | cut -f1)
    echo "   Total size: ${TOTAL}"
    echo ""
    echo "📧 Share each ZIP with the respective person."
    echo "   Each opens pre-filtered to their view."
    echo "   They can still drill into other filters if needed."
else
    echo "🌍 Full dashboard (no filter)"
    build_zip "${OUT_DIR}" "Full" "Everyone" "" "All stores, all views"
fi

echo ""
echo "🐶 Woof!"
