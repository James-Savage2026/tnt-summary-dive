#!/usr/bin/env python3
"""Add Leak Management tab to TNT Dashboard — v3 matching Power BI layout.

Leak Rate % = (SUM trigger_qty / SUM unique asset charges) × 100
Charge is STATIC per asset (tank capacity). Trigger qty is cumulative.
Threshold: 9%.
"""

import json
import csv
import re
from pathlib import Path

DASHBOARD = Path(__file__).parent / 'index.html'
BQ = Path.home() / 'bigquery_results'

STORE_FILE = BQ / 'leak-store-rollup-v2-20260210-094209.csv'
MGMT_FILE = BQ / 'leak-mgmt-rollup-v2-20260210-094208.csv'
LOCATION_FILE = BQ / 'leak-locations-20260210-095157.csv'
YOY_FILE = BQ / 'leak-monthly-by-year-20260210-095158.csv'

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
        'lr': round(sf(r.get('leak_rate_pct')), 2),
        'l12': si(r.get('leaks_last_12mo')),
        'tq12': round(sf(r.get('trigger_qty_last_12mo')), 1),
        'lr12': round(sf(r.get('leak_rate_12mo_pct')), 2),
        'ld': (r.get('latest_leak_date') or '')[:10],
    } for r in rows]


def compress_mgmt(rows):
    return [{
        'srd': r.get('sr_dir', ''), 'fm': r.get('fm_dir', ''),
        'assets': si(r.get('total_assets')), 'stores': si(r.get('store_count')),
        'charge': round(sf(r.get('total_charge')), 1),
        'leaks': si(r.get('total_leaks')),
        'tq': round(sf(r.get('total_trigger_qty')), 1),
        'lr': round(sf(r.get('leak_rate_pct')), 2),
        'tq12': round(sf(r.get('trigger_qty_12mo')), 1),
        'lr12': round(sf(r.get('leak_rate_12mo_pct')), 2),
    } for r in rows]


def build_yoy_data(rows):
    """Build year-over-year monthly data for grouped bar chart."""
    years = sorted(set(si(r['leak_year']) for r in rows))
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    datasets = {}
    for r in rows:
        y = si(r['leak_year'])
        m = si(r['leak_month'])
        if y not in datasets:
            datasets[y] = [None] * 12
        datasets[y][m - 1] = round(sf(r.get('monthly_leak_rate', r.get('monthly_leak_rate_pct', 0))), 4)
    return months, years, datasets


def main():
    print('\U0001f9ca Loading Leak Management data (v3)...')

    stores_raw = load_csv(STORE_FILE)
    mgmt_raw = load_csv(MGMT_FILE)
    locations = load_csv(LOCATION_FILE)
    yoy_raw = load_csv(YOY_FILE)

    stores = compress_stores(stores_raw)
    mgmt = compress_mgmt(mgmt_raw)
    months, years, yoy_ds = build_yoy_data(yoy_raw)

    # Fleet totals
    fleet_charge = sum(d['sc'] for d in stores)
    total_tq = sum(d['tq'] for d in stores)
    total_leaks = sum(d['tl'] for d in stores)
    tq_ytd = sum(d['tq12'] for d in stores)
    leaks_ytd = sum(d['l12'] for d in stores)
    ytd_rate = round((tq_ytd / fleet_charge * 100), 2) if fleet_charge else 0
    threshold_lbs = round(fleet_charge * THRESHOLD / 100)
    stores_over = sum(1 for d in stores if d['lr12'] > THRESHOLD)

    # Leak locations (top 20)
    loc_data = [{
        'name': l.get('leak_location_name', ''),
        'events': si(l.get('leak_events')),
        'avg': round(sf(l.get('avg_amount_added')), 1),
        'total': round(sf(l.get('total_amount_added')), 1),
    } for l in locations[:25]]

    print(f'   Stores: {len(stores):,}')
    print(f'   Fleet charge: {fleet_charge:,.0f} lbs')
    print(f'   YTD leak rate: {ytd_rate:.2f}%')
    print(f'   9% threshold (lbs): {threshold_lbs:,}')
    print(f'   Leak locations: {len(loc_data)}')
    print(f'   YoY years: {years}')

    # JSON data
    store_json = json.dumps(stores, separators=(',', ':'))
    mgmt_json = json.dumps(mgmt, separators=(',', ':'))
    loc_json = json.dumps(loc_data, separators=(',', ':'))
    yoy_json = json.dumps({'months': months, 'years': years, 'data': yoy_ds}, separators=(',', ':'))

    print('\n\U0001f4dd Reading dashboard HTML...')
    html = DASHBOARD.read_text(encoding='utf-8')

    # Remove old leak content
    if '<!-- Leak Tab Content -->' in html:
        print('   Removing old Leak tab...')
        html = re.sub(r'<!-- Leak Tab Content -->.*?<!-- End Leak Tab -->', '', html, flags=re.DOTALL)
        html = re.sub(r'<script>\s*// Leak Management Data.*?</script>', '', html, flags=re.DOTALL)

    # Ensure tab button
    if 'tab-leak' not in html:
        btn = '''\n                <button onclick="switchTab('leak')" id="tab-leak"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001f9ca Leak Management
                </button>'''
        html = html.replace('</nav>\n        </div>\n    </div>', btn + '\n            </nav>\n        </div>\n    </div>', 1)

    leak_html = _build_html(fleet_charge, tq_ytd, ytd_rate, total_leaks, leaks_ytd, threshold_lbs, stores_over, len(stores))
    leak_js = _build_js(store_json, mgmt_json, loc_json, yoy_json)

    html = re.sub(r'(\s*<!-- Footer -->)', '\n' + leak_html + '\n\n    <!-- Footer -->', html, count=1)
    html = html.replace('</body>', leak_js + '\n</body>')

    DASHBOARD.write_text(html, encoding='utf-8')
    print(f'\n\u2705 Leak Management tab updated (v3 - Power BI layout)!')


