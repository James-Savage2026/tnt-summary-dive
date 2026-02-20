#!/usr/bin/env python3
"""Add Terminal Cases tab to TNT Dashboard.

Replicates the Tableau 'Refrigeration Cases Terminal Status Report':
- Summary KPIs: Total Stores, Cases, Open WOs
- Open WOs donut chart
- Consecutive Days in Terminal State bar chart
- FS Sub Market case summary horizontal bar chart
- Cascading filters: Sr Director → Director → RM → FSM → Market → Sub Market
- Full detail table

Data source: re-crystal-mdm-prod.crystal.case_terminal_performance
"""

import json
import csv
import re
import sys
from pathlib import Path

DASHBOARD = Path(__file__).parent / 'index.html'
DATA_FILE = Path(__file__).parent / 'terminal_cases.csv'
WO_FILE = Path(__file__).parent / 'terminal_wos.csv'
SC_URL = 'https://www.servicechannel.com/sc/wo/Workorders/index?id='


def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def sf(v, d=0):
    try: return float(v)
    except: return d


def si(v, d=0):
    try: return int(float(v))
    except: return d


def compress(rows):
    """Compress CSV rows into compact JSON for embedding."""
    return [{
        'sn': r['store_number'],
        'cn': r['case_name'],
        'cl': r.get('controller_label', ''),
        'cc': r.get('case_class', ''),
        'sp': sf(r.get('setpoint'), None),
        'mt': sf(r.get('median_temp'), None),
        'ow': si(r.get('open_work_orders')),
        'pt': sf(r.get('pct_terminal_24h')),
        'cd': si(r.get('consec_days')),
        'dt': si(r.get('days_terminal_30')),
        'bm': r.get('business_model', ''),
        'rn': r.get('region_number', ''),
        'mn': r.get('market_number', ''),
        'fm': r.get('fs_market', ''),
        'fsm': r.get('fs_submarket', ''),
        'od': r.get('ops_divisional', ''),
        'srd': r.get('sr_fm_director', ''),
        'dir': r.get('fm_director', ''),
        'rm': r.get('fm_regional_manager', ''),
        'mgr': r.get('fs_manager', ''),
        'tech': r.get('hvacr_technician', ''),
        'sl': r.get('sensor_label', ''),
    } for r in rows]


