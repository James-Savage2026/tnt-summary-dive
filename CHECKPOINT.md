# HVAC TnT Dashboard — Session Checkpoint

**Last Updated:** 2026-02-20 ~3:00 PM  
**Last Commit:** `fd7f275` — "Clean up Terminal tab debug code from switchTab"  
**Branch:** `main` — clean, up to date with both remotes  
**Session:** Stable — no crashes

---

## ✅ What Got Done This Session

### 0b. Terminal Cases Tab (NEW)
- Added 4th tab: 🌡️ Terminal Cases
- Data: `re-crystal-mdm-prod.crystal.case_terminal_performance` (513 cases, 325 stores)
- Mirrors Tableau "Refrigeration Cases Terminal Status Report"
- KPIs: Total Cases, Total Stores, Cases with/without Open WOs
- Charts: Open WOs donut, Consecutive Days bar, Sub Market bar, Director bar
- Case class cards (MT/LT breakdown with percentages)
- Full detail table with sorting, search, color-coded metrics
- 12 cascading filters: Sr Dir, Director, RM, FSM, Market, Sub Market, Case Class, Consec Days, Open WOs, HVACR Tech, Store, Ops Region
- Script: `add_terminal_tab.py`
- Data files: `terminal_cases.csv`, `terminal_wos.csv`, `terminal_sensors.csv`
- BQ pull: joins Crystal `case_terminal_performance` with `sc_workorder` for open ref WO tracking numbers
- Crystal links: `case_temp_sensor_id` from `re-ods-prod.us_re_ods_prod_pub.case_score_curr` → 100% coverage
- Key fix: f-string `\n` → `\\n` escape for JS `.join()` output
- Commit: `0f59efe`

### 0a. 11-Week TnT Trend Line Chart (NEW)
- Added multi-line Chart.js line chart showing weekly TnT performance over 11 Walmart weeks
- Data source: `trend_data.json` → compacted to `trend_compact.json` (1,518 rows, 29 directors × RMs)
- Embedded as `TREND_DATA` in index.html
- Responds to cascading filters: at Sr Director level shows directors, at Director level shows RMs
- Weighted average across stores per group per week
- Added `QUERY_WEEKLY_TREND` to `refresh.py` for automated BQ pulls
- Located below the breakdown bar chart, above Manager Performance Table
- Commit: `8b3a3dc`

### 1. Email Screenshot Fix
- Right-edge clipping on email screenshot resolved
- Capture buffer: **40px → 120px**
- Scale: **2x → 1.8x** (slight zoom out for wider viewport)
- Commits: `29bd95b`, `9d67a56`, `95f0390`, `1df22dd`, `4cb9d3a`

### 2. README Overhaul
- Updated with proper data source instructions referencing `DATA_SOURCES.md` and `~/Documents/Kodiak/TNT_Data_Sources_Reference.docx`
- Documented the email button, PDF export features, and all recent additions
- Added column type gotchas table, update instructions section, and key rules
- Commit: `62a1f95`

### 3. Share Script (`share.sh`)
- **`./share.sh`** — creates a single full-dashboard ZIP on Desktop (~2.1MB)
- **`./share.sh --laura`** — creates 6 personalized pre-filtered ZIPs:
  - Laura Moore (Sr. Director — all her stores)
  - Brian Conover (277 stores)
  - Donnie Chester (319 stores)
  - Jack Grahek (178 stores)
  - Josh Thaxton (153 stores)
  - Sonya Webster (174 stores)
- Each ZIP contains a self-contained HTML with auto-filter injection via URL hash
- Includes `HOW-TO-VIEW.txt` with instructions for recipients
- All ZIPs land in `~/Desktop/HVAC-Dashboard-{date}-Laura-Moore/`
- Commits: `8e538e4`, `5c6eee5`

### 4. Git Push (16 commits)
- Pushed 16 commits that were stuck locally to both remotes:
  - **origin:** https://github.com/James-Savage2026/tnt-summary-dive
  - **ghe:** https://gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub
- GHE Pages live: https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/

---

## 📁 Project Structure (Key Files)

