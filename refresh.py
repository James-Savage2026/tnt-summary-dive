#!/usr/bin/env python3
"""One-command refresh for the TNT + WTW + Leak dashboard.

Pulls fresh data from BigQuery, merges labor hours, calculates PM scores,
rebuilds all tabs, and pushes to both GitHub remotes.

Usage:
    python3 refresh.py          # Full refresh (BQ pull + rebuild + push)
    python3 refresh.py --local  # Rebuild from cached CSV (no BQ, no push)
    python3 refresh.py --no-push # Pull BQ data + rebuild, but skip git push
"""
import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# === Paths ===
PROJECT = Path(__file__).parent
BQ_DIR = Path.home() / 'bigquery_results'
LATEST_CSV = BQ_DIR / 'wtw-fy26-workorders-pm-scores-labor-LATEST.csv'
PHASE_MAP_CSV = BQ_DIR / 'wtw-fy26-workorders-pm-scores-labor-20260209-151220.csv'
BQ_RAW_CSV = BQ_DIR / 'wtw-bq-raw-latest.csv'
LABOR_CSV = BQ_DIR / 'wtw-labor-latest.csv'
RACK_CSV = BQ_DIR / 'dip-rack-scores-latest.csv'


# === BQ Queries ===
# Stored as constants so they're version-controlled and never hand-typed again.

# ─── RACK SCORE SOURCE ───────────────────────────────────────────────
# DO NOT CHANGE THIS TABLE without explicit approval.
# See DATA_SOURCES.md for full rationale.
#
# Correct table:  re-ods-prod.us_re_ods_prod_pub.dip_rack_scorecard
# Wrong table:    re-crystal-mdm-prod.crystal.rack_comprehensive_performance_data
#                 (stale — data only through Oct 2024, DO NOT USE)
#
# Scoring rules:
#   - Filter to groupKey = 'rackCallLetter' (rack-level tests only)
#   - result = 1 means FAILED, result = 0 means PASSED
#   - Rack Score = 100 * (tests where result=0) / (total tests)
#   - Use most recent testDate per store
# ─────────────────────────────────────────────────────────────────────

QUERY_WTW_WORKORDERS = """
SELECT
  w.tracking_nbr, w.workorder_nbr, w.store_nbr,
  CONCAT(IFNULL(s.city_name,''), ', ', IFNULL(s.state_cd,'')) AS store_name,
  w.status_name, w.extended_status_name,
  s.city_name, s.state_cd,
  s.fm_sr_director_name, s.fm_director_name, s.fm_regional_manager_name,
  s.fs_manager_name, CAST(s.fs_market AS STRING) AS fs_market,
  FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%S', w.expiration_date) AS expiration_date,
  FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%S', w.created_date) AS created_date,
  ROUND(s.twt_ref, 2) AS tnt_score,
  ROUND(s.dewpoint, 1) AS dewpoint_raw,
  ROUND(s.twt_hvac, 2) AS dewpoint_score,
  IF(s.banner_desc = 'Wal-Mart' OR s.store_type_cd = 'R', 'Y', 'N') AS is_div1,
  s.banner_desc
FROM `re-crystal-mdm-prod.crystal.sc_workorder` w
LEFT JOIN `re-crystal-mdm-prod.crystal.store_tabular_view` s
  ON SAFE_CAST(w.store_nbr AS INT64) = s.store_number
WHERE w.problem_code_desc LIKE '%WIN THE WINTER%'
  AND SAFE_CAST(w.store_nbr AS INT64) IS NOT NULL
  AND w.created_date >= '2025-06-01'
ORDER BY SAFE_CAST(w.store_nbr AS INT64)
"""

QUERY_RACK_SCORES = """
-- Rack scores from dip_rack_scorecard (most recent date per store)
-- DO NOT replace with rack_comprehensive_performance_data — see DATA_SOURCES.md
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
ORDER BY d.storeNo
"""

