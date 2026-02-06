#!/usr/bin/env python3
"""Add Win-the-Winter tab to TNT Dashboard - Enhanced Version"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime

# Paths
DASHBOARD_PATH = Path(__file__).parent / 'index.html'
WTW_DATA_PATH = Path.home() / 'bigquery_results' / 'wtw-pm-scores-final-20260205-200434.csv'

def load_csv(path):
    """Load CSV file and return list of dicts"""
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def main():
    print("\U0001F4CA Loading WTW data...")
    
    # Load data
    wtw_data = load_csv(WTW_DATA_PATH)
    print(f"   Loaded {len(wtw_data)} work orders")
    
    # Compress WTW data for embedding - include all filter fields
    compressed_wtw = []
    for wo in wtw_data:
        phase_raw = wo.get('phase', '')
        if 'PH3' in phase_raw:
            phase = 'PH3'
        elif 'PH2' in phase_raw:
            phase = 'PH2'
        else:
            phase = 'PH1'
        
        compressed_wtw.append({
            't': wo.get('tracking_nbr', ''),
            'w': wo.get('workorder_nbr', ''),
            's': wo.get('store_nbr', ''),
            'loc': wo.get('location_name', '')[:40] if wo.get('location_name') else '',
            'st': wo.get('status_name', ''),
            'est': wo.get('extended_status_name', ''),
            'ph': phase,
            'city': wo.get('city_name', ''),
            'state': wo.get('state_cd', ''),
            'srd': wo.get('fm_sr_director_name', ''),
            'fm': wo.get('fm_director_name', ''),
            'rm': wo.get('fm_regional_manager_name', ''),
            'fsm': wo.get('fs_manager_name', ''),
            'mkt': wo.get('fs_market', ''),
            'exp': wo.get('expiration_date', '')[:10] if wo.get('expiration_date') else '',
            'crt': wo.get('created_date', '')[:10] if wo.get('created_date') else '',
            'tnt': wo.get('tnt_score', ''),
            'rack': wo.get('rack_score', ''),
            'dewR': wo.get('dewpoint_raw', ''),
            'dew': wo.get('dewpoint_score', ''),
            'pm': wo.get('pm_score', ''),
            'rackP': wo.get('rack_pass', ''),
            'tntP': wo.get('tnt_pass', ''),
            'dewP': wo.get('dewpoint_pass', ''),
            'allP': wo.get('overall_pass', ''),
            'city': wo.get('city_name', ''),
            'state': wo.get('state_cd', ''),
        })
    
    # Calculate summary stats
    phase_counts = {'PH1': 0, 'PH2': 0, 'PH3': 0}
    status_counts = {}
    for wo in compressed_wtw:
        phase_counts[wo['ph']] = phase_counts.get(wo['ph'], 0) + 1
        est = wo['est'] or wo['st']
        status_counts[est] = status_counts.get(est, 0) + 1
    
    # Get unique values for filters
    sr_directors = sorted(set(wo['srd'] for wo in compressed_wtw if wo['srd']))
    fm_directors = sorted(set(wo['fm'] for wo in compressed_wtw if wo['fm']))
    reg_managers = sorted(set(wo['rm'] for wo in compressed_wtw if wo['rm']))
    fs_managers = sorted(set(wo['fsm'] for wo in compressed_wtw if wo['fsm']))
    markets = sorted(set(wo['mkt'] for wo in compressed_wtw if wo['mkt']))
    
    summary = {
        'total': len(wtw_data),
        'phases': phase_counts,
        'statuses': status_counts,
        'filters': {
            'sr_directors': sr_directors,
            'fm_directors': fm_directors,
            'reg_managers': reg_managers,
            'fs_managers': fs_managers,
            'markets': markets
        }
    }
    
    print(f"   Phases: {phase_counts}")
    print(f"   Sr Directors: {len(sr_directors)}, FM Directors: {len(fm_directors)}")
    print(f"   Markets: {len(markets)}")
    
    print("\n\U0001F4DD Reading dashboard HTML...")
    html = DASHBOARD_PATH.read_text(encoding='utf-8')
    
    # Remove old WTW content if exists
    if '<!-- WTW Tab Content -->' in html:
        print("   Removing old WTW tab...")
        # Remove old WTW content
        html = re.sub(r'<!-- WTW Tab Content -->.*?<!-- Footer -->', '<!-- Footer -->', html, flags=re.DOTALL)
        # Remove old WTW script
        html = re.sub(r'<script>\s*// WTW Data.*?</script>\s*</body>', '</body>', html, flags=re.DOTALL)
    
    # Create the tab navigation HTML (if not exists)
    if '<!-- Tab Navigation -->' not in html:
        tab_nav = '''
    <!-- Tab Navigation -->
    <div class="bg-white border-b border-gray-200 shadow-sm">
        <div class="max-w-7xl mx-auto px-4">
            <nav class="flex space-x-8" aria-label="Tabs">
                <button onclick="switchTab('tnt')" id="tab-tnt"
                        class="tab-btn border-b-2 border-walmart-blue text-walmart-blue py-4 px-1 text-sm font-medium">
                    \U0001F4CA TnT Dashboard
                </button>
                <button onclick="switchTab('wtw')" id="tab-wtw"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \u2744\ufe0f Win the Winter
                </button>
            </nav>
        </div>
    </div>
    '''
        html = html.replace('</header>', '</header>\n' + tab_nav)
    
    # Wrap existing main in tnt-content if not already
    if 'id="tnt-content"' not in html:
        html = html.replace(
            '<main class="max-w-7xl mx-auto px-4 py-6">',
            '<div id="tnt-content">\n    <main class="max-w-7xl mx-auto px-4 py-6">'
        )
    
    # Ensure tnt-content div is closed before WTW content
    if '</div>\n    \n    <!-- WTW Tab Content -->' not in html:
        html = html.replace(
            '</main>\n    \n    <!-- WTW Tab Content -->',
            '</main>\n    </div>\n    \n    <!-- WTW Tab Content -->'
        )
    
    # Create WTW tab content with full filters
    wtw_content = f'''
    <!-- WTW Tab Content -->
    <div id="wtw-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- WTW Header -->
            <div class="bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg shadow-lg p-6 mb-6 text-white">
                <div class="flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold">\u2744\ufe0f Win the Winter FY26</h1>
                        <p class="text-blue-100">Preventive Maintenance Work Order Tracking</p>
                    </div>
                    <div class="text-right">
                        <p class="text-3xl font-bold" id="wtwTotalCount">{summary['total']:,}</p>
                        <p class="text-sm text-blue-100">Total Open Work Orders</p>
                    </div>
                </div>
            </div>
            
            <!-- Phase Toggle Buttons -->
            <div class="bg-white rounded-lg shadow p-4 mb-6">
                <div class="flex flex-wrap gap-3 justify-center">
                    <button onclick="setWtwPhase('')" id="wtw-phase-all"
                            class="wtw-phase-btn px-6 py-3 rounded-lg font-semibold text-sm border-2 border-gray-300 bg-gray-100 text-gray-700">
                        All Phases ({summary['total']:,})
                    </button>
                    <button onclick="setWtwPhase('PH1')" id="wtw-phase-PH1"
                            class="wtw-phase-btn px-6 py-3 rounded-lg font-semibold text-sm border-2 border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100">
                        \U0001F7E6 Phase 1 ({phase_counts['PH1']:,})
                    </button>
                    <button onclick="setWtwPhase('PH2')" id="wtw-phase-PH2"
                            class="wtw-phase-btn px-6 py-3 rounded-lg font-semibold text-sm border-2 border-green-300 bg-green-50 text-green-700 hover:bg-green-100">
                        \U0001F7E2 Phase 2 ({phase_counts['PH2']:,})
                    </button>
                    <button onclick="setWtwPhase('PH3')" id="wtw-phase-PH3"
                            class="wtw-phase-btn px-6 py-3 rounded-lg font-semibold text-sm border-2 border-purple-300 bg-purple-50 text-purple-700 hover:bg-purple-100">
                        \U0001F7E3 Phase 3 ({phase_counts['PH3']:,})
                    </button>
                </div>
            </div>
            
            <!-- Filters (matching TNT tab) -->
            <div class="bg-white rounded-lg shadow p-4 mb-6">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-sm font-medium text-gray-700">Filters</h3>
                    <button onclick="clearWtwFilters()" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm rounded-md transition">
                        \u2715 Clear All Filters
                    </button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Sr. Director</label>
                        <select id="wtwFilterSrDirector" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All Sr. Directors</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">FM Director</label>
                        <select id="wtwFilterDirector" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All Directors</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Regional Manager</label>
                        <select id="wtwFilterManager" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All Managers</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">FS Manager</label>
                        <select id="wtwFilterFSManager" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All FS Managers</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Market</label>
                        <select id="wtwFilterMarket" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All Markets</option>
                        </select>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                        <select id="wtwFilterStatus" onchange="filterWtwData()" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                            <option value="">All Statuses</option>
                            <option value="INCOMPLETE">Incomplete</option>
                            <option value="DISPATCH CONFIRMED">Dispatch Confirmed</option>
                            <option value="PARTS DELIVERED">Parts Delivered</option>
                            <option value="PARTS ON ORDER">Parts On Order</option>
                            <option value="OPEN">Open (Unassigned)</option>
                            <option value="COMPLETED">Completed</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
                        <input type="text" id="wtwSearch" onkeyup="filterWtwData()" placeholder="Store #, city, or tracking #..." 
                               class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-walmart-blue focus:border-walmart-blue text-sm">
                    </div>
                    <div class="flex items-end">
                        <p class="text-sm text-gray-500">Showing <span id="wtwFilteredCount" class="font-bold text-walmart-blue">0</span> work orders</p>
                    </div>
                </div>
            </div>
            
            <!-- KPIs Row -->
            <div class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6" id="wtwKpiRow">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                    <p class="text-sm text-gray-500 uppercase">Completed</p>
                    <p class="text-2xl font-bold text-green-600" id="wtwKpiCompleted">0</p>
                    <p class="text-xs text-gray-400" id="wtwKpiCompletionRate">0% complete</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
                    <p class="text-sm text-gray-500 uppercase">Incomplete</p>
                    <p class="text-2xl font-bold text-red-600" id="wtwKpiIncomplete">{status_counts.get('INCOMPLETE', 0):,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
                    <p class="text-sm text-gray-500 uppercase">Dispatched</p>
                    <p class="text-2xl font-bold text-yellow-600" id="wtwKpiDispatch">{status_counts.get('DISPATCH CONFIRMED', 0):,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                    <p class="text-sm text-gray-500 uppercase">Parts Delivered</p>
                    <p class="text-2xl font-bold text-blue-600" id="wtwKpiPartsDelivered">{status_counts.get('PARTS DELIVERED', 0):,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
                    <p class="text-sm text-gray-500 uppercase">Parts On Order</p>
                    <p class="text-2xl font-bold text-orange-600" id="wtwKpiPartsOrder">{status_counts.get('PARTS ON ORDER', 0):,}</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-gray-500">
                    <p class="text-sm text-gray-500 uppercase">Open</p>
                    <p class="text-2xl font-bold text-gray-600" id="wtwKpiOpen">{status_counts.get('', 0):,}</p>
                </div>
            </div>
            
            <!-- Charts Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">Status Distribution</h3>
                    <div style="height: 280px;">
                        <canvas id="wtwStatusChart"></canvas>
                    </div>
                </div>
                <div class="bg-white rounded-lg shadow p-4">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">Phase Distribution</h3>
                    <div style="height: 280px;">
                        <canvas id="wtwPhaseChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Work Order Table -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b border-gray-200">
                    <div class="flex flex-wrap justify-between items-center gap-4">
                        <h3 class="text-lg font-semibold text-gray-800">Work Orders</h3>
                        <div class="flex gap-2">
                            <button onclick="setWtwStatus('')" id="wtw-status-all"
                                    class="wtw-status-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-gray-300 bg-gray-100 text-gray-700 ring-2 ring-offset-2 ring-walmart-blue">
                                All
                            </button>
                            <button onclick="setWtwStatus('COMPLETED')" id="wtw-status-COMPLETED"
                                    class="wtw-status-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-green-400 bg-green-50 text-green-700 hover:bg-green-100">
                                ✓ Completed
                            </button>
                            <button onclick="setWtwStatus('IN_PROGRESS')" id="wtw-status-IN_PROGRESS"
                                    class="wtw-status-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-yellow-400 bg-yellow-50 text-yellow-700 hover:bg-yellow-100">
                                ⏳ In Progress
                            </button>
                            <button onclick="setWtwStatus('OPEN')" id="wtw-status-OPEN"
                                    class="wtw-status-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-gray-400 bg-gray-50 text-gray-700 hover:bg-gray-100">
                                ○ Open
                            </button>
                        </div>
                    </div>
                </div>
                <div class="overflow-x-auto" style="max-height: 600px;">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('s')">Store \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('ph')">Phase \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('est')">Status \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">FM Director</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Regional Mgr</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('pm')">PM Score \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('rack')">Rack \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('tnt')">TnT \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Dewpoint</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('exp')">Expires \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Links</th>
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
    
    // WTW State
    let wtwCurrentPhase = '';
    let wtwCurrentStatus = '';
    let wtwSortField = 's';
    let wtwSortAsc = true;
    let wtwFilteredData = [];
    
    // Service Channel URL
    const SC_URL = 'https://servicechannel.walmart.com/sc/wo/workorders/';
    
    // Tab switching
    function switchTab(tab) {{
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.classList.remove('border-walmart-blue', 'text-walmart-blue');
            btn.classList.add('border-transparent', 'text-gray-500');
        }});
        document.getElementById('tab-' + tab).classList.remove('border-transparent', 'text-gray-500');
        document.getElementById('tab-' + tab).classList.add('border-walmart-blue', 'text-walmart-blue');
        
        if (tab === 'tnt') {{
            document.getElementById('tnt-content').classList.remove('hidden');
            document.getElementById('wtw-content').classList.add('hidden');
        }} else {{
            document.getElementById('tnt-content').classList.add('hidden');
            document.getElementById('wtw-content').classList.remove('hidden');
            initWtwTab();
        }}
    }}
    
    // Initialize WTW tab
    let wtwInitialized = false;
    function initWtwTab() {{
        if (wtwInitialized) return;
        wtwInitialized = true;
        
        // Populate filter dropdowns
        populateWtwFilters();
        // Initialize charts
        initWtwCharts();
        // Initial data filter
        filterWtwData();
    }}
    
    // Populate filter dropdowns
    function populateWtwFilters() {{
        const filters = WTW_SUMMARY.filters;
        
        const srSel = document.getElementById('wtwFilterSrDirector');
        filters.sr_directors.forEach(v => srSel.add(new Option(v, v)));
        
        const fmSel = document.getElementById('wtwFilterDirector');
        filters.fm_directors.forEach(v => fmSel.add(new Option(v, v)));
        
        const rmSel = document.getElementById('wtwFilterManager');
        filters.reg_managers.forEach(v => rmSel.add(new Option(v, v)));
        
        const fsmSel = document.getElementById('wtwFilterFSManager');
        filters.fs_managers.forEach(v => fsmSel.add(new Option(v, v)));
        
        const mktSel = document.getElementById('wtwFilterMarket');
        filters.markets.forEach(v => mktSel.add(new Option(v, v)));
    }}
    
    // Set phase filter
    function setWtwPhase(phase) {{
        wtwCurrentPhase = phase;
        // Update button styles
        document.querySelectorAll('.wtw-phase-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        const activeBtn = document.getElementById('wtw-phase-' + (phase || 'all'));
        if (activeBtn) {{
            activeBtn.classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }}
        filterWtwData();
    }}
    
    // Set status filter (button toggle)
    function setWtwStatus(status) {{
        wtwCurrentStatus = status;
        // Update button styles
        document.querySelectorAll('.wtw-status-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        const activeBtn = document.getElementById('wtw-status-' + (status || 'all'));
        if (activeBtn) {{
            activeBtn.classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }}
        // Clear the dropdown filter to avoid confusion
        document.getElementById('wtwFilterStatus').value = '';
        filterWtwData();
    }}
    
    // Clear all WTW filters
    function clearWtwFilters() {{
        wtwCurrentPhase = '';
        wtwCurrentStatus = '';
        document.getElementById('wtwFilterSrDirector').value = '';
        document.getElementById('wtwFilterDirector').value = '';
        document.getElementById('wtwFilterManager').value = '';
        document.getElementById('wtwFilterFSManager').value = '';
        document.getElementById('wtwFilterMarket').value = '';
        document.getElementById('wtwFilterStatus').value = '';
        document.getElementById('wtwSearch').value = '';
        document.querySelectorAll('.wtw-phase-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        document.querySelectorAll('.wtw-status-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        document.getElementById('wtw-phase-all').classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        document.getElementById('wtw-status-all').classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        filterWtwData();
    }}
    
    // Filter WTW data
    function filterWtwData() {{
        const srDir = document.getElementById('wtwFilterSrDirector').value;
        const fmDir = document.getElementById('wtwFilterDirector').value;
        const rm = document.getElementById('wtwFilterManager').value;
        const fsm = document.getElementById('wtwFilterFSManager').value;
        const mkt = document.getElementById('wtwFilterMarket').value;
        const status = document.getElementById('wtwFilterStatus').value;
        const search = document.getElementById('wtwSearch').value.toLowerCase();
        
        wtwFilteredData = WTW_DATA.filter(wo => {{
            if (wtwCurrentPhase && wo.ph !== wtwCurrentPhase) return false;
            if (srDir && wo.srd !== srDir) return false;
            if (fmDir && wo.fm !== fmDir) return false;
            if (rm && wo.rm !== rm) return false;
            if (fsm && wo.fsm !== fsm) return false;
            if (mkt && wo.mkt !== mkt) return false;
            // Status button filter (takes priority)
            if (wtwCurrentStatus === 'COMPLETED' && wo.st !== 'COMPLETED') return false;
            if (wtwCurrentStatus === 'IN_PROGRESS' && wo.st !== 'IN PROGRESS') return false;
            if (wtwCurrentStatus === 'OPEN' && wo.st !== 'OPEN') return false;
            // Dropdown filter (if no button selected)
            if (!wtwCurrentStatus) {{
                if (status === 'COMPLETED' && wo.st !== 'COMPLETED') return false;
                if (status === 'OPEN' && wo.st !== 'OPEN' && wo.est !== '') return false;
                if (status && status !== 'OPEN' && status !== 'COMPLETED' && wo.est !== status) return false;
            }}
            if (search) {{
                const searchStr = (wo.s + ' ' + wo.city + ' ' + wo.t + ' ' + wo.fm + ' ' + wo.loc).toLowerCase();
                if (!searchStr.includes(search)) return false;
            }}
            return true;
        }});
        
        // Update filtered count
        document.getElementById('wtwFilteredCount').textContent = wtwFilteredData.length.toLocaleString();
        
        // Update KPIs based on filtered data
        updateWtwKpis();
        
        // Update charts
        updateWtwCharts();
        
        // Render table
        renderWtwTable();
    }}
    
    // Update KPIs
    function updateWtwKpis() {{
        const counts = {{'COMPLETED': 0, 'INCOMPLETE': 0, 'DISPATCH CONFIRMED': 0, 'PARTS DELIVERED': 0, 'PARTS ON ORDER': 0, 'OPEN': 0}};
        wtwFilteredData.forEach(wo => {{
            if (wo.st === 'COMPLETED') {{
                counts['COMPLETED']++;
            }} else {{
                const est = wo.est || 'OPEN';
                if (counts.hasOwnProperty(est)) counts[est]++;
                else if (est.includes('PARTS')) counts['PARTS ON ORDER']++;
            }}
        }});
        const total = wtwFilteredData.length;
        const completionRate = total > 0 ? ((counts['COMPLETED'] / total) * 100).toFixed(1) : 0;
        document.getElementById('wtwKpiCompleted').textContent = counts['COMPLETED'].toLocaleString();
        document.getElementById('wtwKpiCompletionRate').textContent = completionRate + '% complete';
        document.getElementById('wtwKpiIncomplete').textContent = counts['INCOMPLETE'].toLocaleString();
        document.getElementById('wtwKpiDispatch').textContent = counts['DISPATCH CONFIRMED'].toLocaleString();
        document.getElementById('wtwKpiPartsDelivered').textContent = counts['PARTS DELIVERED'].toLocaleString();
        document.getElementById('wtwKpiPartsOrder').textContent = counts['PARTS ON ORDER'].toLocaleString();
        document.getElementById('wtwKpiOpen').textContent = counts['OPEN'].toLocaleString();
    }}
    
    // Sort WTW table
    function sortWtwTable(field) {{
        if (wtwSortField === field) {{
            wtwSortAsc = !wtwSortAsc;
        }} else {{
            wtwSortField = field;
            wtwSortAsc = true;
        }}
        renderWtwTable();
    }}
    
    // Render WTW table
    function renderWtwTable() {{
        // Sort data
        const sorted = [...wtwFilteredData].sort((a, b) => {{
            let aVal = a[wtwSortField] || '';
            let bVal = b[wtwSortField] || '';
            if (wtwSortField === 's') {{
                aVal = parseInt(aVal) || 0;
                bVal = parseInt(bVal) || 0;
            }}
            if (aVal < bVal) return wtwSortAsc ? -1 : 1;
            if (aVal > bVal) return wtwSortAsc ? 1 : -1;
            return 0;
        }});
        
        // Limit display
        const display = sorted.slice(0, 300);
        
        const table = document.getElementById('wtwWoTable');
        table.innerHTML = display.map(wo => {{
            const phaseClass = wo.ph === 'PH1' ? 'bg-blue-100 text-blue-800' : 
                               wo.ph === 'PH2' ? 'bg-green-100 text-green-800' : 
                               'bg-purple-100 text-purple-800';
            const statusClass = wo.st === 'COMPLETED' ? 'text-green-600 font-semibold' : 
                               wo.est === 'INCOMPLETE' ? 'text-red-600 font-semibold' : 'text-gray-600';
            const statusText = wo.st === 'COMPLETED' ? '✓ COMPLETED' : (wo.est || wo.st);
            return `
                <tr class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-sm font-medium text-walmart-blue">${{wo.s}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{wo.city}}${{wo.city && wo.state ? ', ' : ''}}${{wo.state}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded-full text-xs font-semibold ${{phaseClass}}">${{wo.ph}}</span>
                    </td>
                    <td class="px-3 py-2 text-sm ${{statusClass}}">${{statusText}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{wo.fm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{wo.rm || '-'}}</td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.pm ? `
                            <div class="flex items-center justify-center gap-1">
                                <span class="px-2 py-1 rounded text-xs font-bold ${{wo.allP === 'PASS' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}}">
                                    ${{parseFloat(wo.pm).toFixed(1)}}%
                                </span>
                                <span class="text-sm ${{wo.allP === 'PASS' ? 'text-green-600' : 'text-red-600'}}">
                                    ${{wo.allP === 'PASS' ? '✓' : '✗'}}
                                </span>
                            </div>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.rack ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.rackP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{parseFloat(wo.rack).toFixed(1)}}% ${{wo.rackP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.tnt ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.tntP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{parseFloat(wo.tnt).toFixed(1)}}% ${{wo.tntP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.dewR ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.dewP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{wo.dewR}}°F ${{wo.dewP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center text-gray-500">${{wo.exp}}</td>
                    <td class="px-3 py-2 text-sm text-center">
                        <div class="flex gap-2 justify-center">
                            <a href="${{SC_URL}}${{wo.t}}" target="_blank" 
                               class="text-walmart-blue hover:underline text-xs" title="Service Channel">
                                SC \u2197
                            </a>
                            <a href="https://crystal.walmart.com/us/stores/search/${{wo.s}}" target="_blank" 
                               class="text-green-600 hover:underline text-xs" title="Crystal Store">
                                Crystal \u2197
                            </a>
                            <a href="https://crystal.walmart.com/us/reports/custom-reports/46?report-name=win-the-winter---store-details&report-filters=Store%2520Number%255B0%255D%3D${{wo.s}}" target="_blank" 
                               class="text-purple-600 hover:underline text-xs" title="WTW Report">
                                WTW \u2197
                            </a>
                        </div>
                    </td>
                </tr>
            `;
        }}).join('');
        
        if (sorted.length > 300) {{
            table.innerHTML += `<tr><td colspan="12" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} results. Use filters to narrow down.</td></tr>`;
        }}
    }}
    
    // Charts
    let wtwStatusChart = null;
    let wtwPhaseChart = null;
    
    function initWtwCharts() {{
        // Status chart
        const statusCtx = document.getElementById('wtwStatusChart').getContext('2d');
        wtwStatusChart = new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Completed', 'Incomplete', 'Dispatched', 'Parts Delivered', 'Parts On Order', 'Open'],
                datasets: [{{
                    data: [0, 0, 0, 0, 0, 0],
                    backgroundColor: ['#22c55e', '#ef4444', '#eab308', '#3b82f6', '#f97316', '#6b7280'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right', labels: {{ boxWidth: 12, padding: 15 }} }},
                    datalabels: {{
                        color: '#fff',
                        font: {{ weight: 'bold', size: 11 }},
                        formatter: (value, ctx) => {{
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            if (total === 0) return '';
                            const pct = ((value / total) * 100).toFixed(0);
                            return pct > 5 ? pct + '%' : '';
                        }}
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
        
        // Phase chart
        const phaseCtx = document.getElementById('wtwPhaseChart').getContext('2d');
        wtwPhaseChart = new Chart(phaseCtx, {{
            type: 'bar',
            data: {{
                labels: ['Phase 1', 'Phase 2', 'Phase 3'],
                datasets: [{{
                    label: 'Work Orders',
                    data: [0, 0, 0],
                    backgroundColor: ['#3b82f6', '#22c55e', '#a855f7'],
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    datalabels: {{
                        color: '#fff',
                        anchor: 'center',
                        font: {{ weight: 'bold', size: 14 }},
                        formatter: (value) => value > 0 ? value.toLocaleString() : ''
                    }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
        
        updateWtwCharts();
    }}
    
    function updateWtwCharts() {{
        if (!wtwStatusChart || !wtwPhaseChart) return;
        
        // Count statuses in filtered data
        const statusCounts = {{'COMPLETED': 0, 'INCOMPLETE': 0, 'DISPATCH CONFIRMED': 0, 'PARTS DELIVERED': 0, 'PARTS ON ORDER': 0, 'OPEN': 0}};
        const phaseCounts = {{'PH1': 0, 'PH2': 0, 'PH3': 0}};
        
        wtwFilteredData.forEach(wo => {{
            if (wo.st === 'COMPLETED') {{
                statusCounts['COMPLETED']++;
            }} else {{
                const est = wo.est || 'OPEN';
                if (statusCounts.hasOwnProperty(est)) statusCounts[est]++;
                else if (est.includes('PARTS')) statusCounts['PARTS ON ORDER']++;
            }}
            phaseCounts[wo.ph] = (phaseCounts[wo.ph] || 0) + 1;
        }});
        
        wtwStatusChart.data.datasets[0].data = [
            statusCounts['COMPLETED'],
            statusCounts['INCOMPLETE'],
            statusCounts['DISPATCH CONFIRMED'],
            statusCounts['PARTS DELIVERED'],
            statusCounts['PARTS ON ORDER'],
            statusCounts['OPEN']
        ];
        wtwStatusChart.update();
        
        wtwPhaseChart.data.datasets[0].data = [
            phaseCounts['PH1'],
            phaseCounts['PH2'],
            phaseCounts['PH3']
        ];
        wtwPhaseChart.update();
    }}
    </script>
    '''
    
    # Insert WTW content before Footer
    html = re.sub(
        r'(</div>\s*<!-- Footer -->)',
        wtw_content + '\n\n    <!-- Footer -->',
        html,
        count=1
    )
    
    # Add WTW JavaScript before closing body
    html = html.replace('</body>', wtw_js + '\n</body>')
    
    # Update timestamp
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = re.sub(r'Data as of [0-9-]+ [0-9:]+', f'Data as of {now}', html)
    
    # Save
    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print(f"\n\u2705 Dashboard updated with enhanced WTW tab!")
    print(f"   - {len(compressed_wtw):,} work orders with full filter data")
    print(f"   - Clickable tracking numbers linking to Service Channel")
    print(f"   - Phase filter buttons")
    print(f"   - Same filters as TNT tab (Sr. Dir, FM Dir, RM, FSM, Market)")

if __name__ == '__main__':
    main()
