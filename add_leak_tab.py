#!/usr/bin/env python3
"""Add Leak Management tab to TNT Dashboard — v4 CY2026 + cumulative.

Leak Rate % = (SUM trigger_qty / SUM unique asset charges) × 100
Rates are CALENDAR YEAR. Monthly chart is CUMULATIVE.
Threshold: 9%.
"""

import json
import csv
import re
from pathlib import Path

DASHBOARD = Path(__file__).parent / 'index.html'
BQ = Path.home() / 'bigquery_results'

STORE_FILE = BQ / 'leak-store-cy2026-20260210-100447.csv'
MGMT_FILE = BQ / 'leak-mgmt-cy2026-20260210-100441.csv'
CUMUL_FILE = BQ / 'leak-monthly-cumulative-20260210-100208.csv'
LOC_FILE = BQ / 'leak-locations-20260210-095157.csv'

THRESHOLD = 9


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
        'ld': (r.get('latest_leak_date') or '')[:10],
    } for r in rows]


def compress_mgmt(rows):
    return [{
        'srd': r.get('sr_dir', ''), 'fm': r.get('fm_dir', ''),
        'assets': si(r.get('total_assets')), 'stores': si(r.get('store_count')),
        'charge': round(sf(r.get('total_charge')), 1),
        'cyl': si(r.get('cy_leaks')),
        'cytq': round(sf(r.get('cy_trigger_qty')), 1),
        'cylr': round(sf(r.get('cy_leak_rate_pct')), 2),
    } for r in rows]


def build_cumul_data(rows):
    """Build cumulative monthly data per year."""
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    years = sorted(set(si(r['yr']) for r in rows))
    data = {}
    for r in rows:
        y = si(r['yr'])
        m = si(r['mo'])
        if y not in data:
            data[y] = [None] * 12
        data[y][m - 1] = round(sf(r.get('cumulative_rate_pct')), 4)
    return {'months': months, 'years': years, 'data': data}


def main():
    print('🧊 Loading Leak Management data (v4 — CY2026)...')

    stores_raw = load_csv(STORE_FILE)
    mgmt_raw = load_csv(MGMT_FILE)
    cumul_raw = load_csv(CUMUL_FILE)
    locations = load_csv(LOC_FILE)

    stores = compress_stores(stores_raw)
    mgmt = compress_mgmt(mgmt_raw)
    cumul = build_cumul_data(cumul_raw)

    # Fleet totals
    fleet_charge = sum(d['sc'] for d in stores)
    cy_tq = sum(d['cytq'] for d in stores)
    cy_leaks = sum(d['cyl'] for d in stores)
    cy_rate = round((cy_tq / fleet_charge * 100), 2) if fleet_charge else 0
    threshold_lbs = round(fleet_charge * THRESHOLD / 100)
    stores_over = sum(1 for d in stores if d['cylr'] > THRESHOLD)

    loc_data = [{
        'name': l.get('leak_location_name', ''),
        'events': si(l.get('leak_events')),
        'avg': round(sf(l.get('avg_amount_added')), 1),
    } for l in locations[:25]]

    print(f'   Stores: {len(stores):,}')
    print(f'   Fleet charge: {fleet_charge:,.0f} lbs')
    print(f'   CY2026 leak rate: {cy_rate:.2f}%')
    print(f'   CY2026 trigger qty: {cy_tq:,.0f} lbs')
    print(f'   CY2026 leak events: {cy_leaks:,}')
    print(f'   Stores over {THRESHOLD}%: {stores_over:,}')

    store_json = json.dumps(stores, separators=(',', ':'))
    mgmt_json = json.dumps(mgmt, separators=(',', ':'))
    loc_json = json.dumps(loc_data, separators=(',', ':'))
    cumul_json = json.dumps(cumul, separators=(',', ':'))

    print('\n📝 Reading dashboard HTML...')
    html = DASHBOARD.read_text(encoding='utf-8')

    if '<!-- Leak Tab Content -->' in html:
        print('   Removing old Leak tab...')
        html = re.sub(r'<!-- Leak Tab Content -->.*?<!-- End Leak Tab -->', '', html, flags=re.DOTALL)
        html = re.sub(r'<script>\s*// Leak Management Data.*?</script>', '', html, flags=re.DOTALL)

    if 'tab-leak' not in html:
        btn = '''\n                <button onclick="switchTab('leak')" id="tab-leak"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    🧊 Leak Management
                </button>'''
        html = html.replace('</nav>\n        </div>\n    </div>', btn + '\n            </nav>\n        </div>\n    </div>', 1)

    leak_html = _build_html(fleet_charge, cy_tq, cy_rate, cy_leaks, threshold_lbs, stores_over, len(stores))
    leak_js = _build_js(store_json, mgmt_json, loc_json, cumul_json)

    html = re.sub(r'(\s*<!-- Footer -->)', '\n' + leak_html + '\n\n    <!-- Footer -->', html, count=1)
    html = html.replace('</body>', leak_js + '\n</body>')

    DASHBOARD.write_text(html, encoding='utf-8')
    print(f'\n✅ Leak Management tab updated (v4 — CY2026 + cumulative)!')


