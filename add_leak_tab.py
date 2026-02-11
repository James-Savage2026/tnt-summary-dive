#!/usr/bin/env python3
"""Add Leak Management tab to TNT Dashboard — v5 Burn Rate + Walmart colors.

Leak Rate % = (SUM trigger_qty / SUM unique asset charges) × 100
Rates are CALENDAR YEAR. Monthly chart is CUMULATIVE.
Burn Rate = annualized projection based on daily usage pace.
Threshold: 9%.
"""

import json
import csv
import re
import sys
from datetime import date
from pathlib import Path

# Add project dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from leak_tab_html import build_leak_html
from leak_tab_js import build_leak_js

DASHBOARD = Path(__file__).parent / 'index.html'
BQ = Path.home() / 'bigquery_results'

STORE_FILE = BQ / 'leak-store-corrected.csv'
CUMUL_FILE = BQ / 'leak-monthly-cumulative-corrected.csv'

THRESHOLD = 9
# Walmart brand colors
WM_BLUE = '#0053e2'     # blue.100
WM_SPARK = '#ffc220'    # spark.100
WM_RED = '#ea1100'      # red.100
WM_GREEN = '#2a8703'    # green.100


def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def sf(v, d=0):
    try: return float(v)
    except: return d


def si(v, d=0):
    try: return int(float(v))
    except: return d


def compress_stores(rows):
    return [{
        's': r['store_nbr'], 'nm': (r.get('store_name') or '')[:30],
        'city': r.get('city_name', ''), 'st': r.get('state_cd', ''),
        'ban': r.get('banner_desc', ''),
        'srd': r.get('fm_sr_director_name', ''), 'fm': r.get('fm_director_name', ''),
        'rm': r.get('fm_regional_manager_name', ''), 'fsm': r.get('fs_manager_name', ''),
        'mkt': r.get('fs_market', ''),
        'ac': si(r.get('asset_count')), 'sc': round(sf(r.get('total_static_charge')), 1),
        'tl': si(r.get('total_leaks')), 'tq': round(sf(r.get('total_trigger_qty')), 1),
        'cyl': si(r.get('cy_leaks')), 'cytq': round(sf(r.get('cy_trigger_qty')), 1),
        'cylr': round(sf(r.get('cy_leak_rate_pct')), 2),
    } for r in rows]



def build_cumul_data(rows):
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    years = sorted(set(si(r['yr']) for r in rows))
    data = {}
    for r in rows:
        y, m = si(r['yr']), si(r['mo'])
        if y not in data:
            data[y] = [None] * 12
        data[y][m - 1] = round(sf(r.get('cumulative_rate_pct')), 4)
    return {'months': months, 'years': years, 'data': data}


def calc_burn_rate(cy_tq, fleet_charge):
    """Calculate burn rate projection for EOY."""
    today = date.today()
    jan1 = date(today.year, 1, 1)
    days_elapsed = (today - jan1).days or 1
    days_in_year = 366 if today.year % 4 == 0 else 365
    daily_burn = cy_tq / days_elapsed
    projected_eoy_tq = daily_burn * days_in_year
    projected_eoy_rate = (projected_eoy_tq / fleet_charge * 100) if fleet_charge else 0
    threshold_lbs = fleet_charge * THRESHOLD / 100
    if daily_burn > 0 and cy_tq < threshold_lbs:
        days_to_cross = (threshold_lbs - cy_tq) / daily_burn
        cross_day = days_elapsed + days_to_cross
    else:
        cross_day = -1
    return {
        'days_elapsed': days_elapsed,
        'days_in_year': days_in_year,
        'daily_burn_lbs': round(daily_burn, 1),
        'projected_eoy_tq': round(projected_eoy_tq),
        'projected_eoy_rate': round(projected_eoy_rate, 2),
        'cross_day': round(cross_day),
    }


def main():
    print('\U0001f9ca Loading Leak Management data (v5 — Burn Rate)...')
    stores = compress_stores(load_csv(STORE_FILE))
    cumul = build_cumul_data(load_csv(CUMUL_FILE))
    # Derive mgmt from store data (no separate query needed)
    mgmt = []

    fleet_charge = sum(d['sc'] for d in stores)
    cy_tq = sum(d['cytq'] for d in stores)
    cy_leaks = sum(d['cyl'] for d in stores)
    cy_rate = round((cy_tq / fleet_charge * 100), 2) if fleet_charge else 0
    threshold_lbs = round(fleet_charge * THRESHOLD / 100)
    burn = calc_burn_rate(cy_tq, fleet_charge)

    print(f'   Stores: {len(stores):,}')
    print(f'   Fleet charge: {fleet_charge:,.0f} lbs')
    print(f'   CY2026 rate: {cy_rate:.2f}% | Burn rate proj: {burn["projected_eoy_rate"]:.1f}%')
    print(f'   Daily burn: {burn["daily_burn_lbs"]:,.0f} lbs/day')
    print(f'   Day {burn["days_elapsed"]} of {burn["days_in_year"]}')

    store_json = json.dumps(stores, separators=(',', ':'))
    mgmt_json = json.dumps(mgmt, separators=(',', ':'))  # empty, computed client-side
    cumul_json = json.dumps(cumul, separators=(',', ':'))
    burn_json = json.dumps(burn, separators=(',', ':'))

    print('\n\U0001f4dd Reading dashboard HTML...')
    html = DASHBOARD.read_text(encoding='utf-8')

    if '<!-- Leak Tab Content -->' in html:
        print('   Removing old Leak tab...')
        html = re.sub(r'<!-- Leak Tab Content -->.*?<!-- End Leak Tab -->', '', html, flags=re.DOTALL)
        html = re.sub(r'<script>\s*// Leak Management Data.*?</script>', '', html, flags=re.DOTALL)

    if 'tab-leak' not in html:
        btn = '''\n                <button onclick="switchTab('leak')" id="tab-leak"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001f9ca Leak Management
                </button>'''
        html = html.replace('</nav>\n        </div>\n    </div>', btn + '\n            </nav>\n        </div>\n    </div>', 1)

    leak_html = build_leak_html(fleet_charge, cy_tq, cy_rate, cy_leaks, threshold_lbs, burn)
    leak_js = build_leak_js(store_json, mgmt_json, cumul_json, burn_json)

    html = re.sub(r'(\s*<!-- Footer -->)', '\n' + leak_html + '\n\n    <!-- Footer -->', html, count=1)
    html = html.replace('</body>', leak_js + '\n</body>')

    DASHBOARD.write_text(html, encoding='utf-8')
    print(f'\n\u2705 Leak Management tab updated (v5 — Burn Rate + Walmart colors)!')


if __name__ == '__main__':
    main()
