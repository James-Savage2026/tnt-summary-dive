# HVAC TnT Dashboard — Session Checkpoint

**Last Updated:** 2026-02-16 ~8:38 PM  
**Last Commit:** `7692dea` — "Explicit page breaks + FS Manager in exec summary"  
**Session Crashed:** 413 Payload Too Large (context exceeded ~132K tokens after 323 messages)

---

## 🔥 IMMEDIATE TODO (Pick Up Here)

The user reported 3 issues right before the session crashed:

### 1. ⚠️ Bottom 10 Stores table is MISSING from PDF
- It was there before but disappeared during refactoring
- Likely cause: the `sectionBlock()` call or `page-break` div disrupted the rendering
- Check `buildTntPdf()` in `pdf-export.js` around line 280-300 — the Bottom 10 table IS in the code but may not be rendering
- Also check `buildCombinedPdf()` — it may never have had a Bottom 10

### 2. 📊 SVG visuals bleeding off right edge of PDF page
- The SVG charts (gauges, bar charts, trend lines) extend past the printable area
- Fix: reduce default widths or add `max-width:100%;overflow:hidden;` to chart containers  
- Current SVG widths: `svgTrendChart` default W=540, `svgBarChart` W=520, gauges=130
- The PDF page is `width:1100px` with `padding:40px 44px` = ~1012px usable
- 4 gauges × 130px + gaps = 560px — should be fine
- Check if the bar chart or trend chart is wider than expected

### 3. 📈 90-Day TIT Trend Line chart needs better readability
- User wants: better time indicators, easier to read date slots
- Currently shows ~6 date labels as `MM-DD` format
- Suggestions: show more date labels, use month names, add vertical gridlines at month boundaries
- Consider: weekly tick marks, highlight current week, show data point dots

---

## 📁 Project Structure (Key Files)

| File | Lines | Purpose |
|------|-------|---------|
| `pdf-export.js` | 581 | Main PDF builder — modal, content builders, page layout |
| `pdf-charts.js` | 328 | SVG chart helpers — gauges, bars, donuts, trends, tables |
| `refresh.py` | ~450 | BQ data pull + HTML embed + git push |
| `index.html` | ~18MB | Self-contained dashboard (all data + JS embedded inline) |
| `store_data.json` | 3.3MB | Current store data with `realty_ops_region` |
| `hist_tit.json` | 173K | 90-day daily TIT by director + banner (2610 rows) |
| `hist_ror.json` | 203K | 90-day daily TIT by director + realty_ops_region (3060 rows) |

## 🔧 Architecture Notes

### PDF Generation Flow
1. User clicks "Export PDF" → opens modal (`openPdfModal()`)
2. User selects tab (TnT/WTW/Leak/All), level (Sr Dir/Dir), person
3. `generatePdf()` → `buildPdfContent(tab, level, person)`
4. Content injected into hidden iframe with CSS classes
5. `html2pdf()` renders iframe to PDF with page break rules

### JS Injection Pattern
- `pdf-charts.js` + `pdf-export.js` are concatenated and injected into `index.html`
- Marker start: `/**\n * PDF Chart Helpers`
- Marker end: `\n\n // Wire PDF export button`
- Injection script (run manually or via `embed_data_in_html()` in refresh.py):
```python
with open('pdf-charts.js') as f: charts_js = f.read()
with open('pdf-export.js') as f: export_js = f.read()
combined_js = charts_js + '\n\n' + export_js
# Replace between markers in index.html
```

### Page Break Strategy
- `class="no-break"` → keeps content together within a page
- `class="page-break"` → forces a new page before the element
- html2pdf config: `pagebreak: {mode: ['css'], before: '.page-break', avoid: '.no-break'}`
- CSS in iframe: `.no-break{break-inside:avoid;page-break-inside:avoid;}` and `.page-break{break-before:page;page-break-before:always;}`

### Data Sources
| BQ Table | Dataset | Purpose |
|----------|---------|---------|
| `store_tabular_view` | `re-crystal-mdm-prod.crystal` | Current store metrics (TIT, HVAC, loss) |
| `isp_fm_realty_alignment` | `re-ods-prod.us_re_ods_prod_pub` | `realty_ops_region` mapping |
| `store_score` | `re-ods-prod.us_re_ods_prod_pub` | Historical daily TIT (since 2021) |

### Key Field Names
- `realty_ops_region` — the correct ops realty region (NOT `ops_region`)
- `fm_sr_director_name`, `fm_director_name`, `fm_regional_manager_name`
- `fs_manager_name`, `fs_market` — FS manager hierarchy
- `banner_desc` — "WM Supercenter", "Neighborhood Market", "Sam's Club", etc.
- `twt_ref_30_day`, `twt_hvac_30_day`, `total_loss`, `cases_out_of_target`

### Director → Realty Ops Region Mapping
| Director | Realty Regions |
|----------|----------------|
| Brian Conover | 19 (146 stores), 53 (131 stores) |
| Donnie Chester | 25 (161 stores), 21 (158 stores) |

---

## ✅ Completed Features (This Session)

1. **Banner breakout** — Combined/Walmart/Sam's comparison cards on every PDF page
2. **Ops Realty Region breakout** — shows significant regions (≥10 stores) with metrics
3. **90-day historical TIT trend charts** — SVG polyline charts from `store_score` table
4. **FS Manager condensed table** — at bottom of TnT and Exec Summary PDFs
5. **Page break system** — explicit `.page-break` class + `.no-break` class
6. **RM breakout table** — Regional Manager metrics including WM/Sam's columns
7. **Banner filter removed from modal** — all banners shown automatically
8. **Softer color scale** — 85-89% = lime green instead of harsh yellow
9. **refresh.py updated** — new BQ queries for hist data + embed_data_in_html()
10. **Code split** — pdf-export.js (581 lines) + pdf-charts.js (328 lines)

## 📋 Git History (Recent)
```
7692dea Explicit page breaks + FS Manager in exec summary
d737619 Fix page breaks with CSS classes + verify FS Manager table
2ac335d Add FS Manager table + fix page break splitting
e38c33a Use realty_ops_region + 90-day historical TIT trend charts
e760253 Rename to Ops Realty Region + fix PDF page breaks
02aa3a4 Add ops_region breakout to PDF exports
4a4cb1a Auto banner breakout (Combined/Walmart/Sam's) + RM ops region table
8770347 Softer color scale + banner breakout (Walmart/Sam's/Both)
7d114c5 Fix PDF export: Sr Director vs Director bug + aesthetics
```

---

## 🐾 How to Resume

Paste this to Code Puppy:

> I'm working on the HVAC TnT Dashboard PDF exports in `~/Documents/Projects/hvac-tnt-dashboard`. Read `CHECKPOINT.md` for full context. Pick up the 3 items in the IMMEDIATE TODO section: (1) Bottom 10 stores table missing from PDF, (2) SVG visuals bleeding off right edge, (3) 90-day trend chart needs better date labels/readability.
