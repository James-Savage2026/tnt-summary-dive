#!/usr/bin/env python3
"""Add Leak Management tab to TNT Dashboard"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime

DASHBOARD_PATH = Path(__file__).parent / 'index.html'
BQ_DIR = Path.home() / 'bigquery_results'

STORE_ROLLUP = BQ_DIR / 'leak-store-rollup-20260210-091402.csv'
MONTHLY_TREND = BQ_DIR / 'leak-monthly-trend-20260210-091103.csv'
YEARLY_TREND = BQ_DIR / 'leak-yearly-trend-20260210-090542.csv'
REFRIG_TYPES = BQ_DIR / 'leak-refrigerant-types-20260210-091334.csv'


def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def safe_float(val, default=0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def build_compressed_store_data(rows):
    """Compress store rollup for embedding in HTML."""
    compressed = []
    for r in rows:
        compressed.append({
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
            'tl': safe_int(r.get('total_leaks')),
            'tc': safe_float(r.get('total_charge_lbs')),
            'tq': safe_float(r.get('total_trigger_qty')),
            'at': safe_int(r.get('leaks_above_trigger')),
            'alr': safe_float(r.get('avg_leak_rate')),
            'l12': safe_int(r.get('leaks_last_12mo')),
            'c12': safe_float(r.get('charge_last_12mo')),
            'ref': r.get('top_refrigerant', ''),
            'fc': r.get('top_fault_code', ''),
            'ld': (r.get('latest_leak_date', '') or '')[:10],
        })
    return compressed


def main():
    print('\U0001f9ca Loading Leak Management data...')

    stores = load_csv(STORE_ROLLUP)
    monthly = load_csv(MONTHLY_TREND)
    yearly = load_csv(YEARLY_TREND)
    refrig = load_csv(REFRIG_TYPES)

    print(f'   Stores with leaks: {len(stores)}')
    print(f'   Monthly trend rows: {len(monthly)}')
    print(f'   Yearly trend rows: {len(yearly)}')
    print(f'   Refrigerant types: {len(refrig)}')

    compressed = build_compressed_store_data(stores)

    # Summary stats
    total_leaks = sum(d['tl'] for d in compressed)
    total_charge = sum(d['tc'] for d in compressed)
    total_stores = len(compressed)
    leaks_12mo = sum(d['l12'] for d in compressed)
    charge_12mo = sum(d['c12'] for d in compressed)
    above_trigger = sum(d['at'] for d in compressed)

    print(f'   Total leaks: {total_leaks:,}')
    print(f'   Total charge: {total_charge:,.0f} lbs')
    print(f'   Leaks last 12mo: {leaks_12mo:,}')

    # Monthly trend data for chart
    monthly_labels = json.dumps([m['month'] for m in monthly])
    monthly_leaks = json.dumps([safe_int(m['total_leaks']) for m in monthly])
    monthly_charge = json.dumps([safe_float(m['total_charge_lbs']) for m in monthly])
    monthly_stores = json.dumps([safe_int(m['stores_affected']) for m in monthly])

    # Refrigerant type data for chart (top 8 + Other)
    refrig_sorted = sorted(refrig, key=lambda x: safe_int(x['total_leaks']), reverse=True)
    top_refrig = refrig_sorted[:8]
    other_leaks = sum(safe_int(r['total_leaks']) for r in refrig_sorted[8:])
    refrig_labels = json.dumps([r['refrigerant_type_name'] for r in top_refrig] + ['Other'])
    refrig_counts = json.dumps([safe_int(r['total_leaks']) for r in top_refrig] + [other_leaks])

    # Yearly by Sr Director for chart
    yearly_data = json.dumps([{
        'y': safe_int(r['leak_year']),
        'srd': r.get('sr_director', ''),
        'leaks': safe_int(r['total_leaks']),
        'charge': safe_float(r['total_charge_lbs']),
        'stores': safe_int(r['stores_affected']),
    } for r in yearly])

    store_json = json.dumps(compressed, separators=(',', ':'))

    print('\n\U0001f4dd Reading dashboard HTML...')
    html = DASHBOARD_PATH.read_text(encoding='utf-8')

    # Remove old leak content if exists
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

    # Add tab button if not exists
    if 'tab-leak' not in html:
        html = html.replace(
            "onclick=\"switchTab('wtw')\" id=\"tab-wtw\"",
            "onclick=\"switchTab('wtw')\" id=\"tab-wtw\""
        )
        leak_tab_btn = '''\n                <button onclick="switchTab('leak')" id="tab-leak"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001f9ca Leak Management
                </button>'''
        html = html.replace(
            '</nav>\n        </div>\n    </div>',
            leak_tab_btn + '\n            </nav>\n        </div>\n    </div>',
            1
        )

    # Update switchTab to handle leak tab
    if "'leak-content'" not in html:
        html = html.replace(
            "document.getElementById('wtw-content').classList.remove('hidden');",
            "document.getElementById('wtw-content').classList.remove('hidden');\n"
            "            document.getElementById('leak-content').classList.add('hidden');"
        )
        html = html.replace(
            "document.getElementById('wtw-content').classList.add('hidden');\n"
            "            initWtwTab();",
            "document.getElementById('wtw-content').classList.add('hidden');\n"
            "            document.getElementById('leak-content').classList.add('hidden');\n"
            "            initWtwTab();"
        )
        # Add leak case to switchTab
        old_switch = """if (tab === 'tnt') {
            document.getElementById('tnt-content').classList.remove('hidden');
            document.getElementById('wtw-content').classList.add('hidden');"""
        new_switch = """if (tab === 'tnt') {
            document.getElementById('tnt-content').classList.remove('hidden');
            document.getElementById('wtw-content').classList.add('hidden');
            document.getElementById('leak-content').classList.add('hidden');"""
        html = html.replace(old_switch, new_switch)

        # Add leak tab switch case before closing of switchTab
        old_else = """} else {
            document.getElementById('tnt-content').classList.add('hidden');
            document.getElementById('wtw-content').classList.remove('hidden');"""
        new_else = """} else if (tab === 'wtw') {
            document.getElementById('tnt-content').classList.add('hidden');
            document.getElementById('wtw-content').classList.remove('hidden');
            document.getElementById('leak-content').classList.add('hidden');"""
        html = html.replace(old_else, new_else)

        # Add leak else clause
        html = html.replace(
            "initWtwTab();\n        }",
            "initWtwTab();\n        } else if (tab === 'leak') {\n"
            "            document.getElementById('tnt-content').classList.add('hidden');\n"
            "            document.getElementById('wtw-content').classList.add('hidden');\n"
            "            document.getElementById('leak-content').classList.remove('hidden');\n"
            "            initLeakTab();\n"
            "        }",
            1
        )

    # Build leak tab HTML
    leak_html = f'''
    <!-- Leak Tab Content -->
    <div id="leak-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- Header -->
            <div class="bg-gradient-to-r from-teal-600 to-cyan-500 rounded-lg shadow-lg p-6 mb-4 text-white">
                <div class="flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold">\U0001f9ca Leak Management</h1>
                        <p class="text-teal-100">Refrigerant Leak Tracking &amp; Analysis</p>
                    </div>
                    <div class="text-right">
                        <p class="text-3xl font-bold" id="leakTotalCount">{total_leaks:,}</p>
                        <p class="text-sm text-teal-100">Total Leak Records</p>
                    </div>
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-teal-500">
                    <p class="text-sm text-gray-500 uppercase">Total Leaks</p>
                    <p class="text-2xl font-bold text-teal-600" id="leakKpiTotal">{total_leaks:,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-cyan-500">
                    <p class="text-sm text-gray-500 uppercase">Last 12 Months</p>
                    <p class="text-2xl font-bold text-cyan-600" id="leakKpi12mo">{leaks_12mo:,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
                    <p class="text-sm text-gray-500 uppercase">Above Trigger</p>
                    <p class="text-2xl font-bold text-red-600" id="leakKpiAbove">{above_trigger:,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-indigo-500">
                    <p class="text-sm text-gray-500 uppercase">Total Charge</p>
                    <p class="text-2xl font-bold text-indigo-600" id="leakKpiCharge">{total_charge:,.0f}</p>
                    <p class="text-xs text-gray-400">lbs refrigerant</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-amber-500">
                    <p class="text-sm text-gray-500 uppercase">Charge (12mo)</p>
                    <p class="text-2xl font-bold text-amber-600" id="leakKpiCharge12">{charge_12mo:,.0f}</p>
                    <p class="text-xs text-gray-400">lbs refrigerant</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                    <p class="text-sm text-gray-500 uppercase">Stores Affected</p>
                    <p class="text-2xl font-bold text-purple-600" id="leakKpiStores">{total_stores:,}</p>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-sm font-medium text-gray-700 mb-2">Monthly Leak Trend (24 Months)</h3>
                    <div style="height: 280px;"><canvas id="leakTrendChart"></canvas></div>
                </div>
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-sm font-medium text-gray-700 mb-2">Refrigerant Type Breakdown</h3>
                    <div style="height: 280px;"><canvas id="leakRefrigChart"></canvas></div>
                </div>
            </div>

            <!-- Filters -->
            <div class="bg-white rounded-lg shadow p-4 mb-6">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-sm font-medium text-gray-700">Filters</h3>
                    <button onclick="clearLeakFilters()" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm rounded-md">Clear All</button>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
                    <div>
                        <label class="text-xs text-gray-500">Sr. Director</label>
                        <select id="leakFilterSrDir" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                            <option value="">All</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">FM Director</label>
                        <select id="leakFilterFmDir" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                            <option value="">All</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">RFM</label>
                        <select id="leakFilterRm" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                            <option value="">All</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">FSM</label>
                        <select id="leakFilterFsm" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                            <option value="">All</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">Banner</label>
                        <select id="leakFilterBanner" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                            <option value="">All</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-gray-500">Search</label>
                        <input type="text" id="leakSearch" oninput="filterLeakData()" placeholder="Store # or city..." class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                    </div>
                </div>
                <div class="mt-3 flex items-center gap-4">
                    <p class="text-sm text-gray-500">Showing <span id="leakFilteredCount" class="font-bold text-teal-600">0</span> stores</p>
                    <label class="flex items-center gap-1 text-sm text-gray-500">
                        <input type="checkbox" id="leakAboveOnly" onchange="filterLeakData()" class="rounded">
                        Above trigger only
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
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('tl')">Total Leaks \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('l12')">Last 12mo \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('tc')">Charge (lbs) \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('at')">Above Trigger \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Top Refrigerant</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Top Fault</th>
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

    leak_js = f'''
    <script>
    // Leak Management Data
    const LEAK_STORES = {store_json};
    const LEAK_MONTHLY_LABELS = {monthly_labels};
    const LEAK_MONTHLY_LEAKS = {monthly_leaks};
    const LEAK_MONTHLY_CHARGE = {monthly_charge};
    const LEAK_MONTHLY_STORES = {monthly_stores};
    const LEAK_REFRIG_LABELS = {refrig_labels};
    const LEAK_REFRIG_COUNTS = {refrig_counts};
    const LEAK_YEARLY = {yearly_data};

    let leakFilteredData = [];
    let leakSortField = 'tl';
    let leakSortAsc = false;
    let leakInitialized = false;
    let leakTrendChart = null;
    let leakRefrigChart = null;

    function initLeakTab() {{
        if (leakInitialized) return;
        leakInitialized = true;
        initLeakCharts();
        filterLeakData();
    }}

    function updateLeakCascadingFilters() {{
        const srDir = document.getElementById('leakFilterSrDir').value;
        const fmDir = document.getElementById('leakFilterFmDir').value;
        const rm = document.getElementById('leakFilterRm').value;
        const fsm = document.getElementById('leakFilterFsm').value;
        const banner = document.getElementById('leakFilterBanner').value;

        const getValid = (excludeField) => {{
            return LEAK_STORES.filter(s => {{
                if (excludeField !== 'srd' && srDir && s.srd !== srDir) return false;
                if (excludeField !== 'fm' && fmDir && s.fm !== fmDir) return false;
                if (excludeField !== 'rm' && rm && s.rm !== rm) return false;
                if (excludeField !== 'fsm' && fsm && s.fsm !== fsm) return false;
                if (excludeField !== 'ban' && banner && s.ban !== banner) return false;
                return true;
            }});
        }};

        const updateSel = (id, field, exclude, cur) => {{
            const sel = document.getElementById(id);
            const opts = [...new Set(getValid(exclude).map(s => s[field]).filter(Boolean))].sort();
            sel.innerHTML = '<option value="">All</option>';
            opts.forEach(v => {{
                const o = new Option(v, v);
                if (v === cur) o.selected = true;
                sel.add(o);
            }});
            if (cur && !opts.includes(cur)) sel.value = '';
        }};

        updateSel('leakFilterSrDir', 'srd', 'srd', srDir);
        updateSel('leakFilterFmDir', 'fm', 'fm', fmDir);
        updateSel('leakFilterRm', 'rm', 'rm', rm);
        updateSel('leakFilterFsm', 'fsm', 'fsm', fsm);
        updateSel('leakFilterBanner', 'ban', 'ban', banner);
    }}

    function filterLeakData() {{
        const srDir = document.getElementById('leakFilterSrDir').value;
        const fmDir = document.getElementById('leakFilterFmDir').value;
        const rm = document.getElementById('leakFilterRm').value;
        const fsm = document.getElementById('leakFilterFsm').value;
        const banner = document.getElementById('leakFilterBanner').value;
        const search = document.getElementById('leakSearch').value.toLowerCase();
        const aboveOnly = document.getElementById('leakAboveOnly').checked;

        leakFilteredData = LEAK_STORES.filter(s => {{
            if (srDir && s.srd !== srDir) return false;
            if (fmDir && s.fm !== fmDir) return false;
            if (rm && s.rm !== rm) return false;
            if (fsm && s.fsm !== fsm) return false;
            if (banner && s.ban !== banner) return false;
            if (aboveOnly && s.at === 0) return false;
            if (search) {{
                const str = (s.s + ' ' + s.nm + ' ' + s.city).toLowerCase();
                if (!str.includes(search)) return false;
            }}
            return true;
        }});

        document.getElementById('leakFilteredCount').textContent = leakFilteredData.length.toLocaleString();
        updateLeakCascadingFilters();
        updateLeakKpis();
        renderLeakTable();
    }}

    function updateLeakKpis() {{
        let tl = 0, l12 = 0, at = 0, tc = 0, c12 = 0;
        leakFilteredData.forEach(s => {{
            tl += s.tl; l12 += s.l12; at += s.at;
            tc += s.tc; c12 += s.c12;
        }});
        document.getElementById('leakKpiTotal').textContent = tl.toLocaleString();
        document.getElementById('leakKpi12mo').textContent = l12.toLocaleString();
        document.getElementById('leakKpiAbove').textContent = at.toLocaleString();
        document.getElementById('leakKpiCharge').textContent = Math.round(tc).toLocaleString();
        document.getElementById('leakKpiCharge12').textContent = Math.round(c12).toLocaleString();
        document.getElementById('leakKpiStores').textContent = leakFilteredData.length.toLocaleString();
    }}

    function clearLeakFilters() {{
        document.getElementById('leakFilterSrDir').value = '';
        document.getElementById('leakFilterFmDir').value = '';
        document.getElementById('leakFilterRm').value = '';
        document.getElementById('leakFilterFsm').value = '';
        document.getElementById('leakFilterBanner').value = '';
        document.getElementById('leakSearch').value = '';
        document.getElementById('leakAboveOnly').checked = false;
        filterLeakData();
    }}

    function sortLeakTable(field) {{
        if (leakSortField === field) {{ leakSortAsc = !leakSortAsc; }}
        else {{ leakSortField = field; leakSortAsc = false; }}
        renderLeakTable();
    }}

    function renderLeakTable() {{
        const sorted = [...leakFilteredData].sort((a, b) => {{
            let av = a[leakSortField], bv = b[leakSortField];
            if (typeof av === 'number') {{ }}
            else {{ av = av || ''; bv = bv || ''; }}
            if (av < bv) return leakSortAsc ? -1 : 1;
            if (av > bv) return leakSortAsc ? 1 : -1;
            return 0;
        }});
        const display = sorted.slice(0, 300);
        const table = document.getElementById('leakStoreTable');
        table.innerHTML = display.map(s => {{
            const banBadge = s.ban && s.ban.includes('Sam')
                ? '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-800 text-white">Sam&#39;s</span>'
                : '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-400 text-blue-900">WM</span>';
            const triggerPct = s.tq > 0 ? ((s.at / s.tl) * 100).toFixed(0) : 0;
            return `
                <tr class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-sm font-medium text-teal-700">${{s.s}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.city}}${{s.city && s.st ? ', ' : ''}}${{s.st}}</td>
                    <td class="px-3 py-2 text-center">${{banBadge}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.rm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{s.fsm || '-'}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded text-xs font-bold ${{s.tl >= 50 ? 'bg-red-500 text-white' : s.tl >= 20 ? 'bg-amber-500 text-white' : 'bg-gray-100 text-gray-800'}}">${{s.tl.toLocaleString()}}</span>
                    </td>
                    <td class="px-3 py-2 text-center">
                        <span class="font-semibold ${{s.l12 >= 10 ? 'text-red-600' : 'text-gray-700'}}">${{s.l12}}</span>
                    </td>
                    <td class="px-3 py-2 text-sm text-center text-gray-700">${{Math.round(s.tc).toLocaleString()}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-0.5 rounded text-xs ${{s.at > 0 ? 'bg-red-100 text-red-700 font-bold' : 'bg-green-100 text-green-700'}}">
                            ${{s.at}} (${{triggerPct}}%)
                        </span>
                    </td>
                    <td class="px-3 py-2 text-xs text-gray-600">${{s.ref || '-'}}</td>
                    <td class="px-3 py-2 text-xs text-gray-600">${{s.fc || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-center text-gray-500">${{s.ld}}</td>
                </tr>
            `;
        }}).join('');
        if (sorted.length > 300) {{
            table.innerHTML += `<tr><td colspan="12" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} stores. Use filters to narrow down.</td></tr>`;
        }}
    }}

    function initLeakCharts() {{
        // Monthly trend
        const trendCtx = document.getElementById('leakTrendChart').getContext('2d');
        leakTrendChart = new Chart(trendCtx, {{
            type: 'line',
            data: {{
                labels: LEAK_MONTHLY_LABELS,
                datasets: [{{
                    label: 'Leak Events',
                    data: LEAK_MONTHLY_LEAKS,
                    borderColor: '#0053e2',
                    backgroundColor: 'rgba(0,83,226,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3
                }}, {{
                    label: 'Stores Affected',
                    data: LEAK_MONTHLY_STORES,
                    borderColor: '#2a8703',
                    backgroundColor: 'rgba(42,135,3,0.05)',
                    fill: false,
                    tension: 0.3,
                    pointRadius: 3,
                    borderDash: [5, 5]
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
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});

        // Refrigerant doughnut
        const refrigCtx = document.getElementById('leakRefrigChart').getContext('2d');
        leakRefrigChart = new Chart(refrigCtx, {{
            type: 'doughnut',
            data: {{
                labels: LEAK_REFRIG_LABELS,
                datasets: [{{
                    data: LEAK_REFRIG_COUNTS,
                    backgroundColor: [
                        '#0053e2', '#2a8703', '#ffc220', '#ea1100',
                        '#6366f1', '#06b6d4', '#f97316', '#8b5cf6', '#9ca3af'
                    ],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right', labels: {{ boxWidth: 12, padding: 10, font: {{ size: 10 }} }} }},
                    datalabels: {{
                        color: '#fff',
                        font: {{ weight: 'bold', size: 10 }},
                        formatter: (value, ctx) => {{
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((value / total) * 100).toFixed(0);
                            return pct > 5 ? pct + '%' : '';
                        }}
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
    }}
    </script>
    '''

    # Insert before Footer
    html = re.sub(
        r'(\s*<!-- Footer -->)',
        '\n' + leak_html + '\n\n    <!-- Footer -->',
        html, count=1
    )

    # Add JS before closing body
    html = html.replace('</body>', leak_js + '\n</body>')

    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print(f'\n\u2705 Leak Management tab added!')
    print(f'   - {len(stores):,} stores with leak data')
    print(f'   - {total_leaks:,} total leak records')
    print(f'   - Monthly trend chart (24 months)')
    print(f'   - Refrigerant type breakdown')
    print(f'   - Cascading management filters')


if __name__ == '__main__':
    main()
