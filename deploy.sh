#!/bin/bash
#
# TnT Summary Dive - Quick Deploy (uses existing data)
# =====================================================
# This script:
#   1. Generates the shareable HTML from existing data
#   2. Pushes to GitHub
#   3. GitHub Pages auto-updates!
#
# Usage: ./deploy.sh
#
# For full refresh including BQ data, use: ./refresh-and-deploy.sh
#

set -e

echo "🐶 TnT Summary Dive - Quick Deploy"
echo "=================================="
echo ""

# Configuration
PROJECT_DIR="$HOME/Documents/hvac-tnt-dashboard"
GITHUB_REPO_DIR="$HOME/Documents/tnt-summary-dive-github"
PYTHON="$HOME/.code-puppy-venv/bin/python"

cd "$PROJECT_DIR"

# Step 1: Generate the shareable HTML
echo "🌐 Step 1/2: Generating shareable HTML..."
$PYTHON << 'PYTHON_SCRIPT'
import json
from datetime import datetime
import os

print("   Loading data...")

# Read the data files
with open('store_data.json', 'r') as f:
    store_data = json.load(f)

# Check if compact WO exists, otherwise create it
if os.path.exists('workorder_compact.json'):
    with open('workorder_compact.json', 'r') as f:
        wo_data = json.load(f)
else:
    print("   Compressing work orders...")
    with open('workorder_data.json', 'r') as f:
        wo_raw = json.load(f)
    wo_data = []
    for wo in wo_raw:
        wo_data.append({
            't': wo.get('tracking_nbr', ''),
            's': wo.get('store_nbr', ''),
            'st': wo.get('status_name', ''),
            'p': wo.get('priority_name', ''),
            'tr': wo.get('trade_group_name', ''),
            'a': wo.get('age_days', 0),
            'pd': (wo.get('problem_desc', '') or '')[:100],
            'eq': (wo.get('equipment_desc', '') or '')[:30]
        })
    with open('workorder_compact.json', 'w') as f:
        json.dump(wo_data, f, separators=(',', ':'))

print(f"   Loaded {len(store_data)} stores, {len(wo_data)} work orders")

# Read base HTML
with open('index.html', 'r') as f:
    html = f.read()

# Create embedded data script
today = datetime.now().strftime('%Y-%m-%d %H:%M')
embedded_script = f'''
    <script>
        // EMBEDDED DATA - Generated {today}
        const EMBEDDED_STORE_DATA = {json.dumps(store_data, separators=(',', ':'))};
        const EMBEDDED_WO_DATA = {json.dumps(wo_data, separators=(',', ':'))};
    </script>
'''

# Insert or replace embedded data
import re
if 'EMBEDDED_STORE_DATA' in html:
    # Find and replace the existing embedded data section
    pattern = r'<script>\s*// EMBEDDED DATA.*?</script>'
    match = re.search(pattern, html, flags=re.DOTALL)
    if match:
        html = html[:match.start()] + embedded_script.strip() + html[match.end():]
else:
    html = html.replace('<body class="bg-gray-50 min-h-screen">', 
                       f'<body class="bg-gray-50 min-h-screen">\n{embedded_script}')

# Update banner date if present
if 'Data as of' in html:
    html = re.sub(r'Data as of [0-9-]+ [0-9:]+', f'Data as of {today}', html)

# Write output
with open('index.html', 'w') as f:
    f.write(html)

print(f"   ✅ Generated! Data timestamp: {today}")
PYTHON_SCRIPT

# Step 2: Push to GitHub
echo "🚀 Step 2/2: Pushing to GitHub..."
cp index.html "$GITHUB_REPO_DIR/index.html"
cd "$GITHUB_REPO_DIR"
git add index.html
git commit -m "Dashboard update: $(date '+%Y-%m-%d %H:%M')" || echo "   No changes to commit"
git push origin main

echo ""
echo "=================================="
echo "🎉 Done! Your dashboard is live at:"
echo ""
echo "   https://james-savage2026.github.io/tnt-summary-dive/"
echo ""
echo "   (GitHub Pages updates in ~1 minute)"
echo "=================================="