def _build_html(fleet_charge, cy_tq, cy_rate, cy_leaks, threshold_lbs, stores_over, total_stores):
    T = THRESHOLD
    rate_color = 'text-red-600' if cy_rate > T else 'text-green-600'
    bar_pct = min(100, (cy_tq / threshold_lbs * 100)) if threshold_lbs else 0
    bar_color = '#c00' if cy_tq > threshold_lbs else '#70ad47'
    remain = max(0, threshold_lbs - cy_tq)
    remain_color = 'text-red-600' if remain <= 0 else 'text-green-600'
    added_color = 'text-red-600' if cy_tq > threshold_lbs else 'text-green-600'

    return f'''
    <!-- Leak Tab Content -->
    <div id="leak-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">

            <!-- Header -->
            <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
                <div class="flex items-center gap-3 mb-4">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/Walmart_logo.svg" alt="Walmart" class="h-8" crossorigin="anonymous">
                    <div>
                        <h1 class="text-xl font-bold text-gray-800">Refrigerant Leak Report — CY2026</h1>
                        <p class="text-xs text-gray-400">Calendar Year 2026 &bull; Cumulative Leak Rates</p>
                    </div>
                </div>

                <!-- KPI Bar -->
                <div class="grid grid-cols-2 md:grid-cols-5 gap-0">
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">{T}% Leak Rate Threshold (lbs)</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiThreshold">{threshold_lbs:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">CY2026 Leak Rate</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold {rate_color}" id="lkKpiRate">{cy_rate:.2f}%</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">Total # of Leak Records</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiRecords">{cy_leaks:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">CY2026 Amount Added (lbs)</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiAdded">{cy_tq:,.1f}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">Full Charge Total</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiCharge">{fleet_charge:,.0f}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Threshold Bar + Cumulative YoY Chart -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <!-- Threshold Progress Bar -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">{T}% Leak Rate Threshold (lbs)</div>
                    <div class="flex items-center gap-3">
                        <span class="text-sm text-gray-500 whitespace-nowrap" id="lkBarLabel">All Stores</span>
                        <div class="flex-1 relative">
                            <div class="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                                <div id="lkThresholdBar" class="h-8 rounded-full transition-all duration-500"
                                     style="width: {bar_pct:.0f}%; background: {bar_color};"></div>
                            </div>
                            <div class="absolute top-0 right-0 h-8 flex items-center">
                                <span class="bg-gray-700 text-white text-xs px-1.5 py-0.5 rounded">{T}%</span>
                            </div>
                        </div>
                        <span class="text-sm font-bold text-gray-700 whitespace-nowrap" id="lkBarValue">{cy_tq:,.0f} lbs</span>
                    </div>
                    <div class="mt-3 grid grid-cols-3 gap-2 text-center">
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Threshold</p>
                            <p class="text-sm font-bold text-gray-700" id="lkThreshLbs">{threshold_lbs:,} lbs</p>
                        </div>
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Added CY2026</p>
                            <p class="text-sm font-bold {added_color}" id="lkAddedLbs">{cy_tq:,.0f} lbs</p>
                        </div>
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Remaining</p>
                            <p class="text-sm font-bold {remain_color}" id="lkRemainLbs">{remain:,.0f} lbs</p>
                        </div>
                    </div>
                </div>

                <!-- Cumulative YoY Chart -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">Monthly Cumulative Leak Rate vs {T}% Threshold</div>
                    <div style="height: 250px;"><canvas id="leakYoyChart"></canvas></div>
                </div>
            </div>

            <!-- FM Director Chart + Leak Location -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">FM Director CY2026 Leak Rate vs {T}%</div>
                    <div style="height: 350px;"><canvas id="leakMgmtChart"></canvas></div>
                </div>
                <div class="bg-white rounded-lg shadow overflow-hidden">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold text-center">Leak Location</div>
                    <div class="overflow-y-auto" style="max-height: 380px;">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50 sticky top-0">
                                <tr>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Leak Location Name</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Avg Added</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Leak Events</th>
                                </tr>
                            </thead>
                            <tbody id="leakLocTable" class="divide-y divide-gray-200"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Filters -->
            <div class="bg-white rounded-lg shadow p-4 mb-4">
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
                        <input type="text" id="leakSearch" oninput="filterLeakData()" placeholder="Store # or city" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
                    </div>
                </div>
                <div class="mt-3 flex items-center gap-4">
                    <p class="text-sm text-gray-500">Showing <span id="leakFilteredCount" class="font-bold text-teal-600">0</span> stores</p>
                    <label class="flex items-center gap-1 text-sm text-gray-500">
                        <input type="checkbox" id="leakOverOnly" onchange="filterLeakData()" class="rounded">
                        Over {T}% only (CY2026)
                    </label>
                </div>
            </div>

            <!-- Store Table -->
            <div class="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold text-center">Store Summary</div>
                <div class="overflow-x-auto" style="max-height: 600px; overflow-y: auto;">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('s')">Store \u21C5</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Type</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Market</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">RFM</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('ac')">Assets \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('sc')">Charge \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cytq')">Added CY26 \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cylr')">CY26 Rate \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cyl')">Events \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
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


def _build_js(store_json, mgmt_json, loc_json, cumul_json):
    T = THRESHOLD
    return f'''
    <script>
    // Leak Management Data
    const LK_STORES = {store_json};
    const LK_MGMT = {mgmt_json};
    const LK_LOCS = {loc_json};
    const LK_CUMUL = {cumul_json};
    const LK_T = {T};

    let lkFiltered = [];
    let lkSortField = 'cylr';
    let lkSortAsc = false;
    let lkInit = false;
    let lkMgmtChart = null;

    function initLeakTab() {{
        if (lkInit) return;
        lkInit = true;
        initLeakYoyChart();
        renderLocTable();
        filterLeakData();
    }}

    function renderLocTable() {{
        document.getElementById('leakLocTable').innerHTML = LK_LOCS.map(l => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-1.5 text-sm text-gray-700">${{l.name}}</td>
                <td class="px-3 py-1.5 text-sm text-center text-gray-600">${{l.avg.toFixed(1)}}</td>
                <td class="px-3 py-1.5 text-sm text-center text-gray-600">${{l.events.toLocaleString()}}</td>
            </tr>
        `).join('');
    }}

    function initLeakYoyChart() {{
        const colors = {{ 2024: '#FFC000', 2025: '#4472C4', 2026: '#70AD47' }};
        const datasets = LK_CUMUL.years.map(y => ({{
            label: '' + y,
            data: LK_CUMUL.data[y],
            borderColor: colors[y] || '#999',
            backgroundColor: (colors[y] || '#999') + '33',
            fill: false,
            tension: 0.3,
            pointRadius: 4,
            pointBackgroundColor: colors[y] || '#999',
            borderWidth: y === 2026 ? 3 : 2,
        }}));
        // 9% threshold line
        datasets.push({{
            label: LK_T + '% Threshold',
            data: Array(12).fill(LK_T),
            borderColor: '#ea1100',
            borderWidth: 2,
            borderDash: [6, 3],
            pointRadius: 0,
            fill: false
        }});

        new Chart(document.getElementById('leakYoyChart').getContext('2d'), {{
            type: 'line',
            data: {{ labels: LK_CUMUL.months, datasets }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12 }} }},
                    datalabels: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, title: {{ display: true, text: 'Cumulative Leak Rate %' }} }}
                }}
            }}
        }});
    }}

    function renderMgmtChart() {{
        // Recompute mgmt rates from filtered store data
        const mgmtMap = {{}};
        lkFiltered.forEach(s => {{
            const key = s.fm || 'Unknown';
            if (!mgmtMap[key]) mgmtMap[key] = {{ fm: key, srd: s.srd, charge: 0, cytq: 0 }};
            mgmtMap[key].charge += s.sc;
            mgmtMap[key].cytq += s.cytq;
        }});
        const mgmtArr = Object.values(mgmtMap).map(m => ({{ ...m, cylr: m.charge > 0 ? (m.cytq / m.charge * 100) : 0 }}));
        mgmtArr.sort((a, b) => b.cylr - a.cylr);

        if (lkMgmtChart) lkMgmtChart.destroy();
        lkMgmtChart = new Chart(document.getElementById('leakMgmtChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: mgmtArr.map(m => m.fm),
                datasets: [{{
                    label: 'CY2026 Leak Rate %',
                    data: mgmtArr.map(m => m.cylr),
                    backgroundColor: mgmtArr.map(m => m.cylr > LK_T ? 'rgba(234,17,0,0.7)' : 'rgba(42,135,3,0.7)'),
                    borderRadius: 3
                }}, {{
                    label: LK_T + '% Threshold',
                    data: Array(mgmtArr.length).fill(LK_T),
                    type: 'line', borderColor: '#ea1100', borderDash: [6, 3], borderWidth: 2, pointRadius: 0, fill: false
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
                    datalabels: {{
                        anchor: 'end', align: 'end', color: '#333',
                        font: {{ size: 9, weight: 'bold' }},
                        formatter: v => typeof v === 'number' && v !== LK_T ? v.toFixed(1) + '%' : ''
                    }}
                }},
                scales: {{ x: {{ beginAtZero: true, title: {{ display: true, text: 'Leak Rate %' }} }} }}
            }},
            plugins: [ChartDataLabels]
        }});
    }}

    // --- Cascading Filters ---
    function updateLeakCascade() {{
        const vals = {{
            srd: document.getElementById('leakFilterSrDir').value,
            fm: document.getElementById('leakFilterFmDir').value,
            rm: document.getElementById('leakFilterRm').value,
            fsm: document.getElementById('leakFilterFsm').value,
            ban: document.getElementById('leakFilterBanner').value
        }};
        const getValid = (ex) => LK_STORES.filter(s => {{
            for (const [k, v] of Object.entries(vals)) if (k !== ex && v && s[k] !== v) return false;
            return true;
        }});
        const fill = (id, f) => {{
            const sel = document.getElementById(id);
            const cur = vals[f];
            const opts = [...new Set(getValid(f).map(s => s[f]).filter(Boolean))].sort();
            sel.innerHTML = '<option value="">All</option>';
            opts.forEach(v => {{ const o = new Option(v, v); if (v === cur) o.selected = true; sel.add(o); }});
        }};
        fill('leakFilterSrDir', 'srd');
        fill('leakFilterFmDir', 'fm');
        fill('leakFilterRm', 'rm');
        fill('leakFilterFsm', 'fsm');
        fill('leakFilterBanner', 'ban');
    }}

    function filterLeakData() {{
        const srd = document.getElementById('leakFilterSrDir').value;
        const fm = document.getElementById('leakFilterFmDir').value;
        const rm = document.getElementById('leakFilterRm').value;
        const fsm = document.getElementById('leakFilterFsm').value;
        const ban = document.getElementById('leakFilterBanner').value;
        const q = document.getElementById('leakSearch').value.toLowerCase();
        const over = document.getElementById('leakOverOnly').checked;

        lkFiltered = LK_STORES.filter(s => {{
            if (srd && s.srd !== srd) return false;
            if (fm && s.fm !== fm) return false;
            if (rm && s.rm !== rm) return false;
            if (fsm && s.fsm !== fsm) return false;
            if (ban && s.ban !== ban) return false;
            if (over && s.cylr <= LK_T) return false;
            if (q && !(s.s + ' ' + s.nm + ' ' + s.city + ' ' + s.mkt).toLowerCase().includes(q)) return false;
            return true;
        }});

        document.getElementById('leakFilteredCount').textContent = lkFiltered.length.toLocaleString();
        updateLeakCascade();
        updateLeakKpis();
        renderMgmtChart();
        renderLeakTable();
    }}

    function updateLeakKpis() {{
        let sc = 0, cytq = 0, cyl = 0, over = 0;
        lkFiltered.forEach(s => {{ sc += s.sc; cytq += s.cytq; cyl += s.cyl; if (s.cylr > LK_T) over++; }});
        const rate = sc > 0 ? (cytq / sc * 100) : 0;
        const thresh = Math.round(sc * LK_T / 100);
        const remain = Math.max(0, thresh - cytq);
        const pct = thresh > 0 ? Math.min(100, cytq / thresh * 100) : 0;

        document.getElementById('lkKpiThreshold').textContent = thresh.toLocaleString();
        document.getElementById('lkKpiRate').textContent = rate.toFixed(2) + '%';
        document.getElementById('lkKpiRate').className = 'text-xl font-bold ' + (rate > LK_T ? 'text-red-600' : 'text-green-600');
        document.getElementById('lkKpiRecords').textContent = cyl.toLocaleString();
        document.getElementById('lkKpiAdded').textContent = Math.round(cytq).toLocaleString();
        document.getElementById('lkKpiCharge').textContent = Math.round(sc).toLocaleString();

        const bar = document.getElementById('lkThresholdBar');
        bar.style.width = pct.toFixed(0) + '%';
        bar.style.background = cytq > thresh ? '#c00' : '#70ad47';
        document.getElementById('lkBarLabel').textContent = lkFiltered.length < LK_STORES.length ? 'Filtered' : 'All Stores';
        document.getElementById('lkBarValue').textContent = Math.round(cytq).toLocaleString() + ' lbs';
        document.getElementById('lkThreshLbs').textContent = thresh.toLocaleString() + ' lbs';
        document.getElementById('lkAddedLbs').textContent = Math.round(cytq).toLocaleString() + ' lbs';
        document.getElementById('lkAddedLbs').className = 'text-sm font-bold ' + (cytq > thresh ? 'text-red-600' : 'text-green-600');
        document.getElementById('lkRemainLbs').textContent = Math.round(remain).toLocaleString() + ' lbs';
        document.getElementById('lkRemainLbs').className = 'text-sm font-bold ' + (remain <= 0 ? 'text-red-600' : 'text-green-600');
    }}

    function clearLeakFilters() {{
        ['leakFilterSrDir','leakFilterFmDir','leakFilterRm','leakFilterFsm','leakFilterBanner'].forEach(id => document.getElementById(id).value = '');
        document.getElementById('leakSearch').value = '';
        document.getElementById('leakOverOnly').checked = false;
        filterLeakData();
    }}

    function sortLeakTable(f) {{
        if (lkSortField === f) lkSortAsc = !lkSortAsc;
        else {{ lkSortField = f; lkSortAsc = false; }}
        renderLeakTable();
    }}

    function renderLeakTable() {{
        const sorted = [...lkFiltered].sort((a, b) => {{
            let av = a[lkSortField], bv = b[lkSortField];
            if (typeof av === 'number') {{ }}
            else {{ av = av || ''; bv = bv || ''; }}
            if (av < bv) return lkSortAsc ? -1 : 1;
            if (av > bv) return lkSortAsc ? 1 : -1;
            return 0;
        }});
        const disp = sorted.slice(0, 300);
        const t = document.getElementById('leakStoreTable');
        t.innerHTML = disp.map(s => {{
            const ban = s.ban && s.ban.includes('Sam')
                ? '<span class="px-1.5 py-0.5 rounded text-xs font-semibold bg-blue-800 text-white">SAMS</span>'
                : '<span class="px-1.5 py-0.5 rounded text-xs font-semibold bg-yellow-400 text-blue-900">WMT</span>';
            const star = s.cylr > LK_T ? '\u274C' : s.cylr > LK_T * 0.7 ? '\u26A0\uFE0F' : '\u2705';
            const rClass = s.cylr > LK_T ? 'bg-red-500 text-white' : s.cylr > LK_T * 0.7 ? 'bg-amber-500 text-white' : 'bg-green-500 text-white';
            return `
                <tr class="hover:bg-gray-50 ${{s.cylr > LK_T ? 'bg-red-50' : ''}}">
                    <td class="px-3 py-1.5 text-sm font-medium text-gray-800">${{s.s}}</td>
                    <td class="px-3 py-1.5 text-sm text-gray-600">${{s.city}}${{s.city && s.st ? ', ' : ''}}${{s.st}}</td>
                    <td class="px-3 py-1.5 text-center">${{ban}}</td>
                    <td class="px-3 py-1.5 text-xs text-gray-600">${{s.mkt || '-'}}</td>
                    <td class="px-3 py-1.5 text-xs text-gray-600">${{s.rm || '-'}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{s.ac}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.sc).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.cytq).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold ${{rClass}}">${{s.cylr.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-1.5 text-sm text-center">${{s.cyl}}</td>
                    <td class="px-3 py-1.5 text-center text-sm">${{star}}</td>
                </tr>
            `;
        }}).join('');
        if (sorted.length > 300) {{
            t.innerHTML += `<tr><td colspan="11" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} stores.</td></tr>`;
        }}
    }}
    </script>
    '''


if __name__ == '__main__':
    main()
