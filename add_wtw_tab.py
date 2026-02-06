#!/usr/bin/env python3
"""Add Win-the-Winter tab to TNT Dashboard"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime

# Paths
DASHBOARD_PATH = Path(__file__).parent / 'index.html'
WTW_DATA_PATH = Path.home() / 'bigquery_results' / 'wtw-fy26-full-with-fm-20260205-190331.csv'
WTW_STATUS_PATH = Path.home() / 'bigquery_results' / 'wtw-status-breakdown-20260205-190257.csv'
WTW_PHASE_PATH = Path.home() / 'bigquery_results' / 'wtw-phase-breakdown-20260205-190251.csv'
WTW_FM_PATH = Path.home() / 'bigquery_results' / 'wtw-fm-director-summary-20260205-190327.csv'

def load_csv(path):
    """Load CSV file and return list of dicts"""
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def main():
    print("📊 Loading WTW data...")
    
    # Load data
    wtw_data = load_csv(WTW_DATA_PATH)
    status_data = load_csv(WTW_STATUS_PATH)
    phase_data = load_csv(WTW_PHASE_PATH)
    fm_data = load_csv(WTW_FM_PATH)
    
    print(f"   Loaded {len(wtw_data)} work orders")
    print(f"   Loaded {len(status_data)} status categories")
    print(f"   Loaded {len(phase_data)} phase categories")
    print(f"   Loaded {len(fm_data)} FM directors")
    
    # Compress WTW data for embedding
    compressed_wtw = []
    for wo in wtw_data:
        compressed_wtw.append({
            't': wo.get('tracking_nbr', ''),
            'w': wo.get('workorder_nbr', ''),
            's': wo.get('store_nbr', ''),
            'loc': wo.get('location_name', '')[:30] if wo.get('location_name') else '',
            'st': wo.get('status_name', ''),
            'est': wo.get('extended_status_name', ''),
            'lbl': wo.get('label', '').replace('Win_The_Winter_FY26', 'PH1').replace('_PH2', 'PH2').replace('_PH3', 'PH3'),
            'prob': wo.get('problem_type_desc', '')[:40] if wo.get('problem_type_desc') else '',
            'prov': wo.get('provider_name', '')[:20] if wo.get('provider_name') else '',
            'city': wo.get('city_name', ''),
            'state': wo.get('state_cd', ''),
            'fm': wo.get('fm_director_name', ''),
            'rm': wo.get('fm_regional_manager_name', ''),
            'mkt': wo.get('fs_market', ''),
            'exp': wo.get('expiration_date', '')[:10] if wo.get('expiration_date') else '',
            'crt': wo.get('created_date', '')[:10] if wo.get('created_date') else '',
        })
    
    # Create summary stats
    summary = {
        'total': len(wtw_data),
        'phases': {},
        'statuses': {},
        'fm_directors': []
    }
    
    for p in phase_data:
        phase_name = p['phase'].replace('Win_The_Winter_FY26', 'Phase 1').replace('_PH2', '').replace('_PH3', '')
        if 'PH2' in p['phase']:
            phase_name = 'Phase 2'
        elif 'PH3' in p['phase']:
            phase_name = 'Phase 3'
        if phase_name not in summary['phases']:
            summary['phases'][phase_name] = 0
        summary['phases'][phase_name] += int(p['work_order_count'])
    
    for s in status_data:
        key = s['extended_status_name'] or s['status_name']
        summary['statuses'][key] = int(s['work_order_count'])
    
    for fm in fm_data:
        summary['fm_directors'].append({
            'name': fm['fm_director_name'],
            'total': int(fm['total_work_orders']),
            'incomplete': int(fm['incomplete']),
            'dispatch': int(fm['dispatch_confirmed']),
            'parts': int(fm['parts_pending']),
            'open': int(fm['open_unassigned']),
            'pct': float(fm['pct_incomplete'])
        })
    
    print("\n📝 Reading dashboard HTML...")
    html = DASHBOARD_PATH.read_text(encoding='utf-8')
    
    # Create the tab navigation HTML
    tab_nav = '''
    <!-- Tab Navigation -->
    <div class="bg-white border-b border-gray-200 shadow-sm">
        <div class="max-w-7xl mx-auto px-4">
            <nav class="flex space-x-8" aria-label="Tabs">
                <button onclick="switchTab('tnt')" id="tab-tnt"
                        class="tab-btn border-b-2 border-walmart-blue text-walmart-blue py-4 px-1 text-sm font-medium">
                    📊 TnT Dashboard
                </button>
                <button onclick="switchTab('wtw')" id="tab-wtw"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    ❄️ Win the Winter
                </button>
            </nav>
        </div>
    </div>
    '''
    
    # Create WTW tab content
    wtw_content = f'''
    <!-- WTW Tab Content -->
    <div id="wtw-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- WTW Header -->
            <div class="bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg shadow-lg p-6 mb-6 text-white">
                <div class="flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold">❄️ Win the Winter FY26</h1>
                        <p class="text-blue-100">Preventive Maintenance Work Order Tracking</p>
                    </div>
                    <div class="text-right">
                        <p class="text-3xl font-bold">{summary['total']:,}</p>
                        <p class="text-sm text-blue-100">Total Open Work Orders</p>
                    </div>
                </div>
            </div>
            
            <!-- Phase KPIs -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                    <p class="text-sm text-gray-500 uppercase">Phase 1</p>
                    <p class="text-3xl font-bold text-blue-600">{summary['phases'].get('Phase 1', 0):,}</p>
                    <p class="text-xs text-gray-400">Expires Apr 30, 2026</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                    <p class="text-sm text-gray-500 uppercase">Phase 2</p>
                    <p class="text-3xl font-bold text-green-600">{summary['phases'].get('Phase 2', 0):,}</p>
                    <p class="text-xs text-gray-400">Expires Jun 29, 2026</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                    <p class="text-sm text-gray-500 uppercase">Phase 3</p>
                    <p class="text-3xl font-bold text-purple-600">{summary['phases'].get('Phase 3', 0):,}</p>
                    <p class="text-xs text-gray-400">Expires Jun 29, 2026</p>
                </div>
            </div>
            
            <!-- Status Breakdown -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <!-- Status Chart -->
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">Status Breakdown</h3>
                    <div style="height: 300px;">
                        <canvas id="wtwStatusChart"></canvas>
                    </div>
                </div>
                
                <!-- Status Stats -->
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">Status Details</h3>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center p-2 bg-red-50 rounded">
                            <span class="text-sm font-medium text-red-800">Incomplete</span>
                            <span class="text-lg font-bold text-red-600">{summary['statuses'].get('INCOMPLETE', 0):,}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-yellow-50 rounded">
                            <span class="text-sm font-medium text-yellow-800">Dispatch Confirmed</span>
                            <span class="text-lg font-bold text-yellow-600">{summary['statuses'].get('DISPATCH CONFIRMED', 0):,}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-blue-50 rounded">
                            <span class="text-sm font-medium text-blue-800">Parts Delivered</span>
                            <span class="text-lg font-bold text-blue-600">{summary['statuses'].get('PARTS DELIVERED', 0):,}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-orange-50 rounded">
                            <span class="text-sm font-medium text-orange-800">Parts On Order</span>
                            <span class="text-lg font-bold text-orange-600">{summary['statuses'].get('PARTS ON ORDER', 0):,}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-gray-50 rounded">
                            <span class="text-sm font-medium text-gray-800">Open (Unassigned)</span>
                            <span class="text-lg font-bold text-gray-600">{summary['statuses'].get('', 0) + summary['statuses'].get('OPEN', 0):,}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- FM Director Table -->
            <div class="bg-white rounded-lg shadow mb-6">
                <div class="p-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-800">FM Director Performance</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">FM Director</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total WOs</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Incomplete</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Dispatched</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Parts Pending</th>
                                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Incomplete</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200" id="wtwFmTable">
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- WTW Work Order Table -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b border-gray-200 flex justify-between items-center">
                    <h3 class="text-lg font-semibold text-gray-800">Work Orders</h3>
                    <div class="flex gap-2">
                        <select id="wtwPhaseFilter" onchange="filterWtwTable()" class="border rounded px-2 py-1 text-sm">
                            <option value="">All Phases</option>
                            <option value="PH1">Phase 1</option>
                            <option value="PH2">Phase 2</option>
                            <option value="PH3">Phase 3</option>
                        </select>
                        <select id="wtwStatusFilter" onchange="filterWtwTable()" class="border rounded px-2 py-1 text-sm">
                            <option value="">All Statuses</option>
                            <option value="INCOMPLETE">Incomplete</option>
                            <option value="DISPATCH CONFIRMED">Dispatch Confirmed</option>
                            <option value="PARTS">Parts Pending</option>
                        </select>
                        <input type="text" id="wtwSearch" onkeyup="filterWtwTable()" placeholder="Search store..." 
                               class="border rounded px-2 py-1 text-sm w-40">
                    </div>
                </div>
                <div class="overflow-x-auto" style="max-height: 500px;">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Store</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Phase</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">FM Director</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Expires</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tracking #</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200" id="wtwWoTable">
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    </div>
    '''
    
    # Create the WTW JavaScript
    wtw_js = f'''
    <script>
    // WTW Data
    const WTW_DATA = {json.dumps(compressed_wtw, separators=(',', ':'))};
    const WTW_SUMMARY = {json.dumps(summary, separators=(',', ':'))};
    
    // Tab switching
    function switchTab(tab) {{
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.classList.remove('border-walmart-blue', 'text-walmart-blue');
            btn.classList.add('border-transparent', 'text-gray-500');
        }});
        document.getElementById('tab-' + tab).classList.remove('border-transparent', 'text-gray-500');
        document.getElementById('tab-' + tab).classList.add('border-walmart-blue', 'text-walmart-blue');
        
        // Toggle content
        if (tab === 'tnt') {{
            document.getElementById('tnt-content').classList.remove('hidden');
            document.getElementById('wtw-content').classList.add('hidden');
        }} else {{
            document.getElementById('tnt-content').classList.add('hidden');
            document.getElementById('wtw-content').classList.remove('hidden');
            initWtwCharts();
            renderWtwTables();
        }}
    }}
    
    // Initialize WTW charts
    let wtwStatusChart = null;
    function initWtwCharts() {{
        if (wtwStatusChart) return; // Already initialized
        
        const ctx = document.getElementById('wtwStatusChart').getContext('2d');
        const statuses = WTW_SUMMARY.statuses;
        
        wtwStatusChart = new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['Incomplete', 'Dispatch Confirmed', 'Parts Delivered', 'Parts On Order', 'Open'],
                datasets: [{{
                    data: [
                        statuses['INCOMPLETE'] || 0,
                        statuses['DISPATCH CONFIRMED'] || 0,
                        statuses['PARTS DELIVERED'] || 0,
                        statuses['PARTS ON ORDER'] || 0,
                        (statuses[''] || 0) + (statuses['OPEN'] || 0)
                    ],
                    backgroundColor: ['#ef4444', '#eab308', '#3b82f6', '#f97316', '#6b7280'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right' }},
                    datalabels: {{
                        color: '#fff',
                        font: {{ weight: 'bold' }},
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
    
    // Render WTW tables
    function renderWtwTables() {{
        // FM Director table
        const fmTable = document.getElementById('wtwFmTable');
        fmTable.innerHTML = WTW_SUMMARY.fm_directors.map(fm => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm font-medium text-gray-900">${{fm.name || 'Unknown'}}</td>
                <td class="px-4 py-2 text-sm text-center text-gray-600">${{fm.total}}</td>
                <td class="px-4 py-2 text-sm text-center text-red-600 font-semibold">${{fm.incomplete}}</td>
                <td class="px-4 py-2 text-sm text-center text-yellow-600">${{fm.dispatch}}</td>
                <td class="px-4 py-2 text-sm text-center text-orange-600">${{fm.parts}}</td>
                <td class="px-4 py-2 text-sm text-center">
                    <span class="px-2 py-1 rounded-full text-xs font-semibold ${{fm.pct > 50 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}}">
                        ${{fm.pct.toFixed(1)}}%
                    </span>
                </td>
            </tr>
        `).join('');
        
        filterWtwTable();
    }}
    
    // Filter WTW work order table
    function filterWtwTable() {{
        const phase = document.getElementById('wtwPhaseFilter').value;
        const status = document.getElementById('wtwStatusFilter').value;
        const search = document.getElementById('wtwSearch').value.toLowerCase();
        
        let filtered = WTW_DATA.filter(wo => {{
            if (phase && wo.lbl !== phase) return false;
            if (status === 'PARTS' && !wo.est.includes('PARTS')) return false;
            if (status && status !== 'PARTS' && wo.est !== status) return false;
            if (search && !wo.s.includes(search) && !(wo.loc || '').toLowerCase().includes(search) && !(wo.fm || '').toLowerCase().includes(search)) return false;
            return true;
        }});
        
        // Limit to 200 rows for performance
        const display = filtered.slice(0, 200);
        
        const table = document.getElementById('wtwWoTable');
        table.innerHTML = display.map(wo => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 text-sm font-medium text-walmart-blue">${{wo.s}}</td>
                <td class="px-3 py-2 text-sm text-gray-600">${{wo.city || ''}}${{wo.city && wo.state ? ', ' : ''}}${{wo.state || ''}}</td>
                <td class="px-3 py-2 text-center">
                    <span class="px-2 py-1 rounded-full text-xs font-semibold 
                        ${{wo.lbl === 'PH1' ? 'bg-blue-100 text-blue-800' : 
                          wo.lbl === 'PH2' ? 'bg-green-100 text-green-800' : 
                          'bg-purple-100 text-purple-800'}}">
                        ${{wo.lbl}}
                    </span>
                </td>
                <td class="px-3 py-2 text-sm">
                    <span class="${{wo.est === 'INCOMPLETE' ? 'text-red-600 font-semibold' : 'text-gray-600'}}">
                        ${{wo.est || wo.st}}
                    </span>
                </td>
                <td class="px-3 py-2 text-sm text-gray-600">${{wo.fm || '-'}}</td>
                <td class="px-3 py-2 text-sm text-center text-gray-500">${{wo.exp}}</td>
                <td class="px-3 py-2 text-sm text-gray-400">${{wo.t}}</td>
            </tr>
        `).join('');
        
        if (filtered.length > 200) {{
            table.innerHTML += `<tr><td colspan="7" class="px-3 py-2 text-center text-gray-400 text-sm">Showing 200 of ${{filtered.length}} results. Use filters to narrow.</td></tr>`;
        }}
    }}
    </script>
    '''
    
    # Now modify the HTML
    print("\n🔧 Modifying dashboard HTML...")
    
    # 1. Add tab navigation after header
    html = html.replace(
        '</header>',
        '</header>\n' + tab_nav
    )
    
    # 2. Wrap existing main content in tnt-content div
    html = html.replace(
        '<main class="max-w-7xl mx-auto px-4 py-6">',
        '<div id="tnt-content">\n    <main class="max-w-7xl mx-auto px-4 py-6">'
    )
    html = html.replace(
        '</main>\n\n    <!-- Footer -->',
        '</main>\n    </div>\n\n' + wtw_content + '\n\n    <!-- Footer -->'
    )
    
    # 3. Add WTW JavaScript before closing body tag
    html = html.replace(
        '</body>',
        wtw_js + '\n</body>'
    )
    
    # 4. Update the data timestamp
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = re.sub(
        r'Data as of [0-9-]+ [0-9:]+',
        f'Data as of {now}',
        html
    )
    
    # Save
    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print(f"\n✅ Dashboard updated with WTW tab!")
    print(f"   Added {len(compressed_wtw):,} WTW work orders")
    print(f"   Total phases: {list(summary['phases'].keys())}")
    print(f"   FM Directors: {len(summary['fm_directors'])}")

if __name__ == '__main__':
    main()