def build_terminal_html(total_cases, total_stores, run_stamp):
    """Build the HTML structure for the Terminal Cases tab."""
    run_date = run_stamp[:10] if run_stamp else 'Unknown'
    return f'''<!-- Terminal Tab Content -->
    <div id="terminal-content" class="hidden">
    <main class="max-w-7xl mx-auto px-4 py-6">
        <!-- Filters -->
        <div class="bg-white rounded-lg shadow p-4 mb-6">
            <div class="flex justify-between items-center mb-3">
                <h3 class="text-sm font-medium text-gray-700">Filters</h3>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-400">Data as of: {run_date}</span>
                    <button onclick="clearTerminalFilters()" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm rounded-md">✕ Clear Filters</button>
                </div>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Sr Director</label>
                    <select id="termSrDir" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Director</label>
                    <select id="termDir" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Regional Mgr</label>
                    <select id="termRM" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">FS Manager</label>
                    <select id="termFSM" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">FS Market</label>
                    <select id="termMarket" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Sub Market</label>
                    <select id="termSubMkt" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Case Class</label>
                    <select id="termCaseClass" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Consec. Days</label>
                    <select id="termConsecDays" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                        <option value="1">1 Day</option>
                        <option value="2">2 Days</option>
                        <option value="3+">&gt;3 Days</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Open WOs</label>
                    <select id="termOpenWO" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                        <option value="yes">Has Open WOs</option>
                        <option value="no">No Open WOs</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">HVACR Tech</label>
                    <select id="termTech" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Store</label>
                    <select id="termStore" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Ops Region</label>
                    <select id="termOpsRegion" onchange="applyTerminalFilters()" class="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm">
                        <option value="">All</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Summary KPIs Row -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="bg-white rounded-lg shadow p-4 border-l-4 border-red-700">
                <p class="text-xs text-gray-500 uppercase tracking-wide">Total Cases</p>
                <p class="text-3xl font-bold text-red-700" id="termTotalCases">--</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4 border-l-4 border-amber-600">
                <p class="text-xs text-gray-500 uppercase tracking-wide">Total Stores</p>
                <p class="text-3xl font-bold text-amber-700" id="termTotalStores">--</p>
            </div>
            <div class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-600">
                <p class="text-xs text-gray-500 uppercase tracking-wide">Cases with Open WOs</p>
                <p class="text-3xl font-bold text-blue-700" id="termWithWO">--</p>
                <p class="text-xs text-gray-400" id="termWithWOPct"></p>
            </div>
            <div class="bg-white rounded-lg shadow p-4 border-l-4 border-gray-500">
                <p class="text-xs text-gray-500 uppercase tracking-wide">Cases without WOs</p>
                <p class="text-3xl font-bold text-gray-700" id="termNoWO">--</p>
                <p class="text-xs text-gray-400" id="termNoWOPct"></p>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <!-- Open WOs Donut -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold text-gray-800 mb-3">Open WOs Case Summary</h2>
                <div style="height: 260px; position: relative;">
                    <canvas id="termDonutChart"></canvas>
                </div>
            </div>
            <!-- Consecutive Days Bar -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold text-gray-800 mb-3">Consecutive Days in Terminal State</h2>
                <div style="height: 260px;">
                    <canvas id="termDaysChart"></canvas>
                </div>
            </div>
            <!-- Sub Market Bar -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold text-gray-800 mb-3" id="termSubMktTitle">FS Sub Market Case Summary</h2>
                <div style="height: 260px;">
                    <canvas id="termSubMktChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Case Class Summary Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <!-- By Director -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold text-gray-800 mb-3">Cases by Director</h2>
                <div style="height: 300px;">
                    <canvas id="termDirChart"></canvas>
                </div>
            </div>
            <!-- By Case Class -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-base font-semibold text-gray-800 mb-3">Cases by Type</h2>
                <div class="grid grid-cols-2 gap-4" id="termCaseClassCards">
                </div>
            </div>
        </div>

        <!-- Detail Table -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <div class="px-4 py-3 border-b border-gray-200 bg-red-800 flex justify-between items-center">
                <h2 class="text-base font-semibold text-white">Refrigeration Case Status Detail</h2>
                <div class="flex items-center gap-3">
                    <input type="text" id="termTableSearch" placeholder="Search..." 
                           class="border border-gray-300 rounded-md px-3 py-1 text-sm">
                    <span class="text-xs text-red-200" id="termRowCount"></span>
                </div>
            </div>
            <div class="overflow-x-auto" style="max-height: 600px; overflow-y: auto;">
                <table class="min-w-full divide-y divide-gray-200 text-xs">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('sn')">Store</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('fsm')">Sub Mkt</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('dir')">Director</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('rm')">Regional Mgr</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('mgr')">FS Manager</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('tech')">HVACR Tech</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('cn')">Case Name</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600">Class</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('ow')">Open WOs</th>
                            <th class="px-2 py-2 text-left font-medium text-gray-600">WO Links</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('pt')" title="% Time in Terminal State (24h)">% Terminal</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('cd')" title="Consecutive Days in Terminal State">Consec Days</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('dt')" title="Days in Terminal State Last 30">Days/30</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('mt')">Median Temp</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600 cursor-pointer" onclick="sortTermTable('sp')">Setpoint</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600">Variance</th>
                            <th class="px-2 py-2 text-center font-medium text-gray-600">Email</th>
                        </tr>
                    </thead>
                    <tbody id="termTableBody" class="bg-white divide-y divide-gray-100">
                    </tbody>
                </table>
            </div>
        </div>
    </main>
    </div>
<!-- End Terminal Tab -->'''


