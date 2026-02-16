# ⚠️ DATA SOURCES — DO NOT MODIFY WITHOUT APPROVAL ⚠️

**Owner:** James Savage (j0s028j)  
**Last Verified:** 2026-02-16  
**Approved By:** James Savage  

> **This document is the single source of truth for every data source,
> calculation, and business rule in this dashboard. If you are modifying
> `refresh.py`, `add_wtw_tab.py`, or any BQ query, you MUST read this
> document first. Do not deviate from these specifications without
> explicit written approval from the owner.**

---

## Table of Contents

1. [Approved Data Sources](#1-approved-data-sources)
2. [Rack Score Calculation](#2-rack-score-calculation)
3. [PM Score Calculation](#3-pm-score-calculation)
4. [PM Readiness Categories](#4-pm-readiness-categories)
5. [Labor Hours](#5-labor-hours)
6. [Column Type Reference](#6-column-type-reference)
7. [Banned Data Sources](#7-banned-data-sources)
8. [Change Log](#8-change-log)

---

## 1. Approved Data Sources

| Purpose | Table | Project | Status |
|---------|-------|---------|--------|
| **Work Orders** | `crystal.sc_workorder` | `re-crystal-mdm-prod` | ✅ Approved |
| **Store Metrics** | `crystal.store_tabular_view` | `re-crystal-mdm-prod` | ✅ Approved |
| **Rack Scores** | `us_re_ods_prod_pub.dip_rack_scorecard` | `re-ods-prod` | ✅ Approved |
| **Labor Hours** | `us_re_ods_prod_pub.sc_walmart_workorder_labor_performed` | `re-ods-prod` | ✅ Approved |

### Do not substitute these tables. Period.

If a table is renamed, deprecated, or you think there's a "better" source,
do not swap it in. Open an issue, tag the owner, and get approval first.

---

## 2. Rack Score Calculation

### Source Table

```
re-ods-prod.us_re_ods_prod_pub.dip_rack_scorecard
```

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `storeNo` | STRING | Store number |
| `testDate` | DATE | Date the test was run |
| `testName` | STRING | Test type (e.g., "Compressor Proof Test") |
| `result` | INT64 | **1 = FAILED, 0 = PASSED** |
| `groupKey` | STRING | Grouping dimension (see below) |
| `groupValue` | STRING | Value within group (rack letter, circuit ID) |

### groupKey Values

| groupKey | What it means | Use in scoring? |
|----------|--------------|------------------|
| `rackCallLetter` | Rack-level test (A, B, C, D...) | **YES — use this** |
| `defrost` | Circuit-level cycling test (A2.3, B1.1...) | **NO — exclude** |

### ⚠️ CRITICAL: `result` column encoding

```
result = 1  →  TEST FAILED
result = 0  →  TEST PASSED
```

**This is counterintuitive.** Triple-check any code that touches this column.
If you see `SUM(result)` being used as "passes", that is a bug.

### Scoring Formula

```sql
Rack Score = 100.0 * (COUNT(*) - SUM(result)) / COUNT(*)
--                     total      failures       total
--          = 100 * passed_tests / total_tests
```

Filtered to:
- `groupKey = 'rackCallLetter'` (rack-level only, not circuit/defrost)
- Most recent `testDate` per store

### Approved SQL

```sql
WITH latest_date AS (
  SELECT storeNo, MAX(testDate) AS max_date
  FROM `re-ods-prod.us_re_ods_prod_pub.dip_rack_scorecard`
  WHERE groupKey = 'rackCallLetter'
  GROUP BY storeNo
)
SELECT
  d.storeNo,
  d.testDate,
  COUNT(*) AS total_tests,
  SUM(d.result) AS failed_tests,
  COUNT(*) - SUM(d.result) AS passed_tests,
  ROUND(100.0 * (COUNT(*) - SUM(d.result)) / COUNT(*), 2) AS rack_score
FROM `re-ods-prod.us_re_ods_prod_pub.dip_rack_scorecard` d
INNER JOIN latest_date ld
  ON d.storeNo = ld.storeNo AND d.testDate = ld.max_date
WHERE d.groupKey = 'rackCallLetter'
GROUP BY d.storeNo, d.testDate
```

### Validation

Store 14 on 2026-01-07:
- 38 rack-level tests, 2 failed → Rack Score = 94.74%
- Crystal PM at completion = 94.94% (within 0.34% — confirmed match)

---

## 3. PM Score Calculation

### Formula

```
PM Score = Average of AVAILABLE components (NULL excluded, NOT treated as 0)
```

### Components

| Component | Source | Column | Pass Threshold | If NULL |
|-----------|--------|--------|----------------|----------|
| Rack Score | `dip_rack_scorecard` | (calculated) | ≥ 90% | Excluded from avg |
| TnT Score | `store_tabular_v `twt_ref` | ≥ 90% (WM) / ≥ 87% (Sam's) | Excluded from avg |
| Dewpoint | `store_tabular_view` | `dewpoint` | ≤ 52°F | Excluded from avg |

### Dewpoint Scoring

- Dewpoint ≤ 52°F → component value = **100%** (pass)
- Dewpoint > 52°F → component value = **0%** (fail)
- Dewpoint is NULL → **excluded** from average entirely

### Sam's Club Threshold

Sam's Club stores (`banner_desc LIKE '%Sam%'`) use a TnT pass threshold
of **87%** instead of 90%. This is intentional and approved.

### Example

| Store | Rack | TnT | Dewpoint | PM Score |
|-------|------|-----|----------|----------|
| Has all 3 | 95% | 92% | 38°F (100%) | (95+92+100)/3 = **95.67%** |
| Missing dewpoint | 95% | 92% | NULL | (95+92)/2 = **93.50%** |
| Missing rack | NULL | 92% | 38°F (100%) | (92+100)/2 = **96.00%** |

### Overall Pass

A store passes overall **only if**:
1. All 3 components have data (not NULL)
2. Rack ≥ 90%
3. TnT ≥ 90% (or ≥ 87% for Sam's)
4. Dewpoint ≤ 52°F

---

## 4. PM Readiness Categories

| Category | Filter Criteria | Action |
|----------|----------------|--------|
| ✓ Ready to Complete | `status != 'COMPLETED'` AND overall_pass = Y | Can be closed |
| 🔍 Review Needed | `status = 'COMPLETED'` AND PM ≥ 90% AND overall_pass = N | Almost there — 1+ criteria failing |
| ⚠ Critical Reopen | `status = 'COMPLETED'` AND PM < threshold AND failing 2+ metrics AND repair < 8hrs | Needs significant work |
| 🏪 Div1 Stores | `banner_desc = 'Wal-Mart'` OR `store_type_cd = 'R'` | Manual review, excluded from reopen counts |

### PM Threshold by Banner

| Banner | PM Threshold | TnT Pass |
|--------|-------------|----------|
| Walmart (WM Supercenter, Wal-Mart) | 90% | ≥ 90% |
| Sam's Club | 87% | ≥ 87% |

### Critical Reopen — ALL 4 conditions must be true

1. WO status is `COMPLETED`
2. PM Score **< 90%** (Walmart) or **< 87%** (Sam's)
3. Failing **2 or more** of the 3 metrics (rack, tnt, dewpoint)
4. Repair hours **< 8** (indicates insufficient work was done)

Do not simplify this to just "PM < 90%". The repair hour and fail count
guardrails prevent false alarms on stores that got real work done.

---

## 5. Labor Hours

### Source Table

```
re-ods-prod.us_re_ods_prod_pub.sc_walmart_workorder_labor_performed
```

### Key Columns

| Column | Type | Maps to |
|--------|------|---------|
| `tracking_number` | INT64 | Joins to `sc_workorder.tracking_nbr` (INT64) |
| `r_t_hours` | BIGNUMERIC | Repair time hours |
| `t_t_hours` | BIGNUMERIC | Travel time hours |
| `o_t_hours` | BIGNUMERIC | Overtime hours |
| `mechanic` | STRING | Technician identifier |

### Aggregation

Each row = one check-in/visit. Aggregate per work order:

```sql
SELECT
  tracking_number,
  SUM(COALESCE(r_t_hours, 0)) AS repair_hrs,
  SUM(COALESCE(t_t_hours, 0)) AS travel_hrs,
  SUM(r_t_hours + t_t_hours)  AS total_hrs,
  COUNT(*)                    AS num_visits,
  COUNT(DISTINCT mechanic)    AS num_techs
FROM labor_performed
GROUP BY tracking_number
```

---

## 6. Column Type Reference

These type mismatches have caused query failures. Do not guess — use this table.

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `sc_workorder` | `tracking_nbr` | **INT64** | |
| `sc_workorder` | `store_nbr` | **STRING** | Cast to INT64 for joins |
| `store_tabular_view` | `store_number` | **INT64** | |
| `dip_rack_scorecard` | `storeNo` | **STRING** | Joins to sc_workorder.store_nbr directly |
| `labor_performed` | `tracking_number` | **INT64** | Matches sc_workorder.tracking_nbr |
| `store_tabular_view` | `fs_market` | **INT64** | Cast to STRING for display |

### Common Join Patterns

```sql
-- Work Orders → Store Metrics
SAFE_CAST(w.store_nbr AS INT64) = s.store_number

-- Work Orders → Rack Scores
w.store_nbr = r.storeNo  -- both STRING

-- Work Orders → Labor
w.tracking_nbr = lp.tracking_number  -- both INT64
```

---

## 7. Banned Data Sources

| Table | Why it's banned |
|-------|-----------------|
| `crystal.rack_comprehensive_performance_data` | **Data stale since Oct 2024.** Produces wildly incorrect rack scores (e.g., Store 14: 63.91% vs correct 95%). DO NOT USE. |

If you find this table referenced anywhere in the codebase, it is a bug.
Replace it with `dip_rack_scorecard` using the approved SQL above.

---

## 8. Change Log

| Date | Change | Approved By |
|------|--------|-------------|
| 2026-02-16 | Switched rack source from `rack_comprehensive_performance_data` to `dip_rack_scorecard`. Fixed `result` column encoding (1=fail, 0=pass). | James Savage |
| 2026-02-16 | Added labor hours from `sc_walmart_workorder_labor_performed`. | James Savage |
| 2026-02-16 | Confirmed PM score calculation matches Crystal within 0.34% for Store 14. | James Savage |
| 2026-02-09 | Initial dashboard build with WTW tab. | James Savage |

---

## ✋ Before You Change Anything

1. **Read this document.**
2. **Check the banned sources list.**
3. **Validate against Crystal** — pick 3 stores, compare PM scores.
4. **Get approval** from the owner before merging.
5. **Update the change log** with what you changed and who approved it.

If you skip these steps and break the dashboard, that's on you.