QUERY_LABOR = """
SELECT
  lp.tracking_number,
  ROUND(SUM(COALESCE(lp.r_t_hours, 0)), 2) AS repair_hrs,
  ROUND(SUM(COALESCE(lp.t_t_hours, 0)), 2) AS travel_hrs,
  ROUND(SUM(COALESCE(lp.o_t_hours, 0)), 2) AS ot_hrs,
  ROUND(SUM(COALESCE(lp.r_t_hours, 0) + COALESCE(lp.t_t_hours, 0)), 2) AS total_hrs,
  COUNT(*) AS num_visits,
  COUNT(DISTINCT lp.mechanic) AS num_techs
FROM `re-ods-prod.us_re_ods_prod_pub.sc_walmart_workorder_labor_performed` lp
INNER JOIN (
  SELECT tracking_nbr
  FROM `re-crystal-mdm-prod.crystal.sc_workorder`
  WHERE problem_code_desc LIKE '%WIN THE WINTER%'
    AND created_date >= '2025-06-01'
) wtw ON lp.tracking_number = wtw.tracking_nbr
GROUP BY lp.tracking_number
"""

QUERY_STORES = """
SELECT
  store_number, banner_desc, city_name AS store_city, state_cd AS store_state,
  fm_sr_director_name, fm_director_name, fm_regional_manager_name,
  fs_manager_name, fs_market, ops_region,
  twt_ref, twt_ref_7_day, twt_ref_30_day, twt_ref_90_day,
  twt_hvac, twt_hvac_7_day, twt_hvac_30_day, twt_hvac_90_day,
  case_count, cases_out_of_target, total_loss
FROM `re-crystal-mdm-prod.crystal.store_tabular_view`
WHERE country_cd = 'US'
"""


