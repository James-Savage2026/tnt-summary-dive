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
- **Dynamic phase cards** with status progress bars
- **Dynamic PM readiness buttons**
- **Crystal-aligned PM scores** (within 0.74% of Crystal!)

---

## 🧮 PM Score Formula (Crystal Method)

```
PM Score = (TnT + Rack + AHU_TnT) / 3
```

| Component | Source | Pass Threshold |
|-----------|--------|----------------|
| **TnT** | `twt_ref` | ≥ 90% (WM) / ≥ 87% (Sam's) |
| **Rack** | `rack_comprehensive_performance_data` | ≥ 90% |
| **AHU TnT** | `pct_time_in_target_ahu` | ≥ 90% |

**Note:** NULL values are excluded from the average (not treated as 0).

### Example: Store 431
| Component | Value |
|-----------|------:|
| TnT | 70.30% |
| Rack | 92.92% |
| AHU TnT | 96.95% |
| **Our PM** | **86.72%** |
| **Crystal PM** | **85.98%** |
| **Difference** | **0.74%** ✅ |

---

## 🎯 PM Readiness Categories

| Button | Criteria | Meaning |
|--------|----------|--------|
| ✓ **Ready to Complete** | Not Completed + All PM Pass | Can be closed now! |
| 🔍 **Review Needed** | Completed + PM ≥90% but failing 1+ criteria | Almost there |
| ⚠ **Critical Reopen** | Completed + PM <90% | Needs work |
| 🏪 **Div1 Stores** | Small-format legacy stores | Manual review |

---

## 🏪 Div1 Stores

Div1 stores are small-format legacy "Wal-Mart" banner stores:
- `banner_desc = 'Wal-Mart'` or `store_type_cd = 'R'`
- ~24 cases vs ~133 in Supercenters
- Often missing sensor data
- Excluded from Review/Critical counts
- Marked with "D1" badge

---

## 📁 Key Files

| File | Purpose |
|------|--------|
| `index.html` | Main dashboard (TnT + WTW tabs) |
| `add_wtw_tab.py` | WTW data loader script |
| `README.md` | This documentation |

---

## 🔗 BigQuery Tables

| Table | Purpose |
|-------|--------|
| `re-crystal-mdm-prod.crystal.store_tabular_view` | Store metrics, TnT, AHU TnT |
| `re-crystal-mdm-prod.crystal.sc_workorder` | Service Channel work orders |
| `re-crystal-mdm-prod.crystal.rack_comprehensive_performance_data` | Rack scorecards |

---

## 🔗 Service Channel Link Format

```
https://www.servicechannel.com/sc/wo/Workorders/index?id={tracking_nbr}
```

---

## 📈 Current Stats (as of 2026-02-05)

| Metric | Count |
|--------|------:|
| Total WTW WOs | 5,213 |
| Completed | 1,157 |
| In Progress | 3,991 |
| Open | 58 |
| Ready to Complete | ~935 |
| Should Reopen | ~671 |
| Div1 Stores | 351 |

---

## 📋 Morning Checklist

- [ ] Run `python add_wtw_tab.py` to refresh data
- [ ] Check "Review Needed" for stores close to passing
- [ ] Check "Critical Reopen" for stores needing work
- [ ] Push updates to GitHub Pages
- [ ] Share link: https://james-savage2026.github.io/tnt-summary-dive/

---

## 🛠 Troubleshooting

### PM score doesn't match Crystal exactly
Our scores are within ~0.74% of Crystal. The small difference is due to:
- Data timing (snapshot vs real-time)
- Rounding at intermediate steps
- Possible weighted averages in Crystal

### "Module not found" error
```bash
cd ~/Documents/Kodiak && source .venv/bin/activate
python ~/Documents/Projects/hvac-tnt-dashboard/add_wtw_tab.py
```

---

## 📞 Contact

Built with Code Puppy 🐶 | Questions? #element-genai-support on Slack