def build_terminal_js(data_json):
    """Build the JS for the Terminal Cases tab."""
    return f'''<!-- Terminal JS Start -->
<script>
// Terminal Cases Data
const TERMINAL_DATA = {data_json};
console.log('TERMINAL_DATA loaded:', TERMINAL_DATA.length, 'records');
</script>
<script>
let termFiltered = [...TERMINAL_DATA];
let termSort = {{ field: 'cd', dir: 'desc' }};
let termDonutChart, termDaysChart, termSubMktChart, termDirChart;

function initTerminalTab() {{
    if (window._termInit) return;
    window._termInit = true;
    try {{
        populateTerminalFilters();
        applyTerminalFilters();
        console.log('Terminal tab initialized:', TERMINAL_DATA.length, 'cases');
    }} catch(e) {{
        console.error('Terminal tab init error:', e);
        document.getElementById('termTotalCases').textContent = 'ERROR';
        document.getElementById('termTotalCases').title = e.message;
    }}
}}

function populateTerminalFilters() {{
    const data = TERMINAL_DATA;
    const fill = (id, vals) => {{
        const sel = document.getElementById(id);
        const cur = sel.value;
        while (sel.options.length > 1) sel.remove(1);
        vals.sort().forEach(v => {{
            if (v) {{ const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }}
        }});
        sel.value = cur;
    }};
    fill('termSrDir', [...new Set(data.map(r => r.srd))]);
    fill('termDir', [...new Set(data.map(r => r.dir))]);
    fill('termRM', [...new Set(data.map(r => r.rm))]);
    fill('termFSM', [...new Set(data.map(r => r.mgr))]);
    fill('termMarket', [...new Set(data.map(r => r.fm))]);
    fill('termSubMkt', [...new Set(data.map(r => r.fsm))]);
    fill('termCaseClass', [...new Set(data.map(r => r.cc))]);
    fill('termTech', [...new Set(data.map(r => r.tech))]);
    fill('termStore', [...new Set(data.map(r => r.sn))]);
    fill('termOpsRegion', [...new Set(data.map(r => r.rn))]);
}}

function cascadeTerminalFilters() {{
    const srd = document.getElementById('termSrDir').value;
    const dir = document.getElementById('termDir').value;
    const rm = document.getElementById('termRM').value;
    const fsm = document.getElementById('termFSM').value;
    let data = TERMINAL_DATA;
    if (srd) data = data.filter(r => r.srd === srd);
    if (dir) data = data.filter(r => r.dir === dir);
    if (rm) data = data.filter(r => r.rm === rm);
    if (fsm) data = data.filter(r => r.mgr === fsm);

    const fill = (id, vals) => {{
        const sel = document.getElementById(id);
        const cur = sel.value;
        while (sel.options.length > 1) sel.remove(1);
        vals.sort().forEach(v => {{
            if (v) {{ const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }}
        }});
        if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
        else sel.value = '';
    }};
    if (!srd) fill('termSrDir', [...new Set(TERMINAL_DATA.map(r => r.srd))]);
    fill('termDir', [...new Set(data.map(r => r.dir))]);
    fill('termRM', [...new Set(data.map(r => r.rm))]);
    fill('termFSM', [...new Set(data.map(r => r.mgr))]);
    fill('termMarket', [...new Set(data.map(r => r.fm))]);
    fill('termSubMkt', [...new Set(data.map(r => r.fsm))]);
    fill('termTech', [...new Set(data.map(r => r.tech))]);
    fill('termStore', [...new Set(data.map(r => r.sn))]);
    fill('termOpsRegion', [...new Set(data.map(r => r.rn))]);
}}

function applyTerminalFilters() {{
    cascadeTerminalFilters();
    let data = [...TERMINAL_DATA];
    const v = id => document.getElementById(id).value;
    if (v('termSrDir')) data = data.filter(r => r.srd === v('termSrDir'));
    if (v('termDir')) data = data.filter(r => r.dir === v('termDir'));
    if (v('termRM')) data = data.filter(r => r.rm === v('termRM'));
    if (v('termFSM')) data = data.filter(r => r.mgr === v('termFSM'));
    if (v('termMarket')) data = data.filter(r => r.fm === v('termMarket'));
    if (v('termSubMkt')) data = data.filter(r => r.fsm === v('termSubMkt'));
    if (v('termCaseClass')) data = data.filter(r => r.cc === v('termCaseClass'));
    if (v('termTech')) data = data.filter(r => r.tech === v('termTech'));
    if (v('termStore')) data = data.filter(r => r.sn === v('termStore'));
    if (v('termOpsRegion')) data = data.filter(r => r.rn === v('termOpsRegion'));

    const cd = v('termConsecDays');
    if (cd === '1') data = data.filter(r => r.cd === 1);
    else if (cd === '2') data = data.filter(r => r.cd === 2);
    else if (cd === '3+') data = data.filter(r => r.cd >= 3);

    const wo = v('termOpenWO');
    if (wo === 'yes') data = data.filter(r => r.ow > 0);
    else if (wo === 'no') data = data.filter(r => r.ow === 0);

    // Search
    const q = (document.getElementById('termTableSearch').value || '').toLowerCase();
    if (q) data = data.filter(r => 
        (r.sn + ' ' + r.cn + ' ' + r.dir + ' ' + r.rm + ' ' + r.mgr + ' ' + r.tech + ' ' + r.fsm).toLowerCase().includes(q)
    );

    termFiltered = data;
    updateTerminalKPIs(data);
    updateTerminalCharts(data);
    updateTerminalTable(data);
}}

function clearTerminalFilters() {{
    ['termSrDir','termDir','termRM','termFSM','termMarket','termSubMkt',
     'termCaseClass','termConsecDays','termOpenWO','termTech','termStore','termOpsRegion'].forEach(id => {{
        document.getElementById(id).value = '';
    }});
    document.getElementById('termTableSearch').value = '';
    populateTerminalFilters();
    applyTerminalFilters();
}}

function updateTerminalKPIs(data) {{
    const stores = new Set(data.map(r => r.sn)).size;
    const withWO = data.filter(r => r.ow > 0).length;
    const noWO = data.length - withWO;
    document.getElementById('termTotalCases').textContent = data.length.toLocaleString();
    document.getElementById('termTotalStores').textContent = stores.toLocaleString();
    document.getElementById('termWithWO').textContent = withWO.toLocaleString();
    document.getElementById('termNoWO').textContent = noWO.toLocaleString();
    document.getElementById('termWithWOPct').textContent = data.length ? (withWO / data.length * 100).toFixed(1) + '% of cases' : '';
    document.getElementById('termNoWOPct').textContent = data.length ? (noWO / data.length * 100).toFixed(1) + '% of cases' : '';

    // Case class cards
    const ccMap = {{}};
    data.forEach(r => {{ const k = r.cc || 'Unknown'; ccMap[k] = (ccMap[k] || 0) + 1; }});
    const colors = {{ MT: 'bg-amber-100 text-amber-800 border-amber-300', LT: 'bg-blue-100 text-blue-800 border-blue-300', Unknown: 'bg-gray-100 text-gray-700 border-gray-300' }};
    const labels = {{ MT: 'Medium Temp', LT: 'Low Temp', Unknown: 'Unknown' }};
    let cards = '';
    Object.entries(ccMap).sort((a,b) => b[1]-a[1]).forEach(([k, cnt]) => {{
        const c = colors[k] || colors.Unknown;
        const l = labels[k] || k;
        cards += `<div class="rounded-lg border-2 p-4 ${{c}} text-center">
            <p class="text-3xl font-bold">${{cnt}}</p>
            <p class="text-sm font-medium">${{l}} (${{k}})</p>
            <p class="text-xs mt-1">${{data.length ? (cnt/data.length*100).toFixed(1) : 0}}%</p>
        </div>`;
    }});
    document.getElementById('termCaseClassCards').innerHTML = cards;
}}

function updateTerminalCharts(data) {{
    try {{
    const withWO = data.filter(r => r.ow > 0).length;
    const noWO = data.length - withWO;

    // Donut
    if (termDonutChart) termDonutChart.destroy();
    const dCtx = document.getElementById('termDonutChart').getContext('2d');
    termDonutChart = new Chart(dCtx, {{
        type: 'doughnut',
        data: {{
            labels: ['With Open WOs (' + withWO + ')', 'No Open WOs (' + noWO + ')'],
            datasets: [{{
                data: [withWO, noWO],
                backgroundColor: ['#b45309', '#d4d4d4'],
                borderWidth: 2, borderColor: '#fff'
            }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            cutout: '55%',
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }} }} }},
                datalabels: {{ display: false }}
            }}
        }}
    }});

    // Consecutive days bar
    const day1 = data.filter(r => r.cd === 1).length;
    const day2 = data.filter(r => r.cd === 2).length;
    const day3p = data.filter(r => r.cd >= 3).length;
    const day0 = data.filter(r => r.cd === 0).length;

    if (termDaysChart) termDaysChart.destroy();
    const bCtx = document.getElementById('termDaysChart').getContext('2d');
    termDaysChart = new Chart(bCtx, {{
        type: 'bar',
        data: {{
            labels: ['0 Days', '1 Day', '2 Days', '>3 Days'],
            datasets: [{{
                data: [day0, day1, day2, day3p],
                backgroundColor: ['#d4d4d4', '#b45309', '#c2410c', '#991b1b'],
                borderRadius: 4
            }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                datalabels: {{ display: false }}
            }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});

    // Sub Market horizontal bar (top 15)
    const smMap = {{}};
    data.forEach(r => {{ const k = r.fsm || 'Unknown'; smMap[k] = (smMap[k] || 0) + 1; }});
    const smSorted = Object.entries(smMap).sort((a, b) => b[1] - a[1]).slice(0, 15);

    if (termSubMktChart) termSubMktChart.destroy();
    const sCtx = document.getElementById('termSubMktChart').getContext('2d');
    termSubMktChart = new Chart(sCtx, {{
        type: 'bar',
        data: {{
            labels: smSorted.map(e => e[0]),
            datasets: [{{
                data: smSorted.map(e => e[1]),
                backgroundColor: '#b45309',
                borderRadius: 3
            }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {{
                legend: {{ display: false }},
                datalabels: {{ display: false }}
            }},
            scales: {{ x: {{ beginAtZero: true }} }}
        }}
    }});

    // Director bar chart
    const dirMap = {{}};
    data.forEach(r => {{ const k = r.dir || 'Unknown'; dirMap[k] = (dirMap[k] || 0) + 1; }});
    const dirSorted = Object.entries(dirMap).sort((a, b) => b[1] - a[1]).slice(0, 15);

    if (termDirChart) termDirChart.destroy();
    const dcCtx = document.getElementById('termDirChart').getContext('2d');
    termDirChart = new Chart(dcCtx, {{
        type: 'bar',
        data: {{
            labels: dirSorted.map(e => e[0].length > 18 ? e[0].substring(0, 18) + '...' : e[0]),
            datasets: [{{
                data: dirSorted.map(e => e[1]),
                backgroundColor: dirSorted.map(e => e[1] >= 30 ? '#991b1b' : e[1] >= 15 ? '#b45309' : '#ca8a04'),
                borderRadius: 4
            }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{ callbacks: {{ title: items => dirSorted[items[0].dataIndex][0] }} }},
                datalabels: {{ display: false }}
            }},
            scales: {{ x: {{ beginAtZero: true }} }}
        }}
    }});
    }} catch(e) {{ console.error('Terminal chart error:', e); }}
}}

function sortTermTable(field) {{
    if (termSort.field === field) termSort.dir = termSort.dir === 'asc' ? 'desc' : 'asc';
    else {{ termSort.field = field; termSort.dir = 'desc'; }}
    updateTerminalTable(termFiltered);
}}

function updateTerminalTable(data) {{
    const sorted = [...data].sort((a, b) => {{
        let av = a[termSort.field], bv = b[termSort.field];
        if (typeof av === 'string') return termSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
        av = av ?? -999; bv = bv ?? -999;
        return termSort.dir === 'asc' ? av - bv : bv - av;
    }});

    document.getElementById('termRowCount').textContent = sorted.length + ' cases';

    const tbody = document.getElementById('termTableBody');
    const pctColor = v => v >= 90 ? 'bg-red-100 text-red-800 font-bold' : v >= 50 ? 'bg-amber-50 text-amber-800' : 'text-gray-700';
    const daysColor = d => d >= 3 ? 'bg-red-100 text-red-800 font-bold' : d >= 1 ? 'bg-amber-50 text-amber-800' : 'text-gray-500';

    const SC = 'https://www.servicechannel.com/sc/wo/Workorders/index?id=';
    let html = '';
    sorted.forEach(r => {{
        const variance = (r.mt != null && r.sp != null) ? (r.mt - r.sp).toFixed(1) : '--';
        const varNum = parseFloat(variance);
        const varColor = isNaN(varNum) ? '' : varNum > 10 ? 'text-red-600 font-bold' : varNum > 5 ? 'text-amber-600' : 'text-gray-600';
        // WO links
        let woLinks = '<span class="text-gray-300">&mdash;</span>';
        if (r.wos && r.wos.length > 0) {{
            woLinks = r.wos.slice(0, 3).map(t =>
                `<a href="${{SC}}${{t}}" target="_blank" class="text-blue-600 hover:underline font-medium" onclick="event.stopPropagation()">#${{t}}</a>`
            ).join('<br>');
            if (r.wos.length > 3) woLinks += `<br><span class="text-gray-400 text-xs">+${{r.wos.length - 3}} more</span>`;
        }}
        // Email button
        const firstName = (r.mgr || '').split(' ')[0] || 'Team';
        html += `<tr class="hover:bg-gray-50">
            <td class="px-2 py-1.5 font-medium text-gray-900">${{r.sn}}</td>
            <td class="px-2 py-1.5 text-gray-600">${{r.fsm || '--'}}</td>
            <td class="px-2 py-1.5 text-gray-600">${{r.dir || '--'}}</td>
            <td class="px-2 py-1.5 text-gray-600">${{r.rm || '--'}}</td>
            <td class="px-2 py-1.5 text-gray-600">${{r.mgr || '--'}}</td>
            <td class="px-2 py-1.5 text-gray-600">${{r.tech || '--'}}</td>
            <td class="px-2 py-1.5 font-medium">${{r.cn}}</td>
            <td class="px-2 py-1.5"><span class="px-1.5 py-0.5 rounded text-xs font-medium ${{r.cc === 'LT' ? 'bg-blue-100 text-blue-700' : r.cc === 'MT' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}}">${{r.cc || '--'}}</span></td>
            <td class="px-2 py-1.5 text-center ${{r.ow > 0 ? 'text-blue-600 font-bold' : 'text-gray-400'}}">${{r.ow}}</td>
            <td class="px-2 py-1.5 text-left">${{woLinks}}</td>
            <td class="px-2 py-1.5 text-center ${{pctColor(r.pt)}}">${{r.pt != null ? r.pt.toFixed(1) + '%' : '--'}}</td>
            <td class="px-2 py-1.5 text-center ${{daysColor(r.cd)}}">${{r.cd}}</td>
            <td class="px-2 py-1.5 text-center text-gray-600">${{r.dt}}</td>
            <td class="px-2 py-1.5 text-center text-gray-700">${{r.mt != null ? r.mt + '\u00b0F' : '--'}}</td>
            <td class="px-2 py-1.5 text-center text-gray-500">${{r.sp != null ? r.sp + '\u00b0F' : '--'}}</td>
            <td class="px-2 py-1.5 text-center ${{varColor}}">${{variance !== '--' ? variance + '\u00b0' : '--'}}</td>
            <td class="px-2 py-1.5 text-center">
                <button onclick="emailTerminalFSM('${{r.mgr}}','${{r.sn}}','${{r.cn}}','${{r.cc}}','${{r.cd}}','${{r.pt}}')" 
                    class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded" title="Email ${{r.mgr}}">\u2709</button>
            </td>
        </tr>`;
    }});
    tbody.innerHTML = html;
}}

function emailTerminalFSM(fsmName, storeNum, caseName, caseClass, consecDays, pctTerminal) {{
    const firstName = (fsmName || 'Team').split(' ')[0];
    const classLabel = caseClass === 'LT' ? 'Low Temp' : caseClass === 'MT' ? 'Medium Temp' : caseClass;
    const subject = `Store ${{storeNum}} \u2013 ${{caseName}} (${{classLabel}}) Terminal Case Support`;
    const body = [
        `Hey ${{firstName}}!`,
        ``,
        `Hope you\u2019re doing well! I wanted to reach out about a refrigeration case in terminal state at Store ${{storeNum}}.`,
        ``,
        `Case: ${{caseName}} (${{classLabel}})`,
        `Consecutive Days in Terminal: ${{consecDays}}`,
        `% Time in Terminal (24h): ${{pctTerminal}}%`,
        ``,
        `How can we get this case back up and running? What support do you need from the team to get it resolved?`,
        ``,
        `Let me know if there are any parts, labor, or coordination needs I can help with.`,
        ``,
        `Thanks!`,
    ].join('\\n');
    window.open(`mailto:?subject=${{encodeURIComponent(subject)}}&body=${{encodeURIComponent(body)}}`);
}}

// Search handler
const termSearchEl = document.getElementById('termTableSearch');
if (termSearchEl) {{
    termSearchEl.addEventListener('input', function() {{
        applyTerminalFilters();
    }});
}} else {{
    console.error('termTableSearch element not found!');
}}
console.log('Terminal tab JS loaded, TERMINAL_DATA:', TERMINAL_DATA.length, 'records');
</script>
<!-- Terminal JS End -->'''


