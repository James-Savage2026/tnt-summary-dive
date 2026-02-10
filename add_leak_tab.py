#!/usr/bin/env python3
"""Add Leak Management tab to TNT Dashboard — v2 with correct leak rate logic.

Leak Rate % = (SUM trigger_qty / SUM unique asset charges) × 100
Charge is STATIC per asset (tank capacity). Trigger qty is cumulative (refrigerant added).
Threshold: 9% — over 9% means too much refrigerant loss.
"""

import json
import csv
import re
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parent / 'index.html'
BQ_DIR = Path.home() / 'bigquery_results'

STORE_ROLLUP = BQ_DIR / 'leak-store-rollup-v2-20260210-094209.csv'
MGMT_ROLLUP = BQ_DIR / 'leak-mgmt-rollup-v2-20260210-094208.csv'
MONTHLY_TREND = BQ_DIR / 'leak-monthly-v2-20260210-094205.csv'

THRESHOLD = 9  # 9% leak rate threshold


def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def sf(val, default=0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def si(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def compress_stores(rows):
    """Compress store rollup for JS embedding."""
    return [{
        's': r.get('store_nbr', ''),
        'nm': (r.get('store_name', '') or '')[:30],
        'city': r.get('city_name', ''),
        'st': r.get('state_cd', ''),
        'ban': r.get('banner_desc', ''),
        'srd': r.get('fm_sr_director_name', ''),
        'fm': r.get('fm_director_name', ''),
        'rm': r.get('fm_regional_manager_name', ''),
        'fsm': r.get('fs_manager_name', ''),
        'mkt': r.get('fs_market', ''),
        'ac': si(r.get('asset_count')),
        'sc': round(sf(r.get('total_static_charge')), 1),
        'tl': si(r.get('total_leaks')),
        'tq': round(sf(r.get('total_trigger_qty')), 1),
        'lr': round(sf(r.get('leak_rate_pct')), 2),
        'l12': si(r.get('leaks_last_12mo')),
        'tq12': round(sf(r.get('trigger_qty_last_12mo')), 1),
        'lr12': round(sf(r.get('leak_rate_12mo_pct')), 2),
        'ld': (r.get('latest_leak_date', '') or '')[:10],
    } for r in rows]


def compress_mgmt(rows):
    """Compress management rollup."""
    return [{
        'srd': r.get('sr_dir', ''),
        'fm': r.get('fm_dir', ''),
        'assets': si(r.get('total_assets')),
        'stores': si(r.get('store_count')),
        'charge': round(sf(r.get('total_charge')), 1),
        'leaks': si(r.get('total_leaks')),
        'tq': round(sf(r.get('total_trigger_qty')), 1),
        'lr': round(sf(r.get('leak_rate_pct')), 2),
        'tq12': round(sf(r.get('trigger_qty_12mo')), 1),
        'lr12': round(sf(r.get('leak_rate_12mo_pct')), 2),
    } for r in rows]


def main():
    print('\U0001f9ca Loading Leak Management data (v2)...')

    stores = load_csv(STORE_ROLLUP)
    mgmt = load_csv(MGMT_ROLLUP)
    monthly = load_csv(MONTHLY_TREND)

    compressed = compress_stores(stores)
    mgmt_data = compress_mgmt(mgmt)

    total_leaks = sum(d['tl'] for d in compressed)
    fleet_charge = sum(d['sc'] for d in compressed)
    total_tq = sum(d['tq'] for d in compressed)
    fleet_lr = round((total_tq / fleet_charge * 100) if fleet_charge else 0, 2)
    leaks_12mo = sum(d['l12'] for d in compressed)
    tq_12mo = sum(d['tq12'] for d in compressed)
    lr_12mo = round((tq_12mo / fleet_charge * 100) if fleet_charge else 0, 2)
    stores_over = sum(1 for d in compressed if d['lr12'] > THRESHOLD)

    print(f'   Stores: {len(compressed):,}')
    print(f'   Fleet charge: {fleet_charge:,.0f} lbs (static asset capacity)')
    print(f'   Total trigger qty: {total_tq:,.0f} lbs (refrigerant added)')
    print(f'   All-time leak rate: {fleet_lr:.1f}%')
    print(f'   12mo leak rate: {lr_12mo:.1f}%')
    print(f'   Stores over {THRESHOLD}%: {stores_over:,}')

    monthly_labels = json.dumps([m['month'] for m in monthly])
    monthly_leaks = json.dumps([si(m['total_leaks']) for m in monthly])
    monthly_tq = json.dumps([round(sf(m['total_trigger_qty']), 1) for m in monthly])
    monthly_lr = json.dumps([round(sf(m['monthly_leak_rate_pct']), 4) for m in monthly])

    store_json = json.dumps(compressed, separators=(',', ':'))
    mgmt_json = json.dumps(mgmt_data, separators=(',', ':'))

    print('\n\U0001f4dd Reading dashboard HTML...')
    html = DASHBOARD_PATH.read_text(encoding='utf-8')

    # Remove old leak content
    if '<!-- Leak Tab Content -->' in html:
        print('   Removing old Leak tab...')
        html = re.sub(
            r'<!-- Leak Tab Content -->.*?<!-- End Leak Tab -->',
            '', html, flags=re.DOTALL
        )
        html = re.sub(
            r'<script>\s*// Leak Management Data.*?</script>',
            '', html, flags=re.DOTALL
        )

    # Ensure tab button exists
    if 'tab-leak' not in html:
        leak_tab_btn = '''\n                <button onclick="switchTab('leak')" id="tab-leak"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001f9ca Leak Management
                </button>'''
        html = html.replace(
            '</nav>\n        </div>\n    </div>',
            leak_tab_btn + '\n            </nav>\n        </div>\n    </div>',
            1
        )

    # Ensure switchTab handles leak
    if "'leak-content'" not in html:
        _add_leak_to_switchtab(html)

    leak_html = build_leak_html(
        total_leaks, fleet_charge, total_tq, fleet_lr,
        leaks_12mo, tq_12mo, lr_12mo, stores_over, len(compressed)
    )
    leak_js = build_leak_js(
        store_json, mgmt_json, monthly_labels, monthly_leaks,
        monthly_tq, monthly_lr
    )

    # Insert HTML before Footer
    html = re.sub(
        r'(\s*<!-- Footer -->)',
        '\n' + leak_html + '\n\n    <!-- Footer -->',
        html, count=1
    )
    html = html.replace('</body>', leak_js + '\n</body>')

    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print(f'\n\u2705 Leak Management tab updated (v2)!')
    print(f'   - Correct leak rate: trigger_qty / static_charge')
    print(f'   - {THRESHOLD}% threshold line on charts')
    print(f'   - Management rollup with leak rates')


def build_leak_html(total_leaks, fleet_charge, total_tq, fleet_lr,
                    leaks_12mo, tq_12mo, lr_12mo, stores_over, total_stores):
    lr_color = 'text-red-600' if lr_12mo > THRESHOLD else 'text-green-600'
    return f'''
    <!-- Leak Tab Content -->
    <div id="leak-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- Header -->
            <div class="bg-gradient-to-r from-teal-600 to-cyan-500 rounded-lg shadow-lg p-6 mb-4 text-white">
                <div class="flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold">\U0001f9ca Leak Management</h1>
                        <p class="text-teal-100">Refrigerant Leak Rate Tracking &bull; Threshold: {THRESHOLD}%</p>
                    </div>
                    <div class="text-right">
                        <p class="text-3xl font-bold" id="leakHeaderRate">{lr_12mo:.1f}%</p>
                        <p class="text-sm text-teal-100">12-Month Fleet Leak Rate</p>
                    </div>
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-teal-500">
                    <p class="text-sm text-gray-500 uppercase">Fleet Static Charge</p>
                    <p class="text-2xl font-bold text-teal-600" id="leakKpiCharge">{fleet_charge:,.0f}</p>
                    <p class="text-xs text-gray-400">lbs (asset capacity)</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-amber-500">
                    <p class="text-sm text-gray-500 uppercase">Trigger Qty (12mo)</p>
                    <p class="text-2xl font-bold text-amber-600" id="leakKpiTQ12">{tq_12mo:,.0f}</p>
                    <p class="text-xs text-gray-400">lbs added back</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-{'red' if lr_12mo > THRESHOLD else 'green'}-500">
                    <p class="text-sm text-gray-500 uppercase">12mo Leak Rate</p>
                    <p class="text-2xl font-bold {lr_color}" id="leakKpiRate12">{lr_12mo:.1f}%</p>
                    <p class="text-xs text-gray-400">threshold: {THRESHOLD}%</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
                    <p class="text-sm text-gray-500 uppercase">Stores Over {THRESHOLD}%</p>
                    <p class="text-2xl font-bold text-red-600" id="leakKpiOver">{stores_over:,}</p>
                    <p class="text-xs text-gray-400">of {total_stores:,} stores</p>
                </div>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-cyan-500">
                    <p class="text-sm text-gray-500 uppercase">Leak Events (12mo)</p>
                    <p class="text-2xl font-bold text-cyan-600" id="leakKpiEvents12">{leaks_12mo:,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-indigo-500">
                    <p class="text-sm text-gray-500 uppercase">All-Time Leak Rate</p>
                    <p class="text-2xl font-bold text-indigo-600" id="leakKpiRateAll">{fleet_lr:.1f}%</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                    <p class="text-sm text-gray-500 uppercase">All-Time Trigger Qty</p>
                    <p class="text-2xl font-bold text-purple-600" id="leakKpiTQAll">{total_tq:,.0f}</p>
                    <p class="text-xs text-gray-400">lbs total added</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-gray-500">
                    <p class="text-sm text-gray-500 uppercase">Total Events</p>
                    <p class="text-2xl font-bold text-gray-600" id="leakKpiEventsAll">{total_leaks:,}</p>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-sm font-medium text-gray-700 mb-2">Monthly Leak Rate vs {THRESHOLD}% Threshold</h3>
                    <div style="height: 300px;"><canvas id="leakTrendChart"></canvas></div>
                </div>
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-sm font-medium text-gray-700 mb-2">FM Director 12mo Leak Rate vs {THRESHOLD}% Threshold</h3>
                    <div style="height: 300px;"><canvas id="leakMgmtChart"></canvas></div>
                </div>
            </div>

            <!-- Management Rollup Table -->
            <div class="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div class="p-4 border-b border-gray-200">
                    <h3 class="text-sm font-medium text-gray-700">Management Rollup — Leak Rate by Director</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sr. Director</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">FM Director</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Stores</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Assets</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Static Charge</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Trigger Qty (12mo)</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">12mo Rate</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">All-Time Rate</th>
                            </tr>
                        </thead>
                        <tbody id="leakMgmtTable" class="divide-y divide-gray-200"></tbody>
                    </table>
                </div>
            </div>

            <!-- Filters -->
            <div class="bg-white rounded-lg shadow p-4 mb-6">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-sm font-medium text-gray-700">Store Detail Filters</h3>
                    <button onclick="clearLeakFilters()" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm rounded-md">Clear All</button>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
                    <div>
                        <label class="text-xs text-gray-500">Sr. Director</label>
                        <select id="leakFilterSrDir" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"><option value="">All</option></select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">FM Director</label>
                        <select id="leakFilterFmDir" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"><option value="">All</option></select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">RFM</label>
                        <select id="leakFilterRm" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"><option value="">All</option></select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">FSM</label>
                        <select id="leakFilterFsm" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"><option value="">All</option></select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">Banner</label>
                        <select id="leakFilterBanner" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"><option value="">All</option></select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">Search</label>
                        <input type="text" id="leakSearch" oninput="filterLeakData()" placeholder="Store # or city..." class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                    </div>
                </div>
                <div class="mt-3 flex items-center gap-4">
                    <p class="text-sm text-gray-500">Showing <span id="leakFilteredCount" class="font-bold text-teal-600">0</span> stores</p>
                    <label class="flex items-center gap-1 text-sm text-gray-500">
                        <input type="checkbox" id="leakOverOnly" onchange="filterLeakData()" class="rounded">
                        Over {THRESHOLD}% only (12mo)
                    </label>
                </div>
            </div>

            <!-- Store Table -->
            <div class="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div class="overflow-x-auto" style="max-height: 600px; overflow-y: auto;">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('s')">Store \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Banner</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">RFM</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">FSM</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('ac')">Assets \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('sc')">Charge (lbs) \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('tq12')">Trigger 12mo \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('lr12')">12mo Rate \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('lr')">All-Time Rate \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('ld')">Last Leak \u21C5</th>
                            </tr>
                        </thead>
                        <tbody id="leakStoreTable" class="divide-y divide-gray-200"></tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>
    <!-- End Leak Tab -->
    '''


def build_leak_js(store_json, mgmt_json, monthly_labels, monthly_leaks,
                  monthly_tq, monthly_lr):
    return f'''
    <script>
    // Leak Management Data
    const LEAK_STORES = {store_json};
    const LEAK_MGMT = {mgmt_json};
    const LEAK_M_LABELS = {monthly_labels};
    const LEAK_M_LEAKS = {monthly_leaks};
    const LEAK_M_TQ = {monthly_tq};
    const LEAK_M_LR = {monthly_lr};
    const LEAK_THRESHOLD = {THRESHOLD};

    let leakFilteredData = [];
    let leakSortField = 'lr12';
    let leakSortAsc = false;
    let leakInitialized = false;

    function initLeakTab() {{
        if (leakInitialized) return;
        leakInitialized = true;
        initLeakCharts();
        renderMgmtTable();
        filterLeakData();
    }}

    function updateLeakCascadingFilters() {{
        const srDir = document.getElementById('leakFilterSrDir').value;
        const fmDir = document.getElementById('leakFilterFmDir').value;
        const rm = document.getElementById('leakFilterRm').value;
        const fsm = document.getElementById('leakFilterFsm').value;
        const banner = document.getElementById('leakFilterBanner').value;

        const getValid = (exclude) => LEAK_STORES.filter(s => {{
            if (exclude !== 'srd' && srDir && s.srd !== srDir) return false;
            if (exclude !== 'fm' && fmDir && s.fm !== fmDir) return false;
            if (exclude !== 'rm' && rm && s.rm !== rm) return false;
            if (exclude !== 'fsm' && fsm && s.fsm !== fsm) return false;
            if (exclude !== 'ban' && banner && s.ban !== banner) return false;
            return true;
        }});

        const fill = (id, field, exclude, cur) => {{
            const sel = document.getElementById(id);
            const opts = [...new Set(getValid(exclude).map(s => s[field]).filter(Boolean))].sort();
            sel.innerHTML = '<option value="">All</option>';
            opts.forEach(v => {{ const o = new Option(v, v); if (v === cur) o.selected = true; sel.add(o); }});
            if (cur && !opts.includes(cur)) sel.value = '';
        }};

        fill('leakFilterSrDir', 'srd', 'srd', srDir);
        fill('leakFilterFmDir', 'fm', 'fm', fmDir);
        fill('leakFilterRm', 'rm', 'rm', rm);
        fill('leakFilterFsm', 'fsm', 'fsm', fsm);
        fill('leakFilterBanner', 'ban', 'ban', banner);
    }}

    function filterLeakData() {{
        const srDir = document.getElementById('leakFilterSrDir').value;
        const fmDir = document.getElementById('leakFilterFmDir').value;
        const rm = document.getElementById('leakFilterRm').value;
        const fsm = document.getElementById('leakFilterFsm').value;
        const banner = document.getElementById('leakFilterBanner').value;
        const search = document.getElementById('leakSearch').value.toLowerCase();
        const overOnly = document.getElementById('leakOverOnly').checked;

        leakFilteredData = LEAK_STORES.filter(s => {{
            if (srDir && s.srd !== srDir) return false;
            if (fmDir && s.fm !== fmDir) return false;
            if (rm && s.rm !== rm) return false;
            if (fsm && s.fsm !== fsm) return false;
            if (banner && s.ban !== banner) return false;
            if (overOnly && s.lr12 <= LEAK_THRESHOLD) return false;
            if (search && !(s.s + ' ' + s.nm + ' ' + s.city).toLowerCase().includes(search)) return false;
            return true;
        }});

        document.getElementById('leakFilteredCount').textContent = leakFilteredData.length.toLocaleString();
        updateLeakCascadingFilters();
        updateLeakKpis();
        renderLeakTable();
    }}

    function updateLeakKpis() {{
        let sc = 0, tq12 = 0, tqAll = 0, l12 = 0, lAll = 0, over = 0;
        leakFilteredData.forEach(s => {{
            sc += s.sc; tq12 += s.tq12; tqAll += s.tq;
            l12 += s.l12; lAll += s.tl;
            if (s.lr12 > LEAK_THRESHOLD) over++;
        }});
        const lr12 = sc > 0 ? (tq12 / sc * 100).toFixed(1) : '0.0';
        const lrAll = sc > 0 ? (tqAll / sc * 100).toFixed(1) : '0.0';

        document.getElementById('leakKpiCharge').textContent = Math.round(sc).toLocaleString();
        document.getElementById('leakKpiTQ12').textContent = Math.round(tq12).toLocaleString();
        document.getElementById('leakKpiRate12').textContent = lr12 + '%';
        document.getElementById('leakKpiRate12').className = 'text-2xl font-bold ' + (parseFloat(lr12) > LEAK_THRESHOLD ? 'text-red-600' : 'text-green-600');
        document.getElementById('leakKpiOver').textContent = over.toLocaleString();
        document.getElementById('leakKpiEvents12').textContent = l12.toLocaleString();
        document.getElementById('leakKpiRateAll').textContent = lrAll + '%';
        document.getElementById('leakKpiTQAll').textContent = Math.round(tqAll).toLocaleString();
        document.getElementById('leakKpiEventsAll').textContent = lAll.toLocaleString();
        document.getElementById('leakHeaderRate').textContent = lr12 + '%';
    }}

    function clearLeakFilters() {{
        ['leakFilterSrDir','leakFilterFmDir','leakFilterRm','leakFilterFsm','leakFilterBanner'].forEach(id => document.getElementById(id).value = '');
        document.getElementById('leakSearch').value = '';
        document.getElementById('leakOverOnly').checked = false;
        filterLeakData();
    }}

    function sortLeakTable(field) {{
        if (leakSortField === field) leakSortAsc = !leakSortAsc;
        else {{ leakSortField = field; leakSortAsc = false; }}
        renderLeakTable();
    }}

    function renderMgmtTable() {{
        const table = document.getElementById('leakMgmtTable');
        const sorted = [...LEAK_MGMT].sort((a, b) => b.lr12 - a.lr12);
        table.innerHTML = sorted.map(m => {{
            const rateClass12 = m.lr12 > LEAK_THRESHOLD ? 'bg-red-500 text-white' : 'bg-green-500 text-white';
            const rateClassAll = m.lr > LEAK_THRESHOLD * 5 ? 'bg-red-500 text-white' : m.lr > LEAK_THRESHOLD * 2 ? 'bg-amber-500 text-white' : 'bg-green-500 text-white';
            return `
                <tr class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-sm text-gray-700">${{m.srd || '-'}}</td>
                    <td class="px-3 py-2 text-sm font-medium text-gray-800">${{m.fm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{m.stores}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{m.assets.toLocaleString()}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{Math.round(m.charge).toLocaleString()}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{Math.round(m.tq12).toLocaleString()}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded text-xs font-bold ${{rateClass12}}">${{m.lr12.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded text-xs font-bold ${{rateClassAll}}">${{m.lr.toFixed(1)}}%</span>
                    </td>
                </tr>
            `;
        }}).join('');
    }}

    function renderLeakTable() {{
        const sorted = [...leakFilteredData].sort((a, b) => {{
            let av = a[leakSortField], bv = b[leakSortField];
            if (typeof av === 'number') {{ /* numeric */ }}
            else {{ av = av || ''; bv = bv || ''; }}
            if (av < bv) return leakSortAsc ? -1 : 1;
            if (av > bv) return leakSortAsc ? 1 : -1;
            return 0;
        }});
        const display = sorted.slice(0, 300);
        const table = document.getElementById('leakStoreTable');
        table.innerHTML = display.map(s => {{
            const ban = s.ban && s.ban.includes('Sam')
                ? '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-800 text-white">Sam&#39;s</span>'
                : '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-400 text-blue-900">WM</span>';
            const r12Class = s.lr12 > LEAK_THRESHOLD ? 'bg-red-500 text-white' : s.lr12 > LEAK_THRESHOLD * 0.7 ? 'bg-amber-500 text-white' : 'bg-green-500 text-white';
            const rAllClass = s.lr > LEAK_THRESHOLD * 5 ? 'bg-red-500 text-white' : s.lr > LEAK_THRESHOLD * 2 ? 'bg-amber-500 text-white' : 'bg-green-500 text-white';
            return `
                <tr class="hover:bg-gray-50 ${{s.lr12 > LEAK_THRESHOLD ? 'bg-red-50' : ''}}">
                    <td class="px-3 py-2 text-sm font-medium text-teal-700">${{s.s}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.city}}${{s.city && s.st ? ', ' : ''}}${{s.st}}</td>
                    <td class="px-3 py-2 text-center">${{ban}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.rm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.fsm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-center text-gray-700">${{s.ac}}</td>
                    <td class="px-3 py-2 text-sm text-center text-gray-700">${{Math.round(s.sc).toLocaleString()}}</td>
                    <td class="px-3 py-2 text-sm text-center text-gray-700">${{Math.round(s.tq12).toLocaleString()}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded text-xs font-bold ${{r12Class}}">${{s.lr12.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded text-xs font-bold ${{rAllClass}}">${{s.lr.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-2 text-sm text-center text-gray-500">${{s.ld}}</td>
                </tr>
            `;
        }}).join('');
        if (sorted.length > 300) {{
            table.innerHTML += `<tr><td colspan="11" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} stores. Use filters.</td></tr>`;
        }}
    }}

    function initLeakCharts() {{
        // Monthly trend — leak rate % with threshold line
        const trendCtx = document.getElementById('leakTrendChart').getContext('2d');
        new Chart(trendCtx, {{
            type: 'bar',
            data: {{
                labels: LEAK_M_LABELS,
                datasets: [{{
                    label: 'Monthly Leak Rate %',
                    data: LEAK_M_LR,
                    backgroundColor: LEAK_M_LR.map(v => v > (LEAK_THRESHOLD / 12) ? 'rgba(234,17,0,0.7)' : 'rgba(42,135,3,0.7)'),
                    borderRadius: 3,
                    order: 2
                }}, {{
                    label: LEAK_THRESHOLD + '% Annual (÷12 monthly)',
                    data: Array(LEAK_M_LABELS.length).fill(LEAK_THRESHOLD / 12),
                    type: 'line',
                    borderColor: '#ea1100',
                    borderDash: [6, 3],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    order: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
                    datalabels: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, title: {{ display: true, text: 'Leak Rate %' }} }}
                }}
            }}
        }});

        // FM Director bar chart — 12mo leak rate vs threshold
        const mgmtSorted = [...LEAK_MGMT].sort((a, b) => b.lr12 - a.lr12);
        const mgmtCtx = document.getElementById('leakMgmtChart').getContext('2d');
        new Chart(mgmtCtx, {{
            type: 'bar',
            data: {{
                labels: mgmtSorted.map(m => m.fm || 'Unknown'),
                datasets: [{{
                    label: '12mo Leak Rate %',
                    data: mgmtSorted.map(m => m.lr12),
                    backgroundColor: mgmtSorted.map(m => m.lr12 > LEAK_THRESHOLD ? 'rgba(234,17,0,0.7)' : 'rgba(42,135,3,0.7)'),
                    borderRadius: 3
                }}, {{
                    label: LEAK_THRESHOLD + '% Threshold',
                    data: Array(mgmtSorted.length).fill(LEAK_THRESHOLD),
                    type: 'line',
                    borderColor: '#ea1100',
                    borderDash: [6, 3],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
                    datalabels: {{
                        anchor: 'end', align: 'end',
                        color: '#333', font: {{ size: 9, weight: 'bold' }},
                        formatter: v => v.toFixed(1) + '%'
                    }}
                }},
                scales: {{
                    x: {{ beginAtZero: true, title: {{ display: true, text: 'Leak Rate %' }} }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
    }}
    </script>
    '''


if __name__ == '__main__':
    main()
