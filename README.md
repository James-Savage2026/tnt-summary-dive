# TnT + Win-the-Winter + Leak Dashboard

**Last Updated:** 2026-02-09  
**GHE Pages:** https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/  
**GitHub Pages:** https://james-savage2026.github.io/tnt-summary-dive/  
**Repo:** https://gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub

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

## 📊 Dashboard Tabs

### Tab 1: TnT Dashboard
- Store-level Time-in-Target scores (Ref + HVAC)
- **Global banner filter** (All / Walmart / Sam’s) affects all KPIs, charts, and tables
- Filters: Sr. Director, FM Director, RM, FSM, Market
- Bottom 10 worst stores with drill-down
- Store detail panel with:
  - Refrigeration assets (racks, scorecard, cases, alarms)
  - HVAC assets (RTU/AHU counts, TnT, dewpoint)
  - Work orders with **Problem Code**, **Trade** (Ref/HVAC), **Equipment**, **Resolution**
  - Trade filter on WO table (All / Refrigeration / HVAC)
  - ✉️ **Email button** — generates mailto with full store report
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

## 🧮 PM Score Calculation

**PM Score = Average of AVAILABLE components (NULL excluded, not treated as 0)**

| Component | Source Column | Pass Threshold | If NULL |
|-----------|--------------|----------------|----------|
| Rack Score | `rack_comprehensive_performance_data.scorecard_score` | ≥ 90% | Excluded |
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
| ⚠ Critical Reopen | Completed + PM below threshold + 2+ fails + <8 repair hrs | Needs work — reopen WO |
| 🏪 Div1 Stores | Small-format legacy stores | Manual review |

---

## 📁 Key Files

| File | Purpose |
|------|--------|
| `refresh.py` | **One-command refresh** (BQ pull + merge + rebuild + push) |
| `index.html` | Main dashboard (TnT + WTW + Leak tabs) |
| `add_wtw_tab.py` | WTW tab HTML/JS generator |
| `add_leak_tab.py` | Leak tab HTML/JS generator |
| `leak_tab_js.py` | Leak tab JS logic (table, charts, filters) |
| `leak_tab_html.py` | Leak tab HTML structure |
| `store_assets.py` | Store asset data loader (rack, HVAC, case, terminal) |
| `store_detail_js.py` | Shared store detail panel (Ref/HVAC assets, leak events) |

---

## 🔗 BigQuery Data Sources

> **⚠️ See [DATA_SOURCES.md](DATA_SOURCES.md) for the full specification.
> Do not change data sources without reading that document and getting approval.**

| Table | Purpose | Join Key |
|-------|---------|----------|
| `crystal.store_tabular_view` | Store metrics, TnT, dewpoint | `store_number` (INT64) |
| `crystal.sc_workorder` | Service Channel work orders | `tracking_nbr` (INT64), `store_nbr` (STRING) |
| `us_re_ods_prod_pub.dip_rack_scorecard` | Rack scores (latest date, `COUNT DISTINCT` per rack) | `storeNo` (STRING) |
| `us_re_ods_prod_pub.sc_walmart_workorder_labor_performed` | Labor hours | `tracking_number` (INT64) |
| `crystal.ahu_hvac_time_in_target_score` | AHU unit count (`COUNT DISTINCT hvacName`) | `storeNo` (STRING) |
| `crystal.rtu_hvac_time_in_target_score` | RTU unit count (`COUNT DISTINCT hvacName`) | `storeNo` (STRING) |

**⚠️ BANNED:** `rack_comprehensive_performance_data` — stale data, DO NOT USE.

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
| BQ query timeout | Run `python3 refresh.py` again — labor query can take ~30s |
| Git push rejected | `git pull --rebase && git push` |
| PM score too low | Check if NULL data is being treated as 0 — should be excluded |
| "No Data" for metrics | Correct behavior — NULL excluded from PM average |
| Module not found | Use system python3, not a venv |
| HVAC units too high | Must use `COUNT DISTINCT hvacName`, not `COUNT(*)` of readings |
| Rack pass/fail counts absurd | Must filter to latest `testDate` only, not all history |
| Leak tab store details missing | Check `hasDetail` declared before use (JS `const` hoisting bug) |
| WO table missing problem codes | Ensure `problem_code_desc` is in the BQ query and mapped to `pc` |

---

## 📞 Contact

Built with Code Puppy 🐶 | Questions? #element-genai-support on Slack