def load_wo_map():
    """Load store -> [tracking_numbers] map from terminal_wos.csv."""
    wo_map = {}
    if not WO_FILE.exists():
        print('   \u26a0\ufe0f  No terminal_wos.csv found, skipping WO links')
        return wo_map
    for r in load_csv(WO_FILE):
        s = r['sn']
        if s not in wo_map:
            wo_map[s] = []
        wo_map[s].append(r['tn'])
    return wo_map


def main():
    print('\U0001f321\ufe0f  Loading Terminal Cases data...')
    if not DATA_FILE.exists():
        print(f'   \u274c {DATA_FILE} not found. Run BQ pull first.')
        sys.exit(1)

    rows = load_csv(DATA_FILE)
    wo_map = load_wo_map()
    data = compress(rows)
    # Inject WO tracking numbers at store level
    for d in data:
        d['wos'] = wo_map.get(d['sn'], [])
    run_stamp = rows[0].get('run_stamp', '') if rows else ''
    stores_with_wos = sum(1 for s in set(d['sn'] for d in data) if s in wo_map)
    print(f'   Stores with open Ref WOs: {stores_with_wos}')

    total_cases = len(data)
    total_stores = len(set(r['sn'] for r in data))

    print(f'   Cases: {total_cases}')
    print(f'   Stores: {total_stores}')
    print(f'   Run stamp: {run_stamp[:10]}')

    data_json = json.dumps(data, separators=(',', ':'))
    print(f'   Data size: {len(data_json):,} chars')

    print('\n\U0001f4dd Reading dashboard HTML...')
    html = DASHBOARD.read_text(encoding='utf-8')

    # Remove old terminal tab if exists
    if '<!-- Terminal Tab Content -->' in html:
        print('   Removing old Terminal tab...')
        html = re.sub(r'<!-- Terminal Tab Content -->.*?<!-- End Terminal Tab -->', '', html, flags=re.DOTALL)
        html = re.sub(r'<!-- Terminal JS Start -->.*?<!-- Terminal JS End -->', '', html, flags=re.DOTALL)
        html = re.sub(r'<script>\s*// Terminal Cases Data.*?</script>', '', html, flags=re.DOTALL)

    # Add tab button if not present
    if 'tab-terminal' not in html:
        btn = '''\n                <button onclick="switchTab('terminal')" id="tab-terminal"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001f321\ufe0f Terminal Cases
                </button>'''
        html = html.replace('</nav>', btn + '\n            </nav>', 1)

    # Update switchTab to include terminal
    if "'terminal-content'" not in html:
        html = html.replace(
            "['tnt-content', 'wtw-content', 'leak-content']",
            "['tnt-content', 'wtw-content', 'leak-content', 'terminal-content']"
        )
        html = html.replace(
            "if (tab === 'leak' && typeof initLeakTab === 'function') initLeakTab();",
            "if (tab === 'leak' && typeof initLeakTab === 'function') initLeakTab();\n        if (tab === 'terminal') initTerminalTab();"
        )

    # Insert HTML before footer
    term_html = build_terminal_html(total_cases, total_stores, run_stamp)
    html = re.sub(r'(\s*<!-- Footer -->)', '\n' + term_html + '\n\n    <!-- Footer -->', html, count=1)

    # Insert JS before </body>
    term_js = build_terminal_js(data_json)
    html = html.replace('</body>', term_js + '\n</body>')

    DASHBOARD.write_text(html, encoding='utf-8')
    print(f'\n\u2705 Terminal Cases tab added! ({total_cases} cases, {total_stores} stores)')
    print(f'   index.html: {len(html):,} chars')


if __name__ == '__main__':
    main()
