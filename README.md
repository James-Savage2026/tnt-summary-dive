# TnT + Win-the-Winter + Leak Dashboard

**Last Updated:** 2026-02-16  
**GHE Pages:** https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/  
**GitHub Pages:** https://james-savage2026.github.io/tnt-summary-dive/  
**GHE Repo:** https://gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub  
**GitHub Repo:** https://github.com/James-Savage2026/tnt-summary-dive

---

## 🚀 One-Command Refresh

```bash
cd ~/Documents/Projects/hvac-tnt-dashboard
python3 refresh.py
```

That's it. The script:
1. Pulls fresh WTW work orders + PM scores from BigQuery
2. Pulls labor hours from `sc_walmart_workorder_labor_performed`
3. Pulls rack scorecard data (latest test date, `COUNT DISTINCT` per rack)
4. Pulls HVAC unit counts (`COUNT DISTINCT hvacName` — not reading counts)
5. Pulls store-level TnT/HVAC metrics from `store_tabular_view`
6. Pulls 30-day Ref/HVAC work orders with `problem_code_desc`
7. Merges everything, calculates PM scores (NULL-excluded)
8. Rebuilds all 3 tabs (TnT, WTW, Leak)
9. Pushes to both GitHub remotes

### Options

```bash
python3 refresh.py            # Full refresh (BQ + rebuild + push)
python3 refresh.py --local    # Rebuild from cached CSV (no BQ, no push)
python3 refresh.py --no-push  # Pull BQ + rebuild, skip git push
```

---

## 🐶 Kodiak Quick Prompt

Paste this into Code Puppy to refresh:

```
Refresh my TNT Summary Report.
Location: ~/Documents/Projects/hvac-tnt-dashboard/
Run: python3 refresh.py
```

---

## ⚠️ Data Sources — READ BEFORE MODIFYING

> **See [DATA_SOURCES.md](DATA_SOURCES.md) for the full specification.**  
> A companion Word doc (`TNT_Data_Sources_Reference.docx`) lives in `~/Documents/Kodiak/`.  
> **Do not change data sources, queries, or business rules without reading those documents and getting written approval from the owner (James Savage).**

### Quick Reference

| Purpose | Table | Project |
|---------|-------|---------|
| Work Orders | `crystal.sc_workorder` | `re-crystal-mdm-prod` |
| Store Metrics | `crystal.store_tabular_view` | `re-crystal-mdm-prod` |
| Rack Scores | `us_re_ods_prod_pub.dip_rack_scorecard` | `re-ods-prod` |
| Labor Hours | `us_re_ods_prod_pub.sc_walmart_workorder_labor_performed` | `re-ods-prod` |
| AHU Units | `crystal.ahu_hvac_time_in_target_score` | `re-crystal-mdm-prod` |
| RTU Units | `crystal.rtu_hvac_time_in_target_score` | `re-crystal-mdm-prod` |

**🚫 BANNED:** `rack_comprehensive_performance_data` — stale data since Oct 2024. DO NOT USE.

### Key Rules

- `result = 1` means **FAILED** (not passed!) in `dip_rack_scorecard`
- HVAC units: use `COUNT(DISTINCT hvacName)`, never `COUNT(*)`
- PM Score: average of available components, NULL = excluded (not zero)
- Sam's Club TnT threshold: **87%** (vs 90% for Walmart)
- Rack scores: filter to latest `testDate` + `groupKey = 'rackCallLetter'` only

---

## 📊 Dashboard Tabs