def run_bq(query: str, output_path: Path, max_rows: int = 15000) -> int:
    """Run a BQ query and save results as CSV. Returns row count."""
    print(f"   Running BQ query -> {output_path.name}...")
    cmd = [
        'bq', 'query', '--format=csv', f'--max_rows={max_rows}',
        '--use_legacy_sql=false', query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    # Filter out gcloud warnings
    lines = [
        line for line in result.stdout.splitlines()
        if not any(skip in line for skip in [
            'WARNING', 'Python', 'gcloud', 'reinstall', 'CLOUDSDK',
            'compatible', 'setting', 'Waiting'
        ]) and line.strip()
    ]
    if lines and lines[0].startswith('Error'):
        print(f"   \u274c BQ ERROR: {''.join(lines[:3])}")
        sys.exit(1)
    output_path.write_text('\n'.join(lines) + '\n')
    row_count = len(lines) - 1  # minus header
    print(f"   \u2705 {row_count} rows")
    return row_count


def load_csv(path: Path) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_phase_map() -> dict[str, str]:
    """Load phase assignments from the original baseline CSV."""
    phase_map = {}
    if not PHASE_MAP_CSV.exists():
        print("   \u26a0\ufe0f  No phase baseline CSV found, assigning by date")
        return phase_map
    with open(PHASE_MAP_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            phase = row.get('phase', '').strip()
            if phase in ('PH1', 'PH2', 'PH3'):
                phase_map[row['tracking_nbr'].strip()] = phase
    return phase_map


def assign_phase(tracking_nbr: str, created_date: str, phase_map: dict) -> str:
    """Assign WTW phase. Known WOs use the baseline map; new ones use date."""
    phase = phase_map.get(tracking_nbr, '')
    if phase:
        return phase
    # New WOs: PH2 started Jan 11, PH3 started Jan 13
    if created_date >= '2026-01-13':
        return 'PH3'
    if created_date >= '2026-01-11':
        return 'PH2'
    return 'PH1'


def calc_pm(row: dict) -> dict:
    """Calculate PM score and pass/fail for a single WO row.

    PM Score = Average of AVAILABLE components (NULL excluded):
      - Rack Score (pass \u2265 90%)
      - TnT Score  (pass \u2265 90% WM / \u2265 87% Sam's)
      - Dewpoint   (pass \u2264 52\u00b0F, scored as 100 if pass, 0 if fail)
    """
    def parse_float(val):
        if val and val not in ('', 'null', 'None'):
            return float(val)
        return None

    tnt_v = parse_float(row.get('tnt_score', ''))
    rack_v = parse_float(row.get('rack_score', ''))
    dew_v = parse_float(row.get('dewpoint_raw', ''))
    banner = row.get('banner_desc', '')
    is_sams = 'Sam' in banner

    # Build component list (NULL excluded)
    components = []
    if rack_v is not None:
        components.append(rack_v)
    if tnt_v is not None:
        components.append(tnt_v)
    if dew_v is not None:
        components.append(100.0 if dew_v <= 52 else 0.0)

    pm_score = round(sum(components) / len(components), 2) if components else ''

    # Pass/fail per metric
    rack_pass = 'Y' if rack_v is not None and rack_v >= 90 else 'N'
    tnt_pass = 'Y' if tnt_v is not None and (
        (is_sams and tnt_v >= 87) or (not is_sams and tnt_v >= 90)
    ) else 'N'
    dew_pass = 'Y' if dew_v is not None and dew_v <= 52 else 'N'

    # Overall: all 3 must pass AND all 3 must have data
    overall = 'Y' if (
        len(components) == 3
        and rack_pass == 'Y' and tnt_pass == 'Y' and dew_pass == 'Y'
    ) else 'N'

    return {
        'pm_score': pm_score,
        'rack_pass': rack_pass,
        'tnt_pass': tnt_pass,
        'dewpoint_pass': dew_pass,
        'overall_pass': overall,
        'components_available': str(len(components)),
    }


def merge_data(
    bq_rows: list, labor_map: dict, rack_map: dict, phase_map: dict,
) -> list[dict]:
    """Merge BQ WO data + rack scores + labor + phases into final output."""
    out = []
    for r in bq_rows:
        tn = str(r['tracking_nbr']).strip()
        lp = labor_map.get(tn, {})
        store = r.get('store_nbr', '').strip()
        # Inject rack score from dip_rack_scorecard
        r['rack_score'] = str(rack_map[store]) if store in rack_map else ''
        pm = calc_pm(r)

        out.append({
            'tracking_nbr': tn,
            'workorder_nbr': r.get('workorder_nbr', ''),
            'store_nbr': r.get('store_nbr', ''),
            'store_name': r.get('store_name', ''),
            'status_name': r.get('status_name', ''),
            'extended_status_name': r.get('extended_status_name', ''),
            'phase': assign_phase(tn, r.get('created_date', ''), phase_map),
            'city_name': r.get('city_name', ''),
            'state_cd': r.get('state_cd', ''),
            'fm_sr_director_name': r.get('fm_sr_director_name', ''),
            'fm_director_name': r.get('fm_director_name', ''),
            'fm_regional_manager_name': r.get('fm_regional_manager_name', ''),
            'fs_manager_name': r.get('fs_manager_name', ''),
            'fs_market': r.get('fs_market', ''),
            'expiration_date': r.get('expiration_date', ''),
            'created_date': r.get('created_date', ''),
            'tnt_score': r.get('tnt_score', ''),
            'rack_score': r.get('rack_score', ''),
            'dewpoint_raw': r.get('dewpoint_raw', ''),
            'dewpoint_score': r.get('dewpoint_score', ''),
            **pm,
            'is_div1': r.get('is_div1', 'N'),
            'banner_desc': r.get('banner_desc', ''),
            'repair_hrs': lp.get('repair_hrs', '0'),
            'travel_hrs': lp.get('travel_hrs', '0'),
            'ot_hrs': lp.get('ot_hrs', '0'),
            'total_hrs': lp.get('total_hrs', '0'),
            'num_visits': lp.get('num_visits', '0'),
            'num_techs': lp.get('num_techs', '0'),
        })
    return out


def write_csv(rows: list[dict], path: Path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def print_stats(rows: list[dict]):
    """Print a summary of the merged data."""
    phases = Counter(r['phase'] for r in rows)
    statuses = Counter(r['status_name'] for r in rows)
    hrs = [float(r['total_hrs']) for r in rows]
    with_hrs = sum(1 for h in hrs if h > 0)
    print(f"   Total WOs: {len(rows)}")
    print(f"   Phases: {dict(sorted(phases.items()))}")
    print(f"   Statuses: {dict(statuses)}")
    print(f"   Labor: avg={sum(hrs)/len(hrs):.1f}hrs, "
          f"with_data={with_hrs}, missing={len(hrs)-with_hrs}")


def run_tab_scripts():
    """Run add_wtw_tab.py and add_leak_tab.py to rebuild index.html."""
    for script in ['add_wtw_tab.py', 'add_leak_tab.py']:
        path = PROJECT / script
        if path.exists():
            print(f"   Running {script}...")
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(PROJECT), capture_output=True, text=True
            )
            # Print last meaningful line
            for line in result.stdout.strip().splitlines()[-2:]:
                if line.strip():
                    print(f"   {line.strip()}")
        else:
            print(f"   \u26a0\ufe0f  {script} not found, skipping")


def git_push():
    """Commit and push to both remotes."""
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    cmds = [
        ['git', 'add', '-A'],
        ['git', 'commit', '-m', f'Refresh data {stamp}'],
        ['git', 'push', 'origin', 'main'],
        ['git', 'push', 'ghe', 'main'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=str(PROJECT), capture_output=True, text=True)
        if result.returncode != 0 and 'nothing to commit' not in result.stdout:
            label = ' '.join(cmd[:3])
            print(f"   \u26a0\ufe0f  {label}: {result.stderr.strip()[:100]}")
        elif 'push' in cmd:
            remote = cmd[2]
            print(f"   \u2705 Pushed to {remote}")


def main():
    local_only = '--local' in sys.argv
    no_push = '--no-push' in sys.argv
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n\U0001f43e TNT Dashboard Refresh \u2014 {ts}")
    print("=" * 50)

    # --- Step 1: Pull data from BQ (or use cached) ---
    if local_only:
        print("\n\U0001f4c1 Step 1: Using cached data (--local mode)")
        if not LATEST_CSV.exists():
            print("   \u274c No cached CSV found. Run without --local first.")
            sys.exit(1)
    else:
        print("\n\U0001f4e1 Step 1: Pulling fresh data from BigQuery")
        run_bq(QUERY_WTW_WORKORDERS, BQ_RAW_CSV)
        run_bq(QUERY_RACK_SCORES, RACK_CSV, max_rows=10000)
        run_bq(QUERY_LABOR, LABOR_CSV)
        run_bq(QUERY_STORES, PROJECT / 'store_data.json')  # for TnT tab

        # Merge BQ data + rack scores + labor + phases
        print("\n\U0001f527 Step 2: Merging data")
        bq_rows = load_csv(BQ_RAW_CSV)
        rack_map = {
            r['storeNo']: float(r['rack_score'])
            for r in load_csv(RACK_CSV)
        }
        labor_map = {r['tracking_number']: r for r in load_csv(LABOR_CSV)}
        phase_map = load_phase_map()
        merged = merge_data(bq_rows, labor_map, rack_map, phase_map)
        write_csv(merged, LATEST_CSV)
        print_stats(merged)
        print(f"   \u2705 Saved: {LATEST_CSV.name}")

    # --- Step 2: Rebuild HTML tabs ---
    print("\n\U0001f3d7\ufe0f  Step 3: Rebuilding dashboard tabs")
    run_tab_scripts()

    # --- Step 3: Git push ---
    if local_only or no_push:
        print("\n\u23e9 Skipping git push")
    else:
        print("\n\U0001f680 Step 4: Pushing to GitHub")
        git_push()

    print("\n" + "=" * 50)
    print("\U0001f389 Done!")
    print("   GHE: https://gecgithub01.walmart.com/pages/j0s028j/north-bu-hvacr-report-hub/")
    print("   GH:  https://james-savage2026.github.io/tnt-summary-dive/")
    print()


if __name__ == '__main__':
    main()
