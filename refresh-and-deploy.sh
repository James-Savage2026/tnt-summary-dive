#!/bin/bash
#
# TnT Summary Dive - One-Command Refresh & Deploy
# ================================================
# This script:
#   1. Pulls fresh data from BigQuery
#   2. Generates the shareable HTML
#   3. Pushes to GitHub
#   4. GitHub Pages auto-updates!
#
# Usage: ./refresh-and-deploy.sh
#

set -e  # Exit on any error

echo "🐶 TnT Summary Dive - Refresh & Deploy"
echo "======================================"
echo ""

# Configuration
PROJECT_DIR="$HOME/Documents/hvac-tnt-dashboard"
GITHUB_REPO_DIR="$HOME/Documents/Projects/hvac-tnt-dashboard"
PYTHON="$HOME/.code-puppy-venv/bin/python"
BQ="$HOME/google-cloud-sdk/bin/bq"
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
export CLOUDSDK_PYTHON="$PYTHON"

cd "$PROJECT_DIR"

# Step 1: Refresh Store Data from BigQuery
echo "📊 Step 1/5: Fetching fresh store data from BigQuery..."
$BQ query --use_legacy_sql=false --format=json --max_rows=50000 --project_id=re-crystal-mdm-prod '
SELECT 
  store_number, banner_desc, city_name as store_city, state_cd as store_state,
  fm_sr_director_name, fm_director_name, fm_regional_manager_name,
  fs_manager_name, fs_market,
  twt_ref, twt_ref_7_day, twt_ref_30_day, twt_ref_90_day,
  twt_hvac, twt_hvac_7_day, twt_hvac_30_day, twt_hvac_90_day,
  case_count, cases_out_of_target, total_loss
FROM `re-crystal-mdm-prod.crystal.store_tabular_view`
WHERE country_cd = "US"
' > store_data.json
echo "   ✅ Store data refreshed!"

# Step 2: Refresh Work Order Data from BigQuery
echo "🔧 Step 2/5: Fetching fresh work order data (last 30 days)..."
$BQ query --use_legacy_sql=false --format=json --max_rows=100000 --project_id=re-crystal-mdm-prod '
SELECT 
  tracking_nbr, workorder_nbr, store_nbr,
  trade_group_name, status_name, priority_name,
  equipment_desc, problem_type_desc, problem_code_desc, problem_desc,
  created_date, completion_date,
  DATE_DIFF(CURRENT_DATE(), DATE(created_date), DAY) as age_days
FROM `re-crystal-mdm-prod.crystal.sc_workorder`
WHERE (
    UPPER(trade_group_name) LIKE "%REFRIGERATION%" 
    OR UPPER(trade_group_name) LIKE "%HVAC%" 
    OR UPPER(trade_group_name) LIKE "%EMS%"
  )
  AND store_nbr IS NOT NULL
  AND created_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY store_nbr, created_date DESC
' > workorder_data.json
echo "   ✅ Work order data refreshed!"

# Step 3: Compress work order data for smaller file size
echo "📦 Step 3/5: Compressing data for web..."
$PYTHON << 'PYTHON_SCRIPT'
import json

# Compress work order data
with open('workorder_data.json', 'r') as f:
    wo_data = json.load(f)

compressed = []
for wo in wo_data:
    compressed.append({
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
    json.dump(compressed, f, separators=(',', ':'))

print(f"   Compressed {len(wo_data)} work orders")
PYTHON_SCRIPT
echo "   ✅ Data compressed!"

# Step 4: Generate the shareable HTML
echo "🌐 Step 4/5: Generating shareable HTML..."
$PYTHON << 'PYTHON_SCRIPT'
import json
from datetime import datetime

# Read the HTML template
with open('index.html', 'r') as f:
    html = f.read()

# Read the data files
with open('store_data.json', 'r') as f:
    store_data = json.load(f)

with open('workorder_compact.json', 'r') as f:
    wo_data = json.load(f)

# Create embedded data script
embedded_script = f'''
    <script>
        // EMBEDDED DATA - No fetch required!
        const EMBEDDED_STORE_DATA = {json.dumps(store_data, separators=(',', ':'))};
        const EMBEDDED_WO_DATA = {json.dumps(wo_data, separators=(',', ':'))};
    </script>
'''

# Check if already has embedded data, replace it
if 'EMBEDDED_STORE_DATA' in html:
    # Replace existing embedded data (use lambda to avoid backslash escape issues in JSON)
    import re
    html = re.sub(
        r'<script>\s*// EMBEDDED DATA.*?</script>',
        lambda m: embedded_script.strip(),
        html,
        flags=re.DOTALL
    )
else:
    # Add embedded data after body tag
    html = html.replace('<body class="bg-gray-50 min-h-screen">', 
                       f'<body class="bg-gray-50 min-h-screen">\n{embedded_script}')

# Update the shareable banner date
today = datetime.now().strftime('%Y-%m-%d %H:%M')
if 'Shareable Version - Data as of' in html:
    import re
    html = re.sub(
        r'Data as of [0-9-]+ [0-9:]+',
        f'Data as of {today}',
        html
    )

# Write the output
with open('index.html', 'w') as f:
    f.write(html)

print(f"   Generated with {len(store_data)} stores, {len(wo_data)} work orders")
print(f"   Data timestamp: {today}")
PYTHON_SCRIPT
echo "   ✅ HTML generated!"

# Step 5: Push to GitHub
echo "🚀 Step 5/5: Pushing to GitHub..."
if [ -d "$GITHUB_REPO_DIR" ]; then
    cp index.html "$GITHUB_REPO_DIR/index.html"
    cd "$GITHUB_REPO_DIR"
    git add index.html
    git commit -m "Data refresh: $(date '+%Y-%m-%d %H:%M')" || echo "   No changes to commit"
    git push origin main
    echo "   ✅ Pushed to GitHub!"
else
    echo "   ⚠️  GitHub repo not cloned yet. Run setup first."
    echo "   Run: git clone https://gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub.git $GITHUB_REPO_DIR"
fi

echo ""
echo "======================================"
echo "🎉 Done! Your dashboard is updating at:"
echo "   https://pages.gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub/"
echo ""
echo "   (GitHub Pages takes 1-2 minutes to refresh)"
echo "======================================"