def _build_html(fleet_charge, tq_ytd, ytd_rate, total_leaks, leaks_ytd, threshold_lbs, stores_over, total_stores):
    T = THRESHOLD
    return f'''
    <!-- Leak Tab Content -->
    <div id="leak-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">

            <!-- Header matching Power BI style -->
            <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
                <div class="flex items-center gap-3 mb-4">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/Walmart_logo.svg" alt="Walmart" class="h-8" crossorigin="anonymous">
                    <div>
                        <h1 class="text-xl font-bold text-gray-800">Refrigerant Leak Report - All Locations</h1>
                        <p class="text-xs text-gray-400">\u21bb Data as of report refresh</p>
                    </div>
                </div>

                <!-- KPI Bar - matching Power BI blue headers -->
                <div class="grid grid-cols-2 md:grid-cols-5 gap-0">
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">9% Leak Rate Threshold (lbs)</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiThreshold">{threshold_lbs:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">YTD Leak Rate</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold {'text-red-600' if ytd_rate > T else 'text-green-600'}" id="lkKpiYtdRate">{ytd_rate:.2f}%</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">Total # of Leak Records</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiRecords">{leaks_ytd:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t">YTD Amount Added (lbs)</div>
                        <div class="border border-gray-200 px-3 py-4 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiAdded">{tq_ytd:,.1f}</p>
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

            <!-- Threshold Bar + Monthly YoY Chart -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <!-- Threshold Progress Bar -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">9% Leak Rate Threshold (lbs)</div>
                    <div class="flex items-center gap-3">
                        <span class="text-sm text-gray-500 whitespace-nowrap" id="lkBarLabel">All Stores</span>
                        <div class="flex-1 relative">
                            <div class="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                                <div id="lkThresholdBar" class="h-8 rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                                     style="width: {min(100, (tq_ytd / threshold_lbs * 100)) if threshold_lbs else 0:.0f}%; background: {'#c00' if tq_ytd > threshold_lbs else '#70ad47'};">
                                </div>
                            </div>
                            <!-- 9% marker -->
                            <div class="absolute top-0 right-0 h-8 flex items-center" style="right: 0;">
                                <span class="bg-gray-700 text-white text-xs px-1.5 py-0.5 rounded">{T}%</span>
                            </div>
                        </div>
                        <span class="text-sm font-bold text-gray-700 whitespace-nowrap" id="lkBarValue">{tq_ytd:,.0f} lbs</span>
                    </div>
                    <div class="mt-3 grid grid-cols-3 gap-2 text-center">
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Threshold</p>
                            <p class="text-sm font-bold text-gray-700" id="lkThreshLbs">{threshold_lbs:,} lbs</p>
                        </div>
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Added YTD</p>
                            <p class="text-sm font-bold {'text-red-600' if tq_ytd > threshold_lbs else 'text-green-600'}" id="lkAddedLbs">{tq_ytd:,.0f} lbs</p>
                        </div>
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Remaining</p>
                            <p class="text-sm font-bold {'text-red-600' if tq_ytd > threshold_lbs else 'text-green-600'}" id="lkRemainLbs">{max(0, threshold_lbs - tq_ytd):,.0f} lbs</p>
                        </div>
                    </div>
                </div>

                <!-- Monthly YoY Chart -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">Monthly Leak Rate vs {T}% Threshold</div>
                    <div style="height: 250px;"><canvas id="leakYoyChart"></canvas></div>
                </div>
            </div>

            <!-- Asset Summary + Leak Location side by side -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <!-- FM Director Leak Rate Chart -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[#4472C4] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">FM Director 12mo Leak Rate vs {T}%</div>
                    <div style="height: 350px;"><canvas id="leakMgmtChart"></canvas></div>
                </div>

                <!-- Leak Location Table -->
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
                        Over {T}% only (12mo)
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
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('tq12')">Added (12mo) \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('lr12')">12mo Rate \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('l12')">Events \u21C5</th>
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


def _build_js(store_json, mgmt_json, loc_json, yoy_json):
    T = THRESHOLD
    return f'''
    <script>
    // Leak Management Data
    const LK_STORES = {store_json};
    const LK_MGMT = {mgmt_json};
    const LK_LOCS = {loc_json};
    const LK_YOY = {yoy_json};
    const LK_THRESHOLD = {T};

    let lkFiltered = [];
    let lkSortField = 'lr12';
    let lkSortAsc = false;
    let lkInitialized = false;

    function initLeakTab() {{
        if (lkInitialized) return;
        lkInitialized = true;
        initLeakCharts();
        renderLocTable();
        renderMgmtTable();
        filterLeakData();
    }}

    function renderLocTable() {{
        const t = document.getElementById('leakLocTable');
        t.innerHTML = LK_LOCS.map(l => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-1.5 text-sm text-gray-700">${{l.name}}</td>
                <td class="px-3 py-1.5 text-sm text-center text-gray-600">${{l.avg.toFixed(1)}}</td>
                <td class="px-3 py-1.5 text-sm text-center text-gray-600">${{l.events.toLocaleString()}}</td>
            </tr>
        `).join('');
    }}

    function renderMgmtTable() {{
        const sorted = [...LK_MGMT].sort((a, b) => b.lr12 - a.lr12);
        // Build FM Director horizontal bar chart
        const ctx = document.getElementById('leakMgmtChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: sorted.map(m => m.fm || 'Unknown'),
                datasets: [{{
                    label: '12mo Leak Rate %',
                    data: sorted.map(m => m.lr12),
                    backgroundColor: sorted.map(m => m.lr12 > LK_THRESHOLD ? 'rgba(234,17,0,0.7)' : 'rgba(42,135,3,0.7)'),
                    borderRadius: 3
                }}, {{
                    label: LK_THRESHOLD + '% Threshold',
                    data: Array(sorted.length).fill(LK_THRESHOLD),
                    type: 'line',
                    borderColor: '#ea1100',
                    borderDash: [6, 3],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
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
                        formatter: v => typeof v === 'number' && v !== LK_THRESHOLD ? v.toFixed(1) + '%' : ''
                    }}
                }},
                scales: {{ x: {{ beginAtZero: true, title: {{ display: true, text: 'Leak Rate %' }} }} }}
            }},
            plugins: [ChartDataLabels]
        }});
    }}

    function initLeakCharts() {{
        // YoY Monthly chart matching Power BI
        const yoyColors = {{ 2024: '#FFC000', 2025: '#4472C4', 2026: '#70AD47' }};
        const datasets = LK_YOY.years.map(y => ({{
            label: '' + y,
            data: LK_YOY.data[y],
            backgroundColor: yoyColors[y] || '#999',
            borderRadius: 2
        }}));
        // Add threshold line
        datasets.push({{
            label: LK_THRESHOLD + '% Annual (\u00f712)',
            data: Array(12).fill(LK_THRESHOLD / 12),
            type: 'line',
            borderColor: '#ea1100',
            borderWidth: 2,
            borderDash: [6, 3],
            pointRadius: 0,
            fill: false
        }});

        const ctx = document.getElementById('leakYoyChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{ labels: LK_YOY.months, datasets }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12 }} }},
                    datalabels: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, title: {{ display: true, text: 'Monthly Rate %' }} }}
                }}
            }}
        }});
    }}

    // --- Filtering & Table ---
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
        const fill = (id, f, ex) => {{
            const sel = document.getElementById(id);
            const cur = vals[f];
            const opts = [...new Set(getValid(f).map(s => s[f]).filter(Boolean))].sort();
            sel.innerHTML = '<option value="">All</option>';
            opts.forEach(v => {{ const o = new Option(v, v); if (v === cur) o.selected = true; sel.add(o); }});
        }};
        fill('leakFilterSrDir', 'srd', 'srd');
        fill('leakFilterFmDir', 'fm', 'fm');
        fill('leakFilterRm', 'rm', 'rm');
        fill('leakFilterFsm', 'fsm', 'fsm');
        fill('leakFilterBanner', 'ban', 'ban');
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
            if (over && s.lr12 <= LK_THRESHOLD) return false;
            if (q && !(s.s + ' ' + s.nm + ' ' + s.city + ' ' + s.mkt).toLowerCase().includes(q)) return false;
            return true;
        }});

        document.getElementById('leakFilteredCount').textContent = lkFiltered.length.toLocaleString();
        updateLeakCascade();
        updateLeakKpis();
        renderLeakTable();
    }}

    function updateLeakKpis() {{
        let sc = 0, tq12 = 0, l12 = 0, over = 0;
        lkFiltered.forEach(s => {{ sc += s.sc; tq12 += s.tq12; l12 += s.l12; if (s.lr12 > LK_THRESHOLD) over++; }});
        const rate = sc > 0 ? (tq12 / sc * 100) : 0;
        const thresh = Math.round(sc * LK_THRESHOLD / 100);
        const remain = Math.max(0, thresh - tq12);
        const pct = thresh > 0 ? Math.min(100, tq12 / thresh * 100) : 0;

        document.getElementById('lkKpiThreshold').textContent = thresh.toLocaleString();
        document.getElementById('lkKpiYtdRate').textContent = rate.toFixed(2) + '%';
        document.getElementById('lkKpiYtdRate').className = 'text-xl font-bold ' + (rate > LK_THRESHOLD ? 'text-red-600' : 'text-green-600');
        document.getElementById('lkKpiRecords').textContent = l12.toLocaleString();
        document.getElementById('lkKpiAdded').textContent = Math.round(tq12).toLocaleString() + '.0';
        document.getElementById('lkKpiCharge').textContent = Math.round(sc).toLocaleString();

        // Threshold bar
        const bar = document.getElementById('lkThresholdBar');
        bar.style.width = pct.toFixed(0) + '%';
        bar.style.background = tq12 > thresh ? '#c00' : '#70ad47';
        document.getElementById('lkBarValue').textContent = Math.round(tq12).toLocaleString() + ' lbs';
        document.getElementById('lkThreshLbs').textContent = thresh.toLocaleString() + ' lbs';
        document.getElementById('lkAddedLbs').textContent = Math.round(tq12).toLocaleString() + ' lbs';
        document.getElementById('lkAddedLbs').className = 'text-sm font-bold ' + (tq12 > thresh ? 'text-red-600' : 'text-green-600');
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
            const star = s.lr12 > LK_THRESHOLD * 2 ? '\u2733\uFE0F'
                       : s.lr12 > LK_THRESHOLD ? '\u2733\uFE0F'
                       : s.lr12 > LK_THRESHOLD * 0.7 ? '\u26A0\uFE0F' : '\u2705';
            const rClass = s.lr12 > LK_THRESHOLD ? 'bg-red-500 text-white' : s.lr12 > LK_THRESHOLD * 0.7 ? 'bg-amber-500 text-white' : 'bg-green-500 text-white';
            return `
                <tr class="hover:bg-gray-50 ${{s.lr12 > LK_THRESHOLD ? 'bg-red-50' : ''}}">
                    <td class="px-3 py-1.5 text-sm font-medium text-gray-800">${{s.s}}</td>
                    <td class="px-3 py-1.5 text-sm text-gray-600">${{s.city}}${{s.city && s.st ? ', ' : ''}}${{s.st}}</td>
                    <td class="px-3 py-1.5 text-center">${{ban}}</td>
                    <td class="px-3 py-1.5 text-xs text-gray-600">${{s.mkt || '-'}}</td>
                    <td class="px-3 py-1.5 text-xs text-gray-600">${{s.rm || '-'}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{s.ac}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.sc).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.tq12).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold ${{rClass}}">${{s.lr12.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-1.5 text-sm text-center">${{s.l12}}</td>
                    <td class="px-3 py-1.5 text-center text-sm">${{star}}</td>
                </tr>
            `;
        }}).join('');
        if (sorted.length > 300) {{
            t.innerHTML += `<tr><td colspan="11" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} stores. Use filters.</td></tr>`;
        }}
    }}
    </script>
    '''


if __name__ == '__main__':
    main()
