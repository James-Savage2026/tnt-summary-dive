# TnT + Win-the-Winter Dashboard

**Last Updated:** 2026-02-05  
**GitHub Pages:** https://james-savage2026.github.io/tnt-summary-dive/  
**Repo:** https://github.com/James-Savage2026/tnt-summary-dive

---

## 🚀 Quick Start (Morning Refresh)

```bash
# 1. Navigate to project
cd ~/Documents/Projects/hvac-tnt-dashboard

# 2. Run the WTW data loader (regenerates dashboard)
python add_wtw_tab.py

# 3. Open locally to verify
open index.html

# 4. Push to GitHub Pages
git add -A && git commit -m "Refresh data $(date +%Y-%m-%d)" && git push
```

---

## 📊 Dashboard Features

### Tab 1: TnT Dashboard
- Store-level Time-in-Target (TnT) scores
- Filters: Sr. Director, FM Director, RM, FSM, Market
- Links to Crystal store pages

### Tab 2: Win-the-Winter (WTW)
- **5,213 work orders** (FY26 WTW program)
- Phase breakdown: PH1 (1,755), PH2 (1,729), PH3 (1,729)
- **Dynamic phase cards** with status progress bars (update with filters)
- PM Readiness filters:
  - ✓ **Ready to Complete** (1,041): In Progress + All PM Pass
  - ⚠ **Should Reopen** (602): Completed + PM Fail (excl. Div1)
  - 🏪 **Div1 Stores** (351): Small-format legacy stores

---

## 🎯 PM Score Criteria

| Metric | Pass Threshold | Notes |
|--------|----------------|-------|
| **Rack Score** | ≥ 90% | From `rack_comprehensive_performance_data` |
| **TnT Score** | ≥ 90% (Walmart) / ≥ 87% (Sam's) | From `store_tabular_view.twt_ref` |
| **Dewpoint** | ≤ 52°F | From `store_tabular_view.dewpoint` |

**PM Score Formula:** `(Rack + TnT + Dewpoint) / 3`  
**Overall Pass:** All 3 metrics must pass

---

## 🏪 Div1 Stores

Div1 stores are small-format legacy "Wal-Mart" banner stores:
- `banner_desc = 'Wal-Mart'` or `store_type_cd = 'R'`
- ~24 cases vs ~133 in Supercenters
- Often missing dewpoint/rack sensors
- **Excluded from "Should Reopen"** count (shown separately)
- Marked with "D1" badge and orange highlight in table

---

## 📁 Key Files

| File | Purpose |
|------|--------|
| `index.html` | Main dashboard (TnT + WTW tabs) |
| `add_wtw_tab.py` | WTW data loader script |
| `workorder_data.json` | Cached work order data |
| `AZURE-DEPLOYMENT-GUIDE.md` | Azure hosting instructions |

---

## 🔗 BigQuery Tables

| Table | Purpose |
|-------|--------|
| `re-crystal-mdm-prod.crystal.store_tabular_view` | Store metrics, TnT, dewpoint |
| `re-crystal-mdm-prod.crystal.sc_workorder` | Service Channel work orders |
| `re-crystal-mdm-prod.crystal.rack_comprehensive_performance_data` | Rack scorecards |

---

## 🔄 Data Files in ~/bigquery_results/

| File | Records | Description |
|------|---------|-------------|
| `wtw-pm-scores-with-div1-*.csv` | 5,213 | Latest WTW data with Div1 flag |
| `wtw-should-reopen-*.csv` | 670 | Completed WOs that should reopen |
| `wtw-should-reopen-by-fm-director-*.csv` | 31 | Breakdown by FM Director |

---

## 🔧 Service Channel Link Format

```
https://www.servicechannel.com/sc/wo/Workorders/index?id={tracking_nbr}
```

---

## 📈 Current Stats (as of 2026-02-05)

| Metric | Count |
|--------|------:|
| Total WTW WOs | 5,213 |
| Completed | 1,156 |
| In Progress | 3,992 |
| Open | 58 |
| Ready to Complete | 1,041 |
| Should Reopen (non-Div1) | 602 |
| Div1 Stores | 351 |

### "Should Reopen" Breakdown
| Failure Reason | Count | % |
|----------------|------:|---:|
| TnT Failed | 533 | 89% |
| Dewpoint Failed | 146 | 24% |
| Rack Failed | 49 | 8% |

---

## 🐶 Code Puppy Commands

```
# Refresh WTW data from BigQuery
Ask: "Refresh my TNT Summary Report with WTW Tab"

# Analyze Should Reopen WOs
Ask: "Show me WTW work orders that should be reopened"

# Update dashboard and push
Ask: "Update the WTW dashboard and push to GitHub"
```

---

## 📋 Tomorrow's Checklist

- [ ] Run `python add_wtw_tab.py` to refresh data
- [ ] Check "Should Reopen" count for new completions
- [ ] Review any new Div1 store issues
- [ ] Push updates to GitHub Pages
- [ ] Share link: https://james-savage2026.github.io/tnt-summary-dive/

---

## 🛠 Troubleshooting

### "Module not found" error
```bash
cd ~/Documents/Kodiak && source .venv/bin/activate
python ~/Documents/Projects/hvac-tnt-dashboard/add_wtw_tab.py
```

### Data file not found
Check `~/bigquery_results/` for latest CSV files. May need to re-run BQ query.

### GitHub push rejected
```bash
git pull --rebase && git push
# Or force push if needed:
git push --force
```

---

## 📞 Contact

Built with Code Puppy 🐶 | Questions? #element-genai-support on Slack