### Tab 1: TnT Dashboard
- Store-level Time-in-Target scores (Ref + HVAC)
- **Global banner filter** (All / Walmart / Sam's) affects all KPIs, charts, and tables
- Filters: Sr. Director, FM Director, RM, FSM, Market
- Bottom 10 worst stores with drill-down
- Store detail panel with:
  - Refrigeration assets (racks, scorecard, cases, alarms)
  - HVAC assets (RTU/AHU counts, TnT, dewpoint)
  - Work orders with **Problem Code**, **Trade** (Ref/HVAC), **Equipment**, **Resolution**
  - Trade filter on WO table (All / Refrigeration / HVAC)
  - ✉️ **Email Report button** — captures a screenshot of the store detail panel to clipboard, opens a pre-formatted `mailto:` with the store summary for quick sharing
- Links to Crystal store pages

### Tab 2: Win-the-Winter (WTW)
- FY26 WTW work orders (Phase 1, 2, 3)
- PM readiness categories with dynamic filters
- Labor hours, visit counts, tech counts per WO
- Clickable tracking numbers → Service Channel

### Tab 3: Leak Management
- CY2026 refrigerant leak rates with burn rate projection
- Cumulative YoY chart
- Per-store detail with asset cross-reference (click any store row to expand)
- Refrigeration + HVAC asset detail panels
- CY2026 leak events table per store

---

## 📄 PDF / Email Export

### Email Report (TnT Tab)
Click the **✉️ Email Report** button on any store detail panel to:
1. Capture a high-res screenshot of the store detail panel
2. Copy the screenshot to your clipboard
3. Open a `mailto:` link with a pre-formatted subject and body containing store metrics
4. Paste the screenshot into the email body for a visual report

### PDF Export (All Tabs)
- Multi-tab PDF export with per-tab or combined "Exec Summary" views
- Sr. Director / Director level breakdowns
- Banner breakout (Combined / Walmart / Sam's comparison cards)
- Ops Realty Region breakout for significant regions (≥10 stores)
- 90-day historical TIT trend charts
- FS Manager and Regional Manager metric tables
- Proper page breaks between sections

---

## 🧮 PM Score Calculation

**PM Score = Average of AVAILABLE components (NULL excluded, not treated as 0)**

| Component | Source | Pass Threshold | If NULL |
|-----------|--------|----------------|----------|
| Rack Score | `dip_rack_scorecard` (calculated) | ≥ 90% | Excluded |
| TnT Score | `store_tabular_view.twt_ref` | ≥ 90% (WM) / ≥ 87% (Sam's) | Excluded |
| Dewpoint | `store_tabular_view.dewpoint` | ≤ 52°F (100 if pass, 0 if fail) | Excluded |

### Example
- Store has Rack: 95%, TnT: 92%, Dewpoint: NULL
- PM = (95 + 92) / 2 = **93.5%** ✓ (not 62.3%)

---

## 🎯 PM Readiness Categories

| Category | Criteria | Action |
|----------|----------|--------|
| ✓ Ready to Complete | Not Completed + All PM Pass | Can be closed |
| 🔍 Review Needed | Completed + PM ≥90% but failing 1+ criteria | Minor fix needed |
| ⚠ Critical Reopen | Completed + PM < threshold + 2+ fails + <8 repair hrs | Needs work |
| 🏪 Div1 Stores | Small-format legacy stores | Manual review |

### Critical Reopen — ALL 4 conditions must be true
1. WO status is `COMPLETED`
2. PM Score **< 90%** (Walmart) or **< 87%** (Sam's)
3. Failing **2 or more** of the 3 metrics
4. Repair hours **< 8** (indicates insufficient work)

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `refresh.py` | One-command refresh (BQ pull + merge + rebuild + push) |
| `index.html` | Main dashboard (TnT + WTW + Leak tabs, all data embedded) |
| `pdf-export.js` | PDF builder — modal, content builders, page layout |
| `pdf-charts.js` | SVG chart helpers — gauges, bars, donuts, trends, tables |
| `add_wtw_tab.py` | WTW tab HTML/JS generator |
| `add_leak_tab.py` | Leak tab HTML/JS generator |
| `leak_tab_js.py` | Leak tab JS logic (table, charts, filters) |
| `leak_tab_html.py` | Leak tab HTML structure |
| `store_assets.py` | Store asset data loader (rack, HVAC, case, terminal) |
| `store_detail_js.py` | Shared store detail panel (Ref/HVAC assets, leak events) |
| `sc_reopen_helper.py` | Service Channel critical reopen logic |
| `DATA_SOURCES.md` | **Single source of truth** for data sources & business rules |

---

## 🔄 Update Instructions

### For Code Puppy / Kodiak

Before making **any** changes to data queries or business logic:

1. **Read [`DATA_SOURCES.md`](DATA_SOURCES.md)** — the single source of truth
2. **Read `~/Documents/Kodiak/TNT_Data_Sources_Reference.docx`** — companion reference
3. **Check the banned sources list** — `rack_comprehensive_performance_data` is BANNED
4. **Validate against Crystal** — pick 3 stores, compare PM scores
5. **Get written approval** from James Savage before merging
6. **Update the change log** in `DATA_SOURCES.md`

### Adding New Features

```bash
# 1. Make your changes
# 2. Test locally
open index.html

# 3. Commit
git add -A && git commit -m "Description of change"

# 4. Push to both remotes
git push origin main
git push ghe main
```

### Refreshing Data

```bash
python3 refresh.py          # Full refresh + auto-push
python3 refresh.py --local  # Rebuild only (no BQ, no push)
```

### Column Type Gotchas

| Column | Type | Watch Out |
|--------|------|-----------|
| `sc_workorder.store_nbr` | STRING | `SAFE_CAST` to INT64 for store joins |
| `sc_workorder.tracking_nbr` | INT64 | Matches `labor_performed.tracking_number` |
| `dip_rack_scorecard.storeNo` | STRING | Joins to `store_nbr` directly |
| `store_tabular_view.fs_market` | INT64 | Cast to STRING for display |
| `dip_rack_scorecard.result` | INT64 | **1 = FAILED, 0 = PASSED** (counterintuitive!) |

---

## 🏪 Div1 Stores

- `banner_desc = 'Wal-Mart'` or `store_type_cd = 'R'`
- ~24 cases vs ~133 in Supercenters
- Often missing sensor data
- Excluded from Review/Critical reopen counts
- Marked with "D1" badge in dashboard

---

## 🛠 Troubleshooting

| Issue | Fix |
|-------|-----|
| BQ query timeout | Run `python3 refresh.py` again |
| Git push rejected | `git pull --rebase && git push` |
| PM score too low | Check if NULL data is being treated as 0 |
| "No Data" for metrics | Correct behavior — NULL excluded |
| Module not found | Use system python3, not a venv |
| HVAC units too high | Must use `COUNT DISTINCT hvacName` |
| Rack scores wrong | Filter to latest `testDate` only |
| Email screenshot clipped | Check zoom/scale in screenshot logic |
| PDF SVGs bleeding off page | Max-width containers, ~1012px usable |

---

## 📞 Contact

Built with Code Puppy 🐶 | Owner: James Savage (j0s028j)  
Questions? #element-genai-support on Slack