| File | Size | Purpose |
|------|------|---------|
| `index.html` | 18MB | Self-contained dashboard (all data + JS embedded) |
| `refresh.py` | 24KB | BQ data pull + HTML embed + git push |
| `share.sh` | 8KB | One-command ZIP packaging (full or --laura) |
| `pdf-export.js` | 48KB | PDF builder — modal, content builders, page layout |
| `pdf-charts.js` | 36KB | SVG chart helpers — gauges, bars, donuts, trends |
| `README.md` | 12KB | Full docs with update instructions |
| `DATA_SOURCES.md` | 12KB | Single source of truth for data & business rules |
| `store_data.json` | 3.3MB | Current store data (6,469 stores) |
| `trend_compact.json` | 134KB | Weekly TnT trend data (11 weeks × 29 dirs × RMs) |
| `add_wtw_tab.py` | 78KB | WTW tab HTML/JS generator |
| `add_leak_tab.py` | 6.7KB | Leak tab HTML/JS generator |
| `add_terminal_tab.py` | 12KB | Terminal Cases tab generator |
| `leak_tab_js.py` | 21KB | Leak tab JS logic |
| `leak_tab_html.py` | 15KB | Leak tab HTML structure |
| `store_detail_js.py` | 13KB | Shared store detail panel |
| `store_assets.py` | 2.6KB | Store asset data loader |
| `sc_reopen_helper.py` | 11KB | Service Channel critical reopen logic |

---

## 📊 Dashboard Current State

- **6,469 stores** across 6 Sr. Directors, 30 Directors
- **4 tabs:** TnT Dashboard, Win-the-Winter, Leak Management, Terminal Cases
- **Filters:** Sr. Director → Director → RM → FSM → Market (cascading)
- **Banner filter:** All / Walmart / Sam's Club
- **Store detail panel** with Ref/HVAC assets, work orders, email button
- **PDF export** with multi-tab, per-person, banner breakout views
- **Email report** captures screenshot to clipboard + opens mailto
- **URL hash state** — shareable links with pre-set filters

---

## 🔗 Remotes & Live Links

| What | URL |
|------|-----|
| GHE Pages (live) | https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/ |
| GitHub Pages (live) | https://james-savage2026.github.io/tnt-summary-dive/ |
| GHE Repo | https://gecgithub01.walmart.com/j0s028j/north-bu-hvacr-report-hub |
| GitHub Repo | https://github.com/James-Savage2026/tnt-summary-dive |

---

## 🔄 Repeatable Workflows

### Daily Refresh + Share
```bash
cd ~/Documents/Projects/hvac-tnt-dashboard
python3 refresh.py       # Pull BQ data + rebuild + push
./share.sh --laura       # 6 personalized ZIPs on Desktop
```

### Quick Local Rebuild (no BQ)
```bash
python3 refresh.py --local
```

### Full Unfiltered ZIP
```bash
./share.sh
```

---

## 📋 Data Source Reference

> Full spec: `DATA_SOURCES.md` + `~/Documents/Kodiak/TNT_Data_Sources_Reference.docx`

| Table | Project | Purpose |
|-------|---------|--------|
| `crystal.sc_workorder` | `re-crystal-mdm-prod` | Work orders |
| `crystal.store_tabular_view` | `re-crystal-mdm-prod` | Store metrics, TnT, dewpoint |
| `us_re_ods_prod_pub.dip_rack_scorecard` | `re-ods-prod` | Rack scores |
| `us_re_ods_prod_pub.sc_walmart_workorder_labor_performed` | `re-ods-prod` | Labor hours |
| `crystal.ahu_hvac_time_in_target_score` | `re-crystal-mdm-prod` | AHU unit counts |
| `crystal.rtu_hvac_time_in_target_score` | `re-crystal-mdm-prod` | RTU unit counts |

**🚫 BANNED:** `rack_comprehensive_performance_data` — stale, DO NOT USE.

---

## 🐾 Known Issues / Future Ideas

- PDF Bottom 10 table may still have rendering edge cases
- SVG charts can bleed on very narrow PDF pages (~1012px usable)
- 90-day trend chart date labels could use more month-boundary markers
- `share.sh` currently hardcodes Laura's org — could be made dynamic for other Sr. Directors
- The old `HVAC-TnT-Dashboard-2026-02-16.zip` from the first `share.sh` run is still on Desktop (can delete)

---

## 🐾 How to Resume

Paste this to Code Puppy:

> I'm working on the HVAC TnT Dashboard in `~/Documents/Projects/hvac-tnt-dashboard`. Read `CHECKPOINT.md` for full context. The dashboard is stable with 3 tabs, email report, PDF export, and `share.sh --laura` for personalized ZIPs. Pick up from the Known Issues section or ask me what to work on next.
