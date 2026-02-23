#!/usr/bin/env python3
"""Add Win-the-Winter tab to TNT Dashboard - Enhanced Version"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime

# Paths
DASHBOARD_PATH = Path(__file__).parent / 'index.html'
WTW_DATA_PATH = Path.home() / 'bigquery_results' / 'wtw-fy26-workorders-pm-scores-labor-LATEST.csv'

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
            'loc': wo.get('store_name', '')[:40] if wo.get('store_name') else '',
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
            'dew': wo.get('dewpoint_raw', ''),
            'dewS': wo.get('dewpoint_score', ''),
            'pm': wo.get('pm_score', ''),
            'rackP': {'Y': 'PASS', 'N': 'FAIL'}.get(wo.get('rack_pass', ''), 'NO DATA'),
            'tntP': {'Y': 'PASS', 'N': 'FAIL'}.get(wo.get('tnt_pass', ''), 'NO DATA'),
            'dewP': {'Y': 'PASS', 'N': 'FAIL'}.get(wo.get('dewpoint_pass', ''), 'NO DATA'),
            'allP': {'Y': 'PASS', 'N': 'FAIL'}.get(wo.get('overall_pass', ''), 'FAIL'),
            'comp': wo.get('components_available', '3'),
            'div1': wo.get('is_div1', 'N'),
            'banner': wo.get('banner_desc', ''),
            'city': wo.get('city_name', ''),
            'state': wo.get('state_cd', ''),
            'repH': wo.get('repair_hrs', ''),
            'trvH': wo.get('travel_hrs', ''),
            'totH': wo.get('total_hrs', ''),
            'vis': wo.get('num_visits', ''),
            'techs': wo.get('num_techs', ''),
        })
    
    # Calculate summary stats with phase breakdown
    phase_counts = {'PH1': 0, 'PH2': 0, 'PH3': 0}
    phase_status = {
        'PH1': {'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0},
        'PH2': {'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0},
        'PH3': {'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}
    }
    status_counts = {}
    ready_to_complete = 0  # In Progress + all PM criteria pass
    should_reopen = 0  # Completed but PM criteria fail (non-Div1)
    should_reopen_div1 = 0  # Completed Div1 stores (manual review)
    div1_count = 0
    
    for wo in compressed_wtw:
        phase_counts[wo['ph']] = phase_counts.get(wo['ph'], 0) + 1
        est = wo['est'] or wo['st']
        status_counts[est] = status_counts.get(est, 0) + 1
        
        # Track status by phase
        st = wo['st']
        if st in phase_status[wo['ph']]:
            phase_status[wo['ph']][st] += 1
        
        # Count Div1 stores
        is_div1 = wo.get('div1', 'N') == 'Y'
        if is_div1:
            div1_count += 1
        
        # Count ready to complete and critical reopen
        # Critical Reopen: Completed + PM below banner threshold + 2+ fails + <8 repair hrs
        pm_score = float(wo.get('pm', 0) or 0)
        is_sams = 'Sam' in wo.get('banner', '')
        pm_threshold = 87 if is_sams else 90
        fail_count = sum(1 for x in [wo.get('rackP',''), wo.get('tntP',''), wo.get('dewP','')] if x == 'FAIL')
        repair_hrs = float(wo.get('repH', 0) or 0)
        
        if st != 'COMPLETED' and wo.get('allP') == 'PASS':
            ready_to_complete += 1
        elif st == 'COMPLETED' and pm_score < pm_threshold and fail_count >= 2 and repair_hrs < 8:
            if is_div1:
                should_reopen_div1 += 1
            else:
                should_reopen += 1
    
    # Get unique values for filters
    sr_directors = sorted(set(wo['srd'] for wo in compressed_wtw if wo['srd']))
    fm_directors = sorted(set(wo['fm'] for wo in compressed_wtw if wo['fm']))
    reg_managers = sorted(set(wo['rm'] for wo in compressed_wtw if wo['rm']))
    fs_managers = sorted(set(wo['fsm'] for wo in compressed_wtw if wo['fsm']))
    markets = sorted(set(wo['mkt'] for wo in compressed_wtw if wo['mkt']))
    
    summary = {
        'total': len(wtw_data),
        'phases': phase_counts,
        'phase_status': phase_status,
        'statuses': status_counts,
        'ready_to_complete': ready_to_complete,
        'should_reopen': should_reopen,
        'should_reopen_div1': should_reopen_div1,
        'div1_count': div1_count,
        'filters': {
            'sr_directors': sr_directors,
            'fm_directors': fm_directors,
            'reg_managers': reg_managers,
            'fs_managers': fs_managers,
            'markets': markets
        }
    }
    
    print(f"   Phases: {phase_counts}")
    print(f"   Phase Status: {phase_status}")
    print(f"   Ready to Complete: {ready_to_complete}, Should Reopen: {should_reopen} (+ {should_reopen_div1} Div1)")
    print(f"   Div1 Stores: {div1_count}")
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
    # Use regex to handle variable whitespace
    if not re.search(r'</div>\s*<!-- WTW Tab Content -->', html):
        html = re.sub(
            r'(</main>)(\s*)(<!-- WTW Tab Content -->)',
            r'\1\n    </div>\2\3',
            html,
            count=1
        )
    
    # Create WTW tab content with full filters
    wtw_content = f'''
    <!-- WTW Tab Content -->
    <div id="wtw-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- WTW Header -->
            <div class="bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg shadow-lg p-6 mb-4 text-white">
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
            
            <!-- Disclaimer -->
            <div class="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-r-lg">
                <div class="flex items-center">
                    <span class="text-amber-600 text-xl mr-3">\u26a0\ufe0f</span>
                    <p class="text-amber-800"><strong>Note:</strong> PM scores may vary up to <strong>1-3%</strong> from Crystal due to differences in data timing and calculation algorithms. Stores are flagged for review when PM score falls below <strong>87%</strong>.</p>
                </div>
            </div>
            
            <!-- Phase Cards with Status Bars (Dynamic) -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6" id="wtwPhaseCards">
                <!-- All Phases -->
                <div onclick="setWtwPhase('')" id="wtw-phase-all"
                     class="wtw-phase-btn cursor-pointer bg-white rounded-lg shadow p-4 border-2 border-gray-300 hover:border-gray-400 transition">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-gray-700">All Phases</span>
                        <span class="text-xl font-bold text-gray-800" id="wtw-phase-all-count">0</span>
                    </div>
                    <div class="h-6 rounded-full overflow-hidden flex bg-gray-200" id="wtw-phase-all-bar"></div>
                    <div class="flex justify-between text-xs text-gray-500 mt-1" id="wtw-phase-all-legend"></div>
                </div>
                
                <!-- Phase 1 -->
                <div onclick="setWtwPhase('PH1')" id="wtw-phase-PH1"
                     class="wtw-phase-btn cursor-pointer bg-blue-50 rounded-lg shadow p-4 border-2 border-blue-300 hover:border-blue-400 transition">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-blue-700">\U0001F7E6 Phase 1</span>
                        <span class="text-xl font-bold text-blue-800" id="wtw-phase-PH1-count">0</span>
                    </div>
                    <div class="h-6 rounded-full overflow-hidden flex bg-gray-200" id="wtw-phase-PH1-bar"></div>
                    <div class="flex justify-between text-xs text-blue-600 mt-1" id="wtw-phase-PH1-legend"></div>
                </div>
                
                <!-- Phase 2 -->
                <div onclick="setWtwPhase('PH2')" id="wtw-phase-PH2"
                     class="wtw-phase-btn cursor-pointer bg-green-50 rounded-lg shadow p-4 border-2 border-green-300 hover:border-green-400 transition">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-green-700">\U0001F7E2 Phase 2</span>
                        <span class="text-xl font-bold text-green-800" id="wtw-phase-PH2-count">0</span>
                    </div>
                    <div class="h-6 rounded-full overflow-hidden flex bg-gray-200" id="wtw-phase-PH2-bar"></div>
                    <div class="flex justify-between text-xs text-green-600 mt-1" id="wtw-phase-PH2-legend"></div>
                </div>
                
                <!-- Phase 3 -->
                <div onclick="setWtwPhase('PH3')" id="wtw-phase-PH3"
                     class="wtw-phase-btn cursor-pointer bg-purple-50 rounded-lg shadow p-4 border-2 border-purple-300 hover:border-purple-400 transition">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-purple-700">\U0001F7E3 Phase 3</span>
                        <span class="text-xl font-bold text-purple-800" id="wtw-phase-PH3-count">0</span>
                    </div>
                    <div class="h-6 rounded-full overflow-hidden flex bg-gray-200" id="wtw-phase-PH3-bar"></div>
                    <div class="flex justify-between text-xs text-purple-600 mt-1" id="wtw-phase-PH3-legend"></div>
                </div>
            </div>
            
            <!-- PM Readiness Buttons (Dynamic) -->
            <div class="bg-white rounded-lg shadow p-4 mb-6" id="wtwPmButtons">
                <div class="flex flex-wrap gap-3 justify-center items-center">
                    <span class="text-sm font-medium text-gray-600">PM Readiness:</span>
                    <button onclick="setWtwPmFilter('')" id="wtw-pm-all"
                            class="wtw-pm-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-gray-300 bg-gray-100 text-gray-700 ring-2 ring-offset-2 ring-walmart-blue">
                        All (<span id="wtw-pm-all-count">0</span>)
                    </button>
                    <button onclick="setWtwPmFilter('ready')" id="wtw-pm-ready"
                            class="wtw-pm-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-green-400 bg-green-50 text-green-700 hover:bg-green-100">
                        \u2713 Ready to Complete (<span id="wtw-pm-ready-count">0</span>)
                    </button>
                    <button onclick="setWtwPmFilter('review')" id="wtw-pm-review"
                            class="wtw-pm-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-yellow-400 bg-yellow-50 text-yellow-700 hover:bg-yellow-100">
                        \U0001F50D Review Needed (<span id="wtw-pm-review-count">0</span>)
                    </button>
                    <button onclick="setWtwPmFilter('critical')" id="wtw-pm-critical"
                            class="wtw-pm-btn px-4 py-2 rounded-lg text-sm font-semibold border-2 border-red-400 bg-red-50 text-red-700 hover:bg-red-100">
                        \u26a0 Critical Reopen (<span id="wtw-pm-critical-count">0</span>)
                    </button>
                </div>
                <div class="text-center text-xs text-gray-500 mt-2">
                    Ready = In Progress + All PM Pass | Review = PM \u226590% but failing 1+ criteria | Critical = PM &lt;90% + failing criteria
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
                            <option value="COMPLETED">Completed</option>
                            <option value="IN PROGRESS">In Progress</option>
                            <option value="OPEN">Open</option>
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
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6" id="wtwKpiRow">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                    <p class="text-sm text-gray-500 uppercase">Completed</p>
                    <p class="text-2xl font-bold text-green-600" id="wtwKpiCompleted">0</p>
                    <p class="text-xs text-gray-400" id="wtwKpiCompletionRate">0% complete</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
                    <p class="text-sm text-gray-500 uppercase">In Progress</p>
                    <p class="text-2xl font-bold text-yellow-600" id="wtwKpiInProgress">0</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-gray-500">
                    <p class="text-sm text-gray-500 uppercase">Open</p>
                    <p class="text-2xl font-bold text-gray-600" id="wtwKpiOpen">0</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-[#0053e2]">
                    <p class="text-sm text-gray-500 uppercase">Total</p>
                    <p class="text-2xl font-bold text-[#0053e2]" id="wtwKpiTotal">0</p>
                </div>
            </div>
            
            <!-- Labor Hours Summary -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-indigo-500">
                    <p class="text-sm text-gray-500 uppercase">Total Hours</p>
                    <p class="text-2xl font-bold text-indigo-600" id="wtwKpiTotalHrs">0</p>
                    <p class="text-xs text-gray-400" id="wtwKpiAvgHrs">0 avg/WO</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-cyan-500">
                    <p class="text-sm text-gray-500 uppercase">Repair Hours</p>
                    <p class="text-2xl font-bold text-cyan-600" id="wtwKpiRepairHrs">0</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-teal-500">
                    <p class="text-sm text-gray-500 uppercase">Travel Hours</p>
                    <p class="text-2xl font-bold text-teal-600" id="wtwKpiTravelHrs">0</p>
                </div>
                <div class="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                    <p class="text-sm text-gray-500 uppercase">Total Visits</p>
                    <p class="text-2xl font-bold text-purple-600" id="wtwKpiTotalVisits">0</p>
                    <p class="text-xs text-gray-400" id="wtwKpiAvgVisits">0 avg/WO</p>
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
            
            <!-- Director Summary Table -->
            <div class="bg-white rounded-lg shadow mb-6">
                <div class="p-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-800">\U0001F4CB Director Summary</h3>
                    <p class="text-sm text-gray-500">Completion by director with OPS Realty Region. Click headers to sort.</p>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortDirSummary('name')">Director \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortDirSummary('region')">Realty Region \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortDirSummary('stores')">Stores \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortDirSummary('total')">WOs \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-green-600 uppercase cursor-pointer hover:bg-green-50" onclick="sortDirSummary('completed')">Done \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-yellow-600 uppercase cursor-pointer hover:bg-yellow-50" onclick="sortDirSummary('ip')">IP \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-600 uppercase cursor-pointer hover:bg-gray-100" onclick="sortDirSummary('pct')">% Done \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-blue-600 uppercase cursor-pointer hover:bg-blue-50" onclick="sortDirSummary('ph1')">PH1 % \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-green-600 uppercase cursor-pointer hover:bg-green-50" onclick="sortDirSummary('ph2')">PH2 % \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-purple-600 uppercase cursor-pointer hover:bg-purple-50" onclick="sortDirSummary('ph3')">PH3 % \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-indigo-600 uppercase cursor-pointer hover:bg-indigo-50" onclick="sortDirSummary('hours')">Hours \u21C5</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-teal-600 uppercase cursor-pointer hover:bg-teal-50" onclick="sortDirSummary('ready')">Ready \u21C5</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200" id="wtwDirSummaryTable">
                        </tbody>
                    </table>
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
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('banner')">Banner \u21C5</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">RFM</th>
                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">FSM</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('pm')">PM Score \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('rack')">Rack \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('tnt')">TnT \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Dewpoint</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('totH')">Hours \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('vis')">Visits \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortWtwTable('exp')">Expires \u21C5</th>
                                <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Links</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200" id="wtwWoTable">
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Completion % by Manager Tables -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                <!-- FSM Completion Table -->
                <div class="bg-white rounded-lg shadow">
                    <div class="p-4 border-b border-gray-200">
                        <h3 class="text-lg font-semibold text-gray-800">\U0001F4CA Phase Completion by FSM</h3>
                        <p class="text-sm text-gray-500">Filtered by Sr. Director & FM Director only. Click headers to sort.</p>
                    </div>
                    <div class="overflow-x-auto max-h-96">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50 sticky top-0">
                                <tr>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortFsmTable('name')">FSM \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-blue-600 uppercase cursor-poer:bg-blue-50" onclick="sortFsmTable('ph1')">PH1 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-green-600 uppercase cursor-pointer hover:bg-green-50" onclick="sortFsmTable('ph2')">PH2 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-purple-600 uppercase cursor-pointer hover:bg-purple-50" onclick="sortFsmTable('ph3')">PH3 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-gray-600 uppercase cursor-pointer hover:bg-gray-100" onclick="sortFsmTable('overall')">Overall \u21C5</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200" id="fsmCompletionTable">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- RFM Completion Table -->
                <div class="bg-white rounded-lg shadow">
                    <div class="p-4 border-b border-gray-200">
                        <h3 class="text-lg font-semibold text-gray-800">\U0001F4CA Phase Completion by RFM</h3>
                        <p class="text-sm text-gray-500">Filtered by Sr. Director & FM Director only. Click headers to sort.</p>
                    </div>
                    <div class="overflow-x-auto max-h-96">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50 sticky top-0">
                                <tr>
                                    <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortRfmTable('name')">RFM \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-blue-600 uppercase cursor-pointer hover:bg-blue-50" onclick="sortRfmTable('ph1')">PH1 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-green-600 uppercase cursor-pointer hover:bg-green-50" onclick="sortRfmTable('ph2')">PH2 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-purple-600 uppercase cursor-pointer hover:bg-purple-50" onclick="sortRfmTable('ph3')">PH3 % \u21C5</th>
                                    <th class="px-3 py-2 text-center text-xs font-medium text-gray-600 uppercase cursor-pointer hover:bg-gray-100" onclick="sortRfmTable('overall')">Overall \u21C5</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200" id="rfmCompletionTable">
                            </tbody>
                        </table>
                    </div>
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
    let wtwPmFilter = '';  // 'ready', 'reopen', or ''
    let wtwSortField = 's';
    let wtwSortAsc = true;
    let wtwFilteredData = [];
    
    // Service Channel URL
    const SC_URL = 'https://www.servicechannel.com/sc/wo/Workorders/index?id=';
    
    // Tab switching
    function switchTab(tab) {{
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.classList.remove('border-walmart-blue', 'text-walmart-blue');
            btn.classList.add('border-transparent', 'text-gray-500');
        }});
        document.getElementById('tab-' + tab).classList.remove('border-transparent', 'text-gray-500');
        document.getElementById('tab-' + tab).classList.add('border-walmart-blue', 'text-walmart-blue');
        
        // Hide all tab content
        ['tnt-content', 'wtw-content', 'leak-content'].forEach(id => {{
            const el = document.getElementById(id);
            if (el) el.classList.add('hidden');
        }});
        // Show selected tab
        const activeEl = document.getElementById(tab + '-content');
        if (activeEl) activeEl.classList.remove('hidden');
        
        if (tab === 'wtw') initWtwTab();
        if (tab === 'leak' && typeof initLeakTab === 'function') initLeakTab();
    }}
    
    // Initialize WTW tab
    let wtwInitialized = false;
    function initWtwTab() {{
        console.log('initWtwTab called');
        if (wtwInitialized) return;
        wtwInitialized = true;
        
        try {{
            // Populate filter dropdowns
            console.log('Populating filters...');
            populateWtwFilters();
            // Initialize charts
            console.log('Initializing charts...');
            initWtwCharts();
            // Initial data filter
            console.log('Filtering data...');
            filterWtwData();
            console.log('initWtwTab complete!');
        }} catch (e) {{
            console.error('Error in initWtwTab:', e);
        }}
    }}
    
    // Populate filter dropdowns dynamically (cascading)
    function populateWtwFilters() {{
        updateCascadingFilters();
    }}
    
    function updateCascadingFilters() {{
        const srDir = document.getElementById('wtwFilterSrDirector').value;
        const fmDir = document.getElementById('wtwFilterDirector').value;
        const rm = document.getElementById('wtwFilterManager').value;
        const fsm = document.getElementById('wtwFilterFSManager').value;
        const mkt = document.getElementById('wtwFilterMarket').value;
        
        const getValidOptions = (excludeField) => {{
            return WTW_DATA.filter(wo => {{
                if (excludeField !== 'srd' && srDir && wo.srd !== srDir) return false;
                if (excludeField !== 'fm' && fmDir && wo.fm !== fmDir) return false;
                if (excludeField !== 'rm' && rm && wo.rm !== rm) return false;
                if (excludeField !== 'fsm' && fsm && wo.fsm !== fsm) return false;
                if (excludeField !== 'mkt' && mkt && wo.mkt !== mkt) return false;
                return true;
            }});
        }};
        
        const updateSelect = (id, field, excludeField, currentVal) => {{
            const sel = document.getElementById(id);
            const validData = getValidOptions(excludeField);
            const options = [...new Set(validData.map(wo => wo[field]).filter(Boolean))].sort();
            sel.innerHTML = '<option value="">All</option>';
            options.forEach(v => {{
                const opt = new Option(v, v);
                if (v === currentVal) opt.selected = true;
                sel.add(opt);
            }});
            if (currentVal && !options.includes(currentVal)) sel.value = '';
        }};
        
        updateSelect('wtwFilterSrDirector', 'srd', 'srd', srDir);
        updateSelect('wtwFilterDirector', 'fm', 'fm', fmDir);
        updateSelect('wtwFilterManager', 'rm', 'rm', rm);
        updateSelect('wtwFilterFSManager', 'fsm', 'fsm', fsm);
        updateSelect('wtwFilterMarket', 'mkt', 'mkt', mkt);
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
    
    // Set PM readiness filter
    function setWtwPmFilter(filter) {{
        wtwPmFilter = filter;
        // Update button styles
        document.querySelectorAll('.wtw-pm-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        const activeBtn = document.getElementById('wtw-pm-' + (filter || 'all'));
        if (activeBtn) {{
            activeBtn.classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }}
        filterWtwData();
    }}
    
    // Clear all WTW filters
    function clearWtwFilters() {{
        wtwCurrentPhase = '';
        wtwCurrentStatus = '';
        wtwPmFilter = '';
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
        document.querySelectorAll('.wtw-pm-btn').forEach(btn => {{
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        }});
        document.getElementById('wtw-phase-all').classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        document.getElementById('wtw-status-all').classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
        document.getElementById('wtw-pm-all').classList.add('ring-2', 'ring-offset-2', 'ring-walmart-blue');
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
            if (!wtwCurrentStatus && status) {{
                if (wo.st !== status) return false;
            }}
            if (search) {{
                const searchStr = (wo.s + ' ' + wo.city + ' ' + wo.t + ' ' + wo.fm + ' ' + wo.loc).toLowerCase();
                if (!searchStr.includes(search)) return false;
            }}
            // PM Readiness filter
            if (wtwPmFilter === 'ready') {{
                // Ready to complete: Not Completed + all PM pass
                if (wo.st === 'COMPLETED' || wo.allP !== 'PASS') return false;
            }}
            if (wtwPmFilter === 'review') {{
                // Review needed: Completed + PM >= banner threshold but failing 1+ criteria (exclude Div1)
                const pmScore = parseFloat(wo.pm) || 0;
                const isSams = (wo.banner || '').includes('Sam');
                const threshold = isSams ? 87 : 90;
                if (wo.st !== 'COMPLETED' || wo.allP === 'PASS' || pmScore < threshold || wo.div1 === 'Y') return false;
            }}
            if (wtwPmFilter === 'critical') {{
                // Critical reopen: Completed + PM below banner threshold
                // + failing 2+ of 3 metrics + repair < 8 hrs (exclude Div1)
                const pmScore = parseFloat(wo.pm) || 0;
                const isSams = (wo.banner || '').includes('Sam');
                const threshold = isSams ? 87 : 90;
                const failCount = [wo.rackP, wo.tntP, wo.dewP].filter(x => x === 'FAIL').length;
                const repairHrs = parseFloat(wo.repH) || 0;
                if (wo.st !== 'COMPLETED' || pmScore >= threshold || failCount < 2 || repairHrs >= 8 || wo.div1 === 'Y') return false;
            }}
            if (wtwPmFilter === 'div1') {{
                // Div1 stores only
                if (wo.div1 !== 'Y') return false;
            }}
            return true;
        }});
        
        // Update filtered count
        document.getElementById('wtwFilteredCount').textContent = wtwFilteredData.length.toLocaleString();
        
        // Update cascading filter dropdowns
        updateCascadingFilters();
        
        // Update KPIs based on filtered data
        updateWtwKpis();
        
        // Update phase cards based on filtered data
        updatePhaseCards();
        
        // Update PM readiness buttons based on filtered data
        updatePmButtons();
        
        // Update charts
        updateWtwCharts();
        
        // Render table
        renderWtwTable();
        
        // Update completion tables (only responds to Sr Dir & FM Dir filters)
        updateCompletionTables();
        
        // Update director summary table
        updateDirSummary();
    }}
    
    // Update KPIs
    function updateWtwKpis() {{
        const counts = {{'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}};
        wtwFilteredData.forEach(wo => {{
            if (wo.st === 'COMPLETED') counts['COMPLETED']++;
            else if (wo.st === 'IN PROGRESS') counts['IN PROGRESS']++;
            else counts['OPEN']++;
        }});
        const total = wtwFilteredData.length;
        const completionRate = total > 0 ? ((counts['COMPLETED'] / total) * 100).toFixed(1) : 0;
        document.getElementById('wtwKpiCompleted').textContent = counts['COMPLETED'].toLocaleString();
        document.getElementById('wtwKpiCompletionRate').textContent = completionRate + '% complete';
        document.getElementById('wtwKpiInProgress').textContent = counts['IN PROGRESS'].toLocaleString();
        document.getElementById('wtwKpiOpen').textContent = counts['OPEN'].toLocaleString();
        document.getElementById('wtwKpiTotal').textContent = total.toLocaleString();
        
        // Labor hours KPIs
        let totalHrs = 0, repairHrs = 0, travelHrs = 0, totalVisits = 0, wosWithHrs = 0;
        wtwFilteredData.forEach(wo => {{
            const tot = parseFloat(wo.totH) || 0;
            const rep = parseFloat(wo.repH) || 0;
            const trv = parseFloat(wo.trvH) || 0;
            const vis = parseInt(wo.vis) || 0;
            totalHrs += tot;
            repairHrs += rep;
            travelHrs += trv;
            totalVisits += vis;
            if (tot > 0) wosWithHrs++;
        }});
        const avgHrs = wosWithHrs > 0 ? (totalHrs / wosWithHrs).toFixed(1) : 0;
        const avgVisits = wosWithHrs > 0 ? (totalVisits / wosWithHrs).toFixed(1) : 0;
        document.getElementById('wtwKpiTotalHrs').textContent = Math.round(totalHrs).toLocaleString();
        document.getElementById('wtwKpiAvgHrs').textContent = avgHrs + ' avg/WO';
        document.getElementById('wtwKpiRepairHrs').textContent = Math.round(repairHrs).toLocaleString();
        document.getElementById('wtwKpiTravelHrs').textContent = Math.round(travelHrs).toLocaleString();
        document.getElementById('wtwKpiTotalVisits').textContent = totalVisits.toLocaleString();
        document.getElementById('wtwKpiAvgVisits').textContent = avgVisits + ' avg/WO';
    }}
    
    // Update Phase Cards based on filtered data
    function updatePhaseCards() {{
        // Calculate phase stats from filtered data
        const phaseStats = {{
            'all': {{'total': 0, 'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}},
            'PH1': {{'total': 0, 'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}},
            'PH2': {{'total': 0, 'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}},
            'PH3': {{'total': 0, 'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}}
        }};
        
        wtwFilteredData.forEach(wo => {{
            const ph = wo.ph;
            const st = wo.st;
            phaseStats['all'].total++;
            phaseStats[ph].total++;
            if (st === 'COMPLETED') {{
                phaseStats['all']['COMPLETED']++;
                phaseStats[ph]['COMPLETED']++;
            }} else if (st === 'IN PROGRESS') {{
                phaseStats['all']['IN PROGRESS']++;
                phaseStats[ph]['IN PROGRESS']++;
            }} else {{
                phaseStats['all']['OPEN']++;
                phaseStats[ph]['OPEN']++;
            }}
        }});
        
        // Update each phase card
        ['all', 'PH1', 'PH2', 'PH3'].forEach(phase => {{
            const stats = phaseStats[phase];
            const total = stats.total || 1;  // Avoid division by zero
            const prefix = phase === 'all' ? 'wtw-phase-all' : `wtw-phase-${{phase}}`;
            
            // Update count
            document.getElementById(`${{prefix}}-count`).textContent = stats.total.toLocaleString();
            
            // Update progress bar - multi-colored with Walmart colors
            const completedPct = (stats['COMPLETED'] / total * 100);
            const inProgressPct = (stats['IN PROGRESS'] / total * 100);
            const openPct = (stats['OPEN'] / total * 100);
            const barLabel = (pct) => pct >= 12 ? `<span class="text-xs font-bold text-white drop-shadow">${{pct.toFixed(0)}}%</span>` : '';
            document.getElementById(`${{prefix}}-bar`).innerHTML = `
                <div class="flex items-center justify-center" style="width: ${{completedPct.toFixed(1)}}%; background: #2a8703;" title="Completed: ${{stats['COMPLETED'].toLocaleString()}} (${{completedPct.toFixed(1)}}%)">${{barLabel(completedPct)}}</div>
                <div class="flex items-center justify-center" style="width: ${{inProgressPct.toFixed(1)}}%; background: #ffc220;" title="In Progress: ${{stats['IN PROGRESS'].toLocaleString()}} (${{inProgressPct.toFixed(1)}}%)">${{barLabel(inProgressPct)}}</div>
                <div class="flex items-center justify-center" style="width: ${{openPct.toFixed(1)}}%; background: #9ca3af;" title="Open: ${{stats['OPEN'].toLocaleString()}} (${{openPct.toFixed(1)}}%)">${{barLabel(openPct)}}</div>
            `;
            
            // Update legend with colored dots
            document.getElementById(`${{prefix}}-legend`).innerHTML = `
                <span><span class="inline-block w-2 h-2 rounded-full mr-1" style="background:#2a8703"></span>Done ${{stats['COMPLETED'].toLocaleString()}}</span>
                <span><span class="inline-block w-2 h-2 rounded-full mr-1" style="background:#ffc220"></span>WIP ${{stats['IN PROGRESS'].toLocaleString()}}</span>
                <span><span class="inline-block w-2 h-2 rounded-full mr-1" style="background:#9ca3af"></span>Open ${{stats['OPEN'].toLocaleString()}}</span>
            `;
        }});
    }}
    
    // Update PM Readiness button counts based on filtered data
    function updatePmButtons() {{
        let ready = 0, review = 0, critical = 0, div1 = 0;
        const total = wtwFilteredData.length;
        
        wtwFilteredData.forEach(wo => {{
            const pmScore = parseFloat(wo.pm) || 0;
            const isDiv1 = wo.div1 === 'Y';
            
            if (isDiv1) {{
                div1++;
            }}
            
            if (wo.st !== 'COMPLETED' && wo.allP === 'PASS') {{
                ready++;
            }}
            
            if (wo.st === 'COMPLETED' && wo.allP === 'FAIL' && !isDiv1) {{
                const isSams = (wo.banner || '').includes('Sam');
                const threshold = isSams ? 87 : 90;
                const failCount = [wo.rackP, wo.tntP, wo.dewP].filter(x => x === 'FAIL').length;
                const repairHrs = parseFloat(wo.repH) || 0;
                if (pmScore < threshold && failCount >= 2 && repairHrs < 8) {{
                    critical++;  // PM below banner threshold + 2+ fails + <8 repair hrs
                }} else if (pmScore >= threshold) {{
                    review++;  // PM above threshold but failing 1+ criteria
                }}
            }}
        }});
        
        // Update button counts
        document.getElementById('wtw-pm-all-count').textContent = total.toLocaleString();
        document.getElementById('wtw-pm-ready-count').textContent = ready.toLocaleString();
        document.getElementById('wtw-pm-review-count').textContent = review.toLocaleString();
        document.getElementById('wtw-pm-critical-count').textContent = critical.toLocaleString();
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
    // Build mailto: link for emailing RM/FSM about a store's PM status
    function buildMailto(name, role, wo) {{
        if (!name || name === '-') return '';
        const isSams = (wo.banner || '').includes('Sam');
        const bannerLabel = isSams ? "Sam's Club" : 'Walmart';
        const threshold = isSams ? '87%' : '90%';
        const pmVal = wo.pm ? parseFloat(wo.pm).toFixed(1) + '%' : 'N/A';
        const rackVal = wo.rack ? parseFloat(wo.rack).toFixed(1) + '%' : 'No Data';
        const tntVal = wo.tnt ? parseFloat(wo.tnt).toFixed(1) + '%' : 'No Data';
        const dewVal = wo.dew ? parseFloat(wo.dew).toFixed(0) + '°F' : 'No Data';
        const rackStatus = wo.rackP === 'PASS' ? '✅ Pass' : wo.rackP === 'FAIL' ? '❌ Fail' : '⬜ No Data';
        const tntStatus = wo.tntP === 'PASS' ? '✅ Pass' : wo.tntP === 'FAIL' ? '❌ Fail' : '⬜ No Data';
        const dewStatus = wo.dewP === 'PASS' ? '✅ Pass' : wo.dewP === 'FAIL' ? '❌ Fail' : '⬜ No Data';
        const subject = `WTW FY26 — Store ${{wo.s}} (${{bannerLabel}}) — PM Score Review`;
        const body = [
            `Hey ${{[wo.rm, wo.fsm].filter(n => n && !n.includes('-FS')).map(n => n.split(' ')[0]).filter((v,i,a) => a.indexOf(v)===i).join(' and ')}}!`,
            '',
            `Just checking in on Win-the-Winter FY26 PM readiness for Store ${{wo.s}} (${{wo.loc || wo.city || ''}}).`,
            '',
            `── Store Summary ──────────────────`,
            `Store:        ${{wo.s}} — ${{wo.loc || wo.city || ''}}${{wo.state ? ', ' + wo.state : ''}}`,
            `Banner:       ${{bannerLabel}}`,
            `Phase:        ${{wo.ph}}`,
            `Status:       ${{wo.st}}`,
            `Tracking #:   ${{wo.t}}`,
            `SC Link:      https://login.servicechannel.com/sc/wo/details/${{wo.t}}`,
            '',
            `── PM Scorecard ───────────────────`,
            `PM Score:     ${{pmVal}} (target: ${{threshold}})`,
            `Rack Score:   ${{rackVal}} ${{rackStatus}}`,
            `TnT Score:    ${{tntVal}} ${{tntStatus}}`,
            `Dewpoint:     ${{dewVal}} ${{dewStatus}}`,
            '',
            `── Labor ──────────────────────────`,
            `Total Hours:  ${{wo.totH || '0'}}  (Repair: ${{wo.repH || '0'}}, Travel: ${{wo.trvH || '0'}})`,
            `Visits:       ${{wo.vis || '0'}}`,
            '',
            `Is this PM 100% complete? Are you and the team satisfied with the result, or is there anything else we should address before closing this out?`,
            ''
        ].join('\\n');
        return `mailto:?subject=${{encodeURIComponent(subject)}}&body=${{encodeURIComponent(body)}}`;
    }}
    
    function renderWtwTable() {{
        console.log('renderWtwTable called, data count:', wtwFilteredData.length);
        // Sort data
        const sorted = [...wtwFilteredData].sort((a, b) => {{
            let aVal = a[wtwSortField] || '';
            let bVal = b[wtwSortField] || '';
            if (['s', 'totH', 'vis', 'pm', 'rack', 'tnt'].includes(wtwSortField)) {{
                aVal = parseFloat(aVal) || 0;
                bVal = parseFloat(bVal) || 0;
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
                               wo.st === 'IN PROGRESS' ? 'text-yellow-600 font-semibold' : 'text-gray-600';
            const statusText = wo.st === 'COMPLETED' ? '✓ COMPLETED' : wo.st;
            const div1Badge = wo.div1 === 'Y' ? '<span class="ml-1 px-1 py-0.5 rounded text-xs bg-orange-100 text-orange-700" title="Div1 - Small format store">D1</span>' : '';
            return `
                <tr class="hover:bg-gray-50 ${{wo.div1 === 'Y' ? 'bg-orange-50' : ''}}">
                    <td class="px-3 py-2 text-sm font-medium text-walmart-blue">${{wo.s}}${{div1Badge}}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${{wo.city}}${{wo.city && wo.state ? ', ' : ''}}${{wo.state}}</td>
                    <td class="px-3 py-2 text-center">
                        <span class="px-2 py-1 rounded-full text-xs font-semibold ${{phaseClass}}">${{wo.ph}}</span>
                    </td>
                    <td class="px-3 py-2 text-sm ${{statusClass}}">${{statusText}}</td>
                    <td class="px-3 py-2 text-center">
                        ${{wo.banner && wo.banner.includes('Sam') ? 
                            '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-800 text-white">Sam&#39;s</span>' : 
                            '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-400 text-blue-900">WM</span>'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-gray-600">
                        <div class="flex items-center gap-1">
                            <span>${{wo.rm || '-'}}</span>
                            ${{wo.rm ? `<a href="${{buildMailto(wo.rm, 'RM', wo)}}" class="inline-flex items-center justify-center w-6 h-6 rounded hover:bg-blue-100" title="Email ${{wo.rm}} about Store ${{wo.s}}"><svg width="16" height="16" viewBox="0 0 32 32" fill="none"><rect x="2" y="6" width="28" height="20" rx="2" fill="#0078d4"/><path d="M2 8l14 9 14-9" stroke="#fff" stroke-width="2" fill="none"/><rect x="18" y="15" width="12" height="11" rx="1" fill="#0053e2"/></svg></a>` : ''}}
                        </div>
                    </td>
                    <td class="px-3 py-2 text-sm text-gray-600">
                        <div class="flex items-center gap-1">
                            <span>${{wo.fsm || '-'}}</span>
                            ${{wo.fsm && !wo.fsm.includes('-FS') ? `<a href="${{buildMailto(wo.fsm, 'FSM', wo)}}" class="inline-flex items-center justify-center w-6 h-6 rounded hover:bg-blue-100" title="Email ${{wo.fsm}} about Store ${{wo.s}}"><svg width="16" height="16" viewBox="0 0 32 32" fill="none"><rect x="2" y="6" width="28" height="20" rx="2" fill="#0078d4"/><path d="M2 8l14 9 14-9" stroke="#fff" stroke-width="2" fill="none"/><rect x="18" y="15" width="12" height="11" rx="1" fill="#0053e2"/></svg></a>` : ''}}
                        </div>
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.pm ? `
                            <div class="flex items-center justify-center gap-1">
                                <span class="px-2 py-1 rounded text-xs font-bold ${{parseFloat(wo.pm) >= 87 ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}}">
                                    ${{parseFloat(wo.pm).toFixed(1)}}%
                                </span>
                                <span class="text-sm ${{parseFloat(wo.pm) >= 87 ? 'text-green-600' : 'text-red-600'}}">
                                    ${{parseFloat(wo.pm) >= 87 ? '✓' : '✗'}}
                                </span>
                            </div>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.rackP === 'NO DATA' ? `
                            <span class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">No Data</span>
                        ` : wo.rack ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.rackP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{parseFloat(wo.rack).toFixed(1)}}% ${{wo.rackP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.tntP === 'NO DATA' ? `
                            <span class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">No Data</span>
                        ` : wo.tnt ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.tntP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{parseFloat(wo.tnt).toFixed(1)}}% ${{wo.tntP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.dewP === 'NO DATA' ? `
                            <span class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">No Data</span>
                        ` : wo.dew ? `
                            <span class="px-2 py-0.5 rounded text-xs ${{wo.dewP === 'PASS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}">
                                ${{parseFloat(wo.dew).toFixed(0)}}°F ${{wo.dewP === 'PASS' ? '✓' : '✗'}}
                            </span>
                        ` : '-'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.totH ? `
                            <div class="text-xs">
                                <span class="font-bold text-gray-800">${{parseFloat(wo.totH).toFixed(1)}}</span>
                                <span class="text-gray-400">hrs</span>
                            </div>
                            <div class="text-xs text-gray-400">
                                R:${{parseFloat(wo.repH || 0).toFixed(0)}} T:${{parseFloat(wo.trvH || 0).toFixed(0)}}
                            </div>
                        ` : '<span class="text-gray-300">—</span>'}}
                    </td>
                    <td class="px-3 py-2 text-sm text-center">
                        ${{wo.vis ? `
                            <span class="font-semibold text-gray-700">${{wo.vis}}</span>
                            <span class="text-xs text-gray-400">${{wo.techs ? '/ ' + wo.techs + ' tech' + (parseInt(wo.techs) > 1 ? 's' : '') : ''}}</span>
                        ` : '<span class="text-gray-300">—</span>'}}
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
            table.innerHTML += `<tr><td colspan="15" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} results. Use filters to narrow down.</td></tr>`;
        }}
    }}
    
    // Completion table sort state
    let fsmSortField = 'overall';
    let fsmSortDesc = true;
    let rfmSortField = 'overall';
    let rfmSortDesc = true;
    let fsmRowsData = [];
    let rfmRowsData = [];
    
    function sortFsmTable(field) {{
        if (fsmSortField === field) {{
            fsmSortDesc = !fsmSortDesc;
        }} else {{
            fsmSortField = field;
            fsmSortDesc = true;
        }}
        renderFsmTable();
    }}
    
    function sortRfmTable(field) {{
        if (rfmSortField === field) {{
            rfmSortDesc = !rfmSortDesc;
        }} else {{
            rfmSortField = field;
            rfmSortDesc = true;
        }}
        renderRfmTable();
    }}
    
    // Completion Tables by FSM and RFM (only responds to Sr Dir & FM Dir filters)
    function updateCompletionTables() {{
        const srDir = document.getElementById('wtwFilterSrDirector').value;
        const fmDir = document.getElementById('wtwFilterDirector').value;
        
        // Filter data by Sr Dir and FM Dir only
        const filteredData = WTW_DATA.filter(wo => {{
            if (srDir && wo.srd !== srDir) return false;
            if (fmDir && wo.fm !== fmDir) return false;
            return true;
        }});
        
        // Calculate completion % by FSM
        const fsmStats = {{}};
        filteredData.forEach(wo => {{
            const fsm = wo.fsm || 'Unknown';
            if (!fsmStats[fsm]) {{
                fsmStats[fsm] = {{
                    PH1: {{ total: 0, completed: 0 }},
                    PH2: {{ total: 0, completed: 0 }},
                    PH3: {{ total: 0, completed: 0 }}
                }};
            }}
            if (wo.ph && fsmStats[fsm][wo.ph]) {{
                fsmStats[fsm][wo.ph].total++;
                if (wo.st === 'COMPLETED') fsmStats[fsm][wo.ph].completed++;
            }}
        }});
        
        // Calculate completion % by RFM
        const rfmStats = {{}};
        filteredData.forEach(wo => {{
            const rfm = wo.rm || 'Unknown';
            if (!rfmStats[rfm]) {{
                rfmStats[rfm] = {{
                    PH1: {{ total: 0, completed: 0 }},
                    PH2: {{ total: 0, completed: 0 }},
                    PH3: {{ total: 0, completed: 0 }}
                }};
            }}
            if (wo.ph && rfmStats[rfm][wo.ph]) {{
                rfmStats[rfm][wo.ph].total++;
                if (wo.st === 'COMPLETED') rfmStats[rfm][wo.ph].completed++;
            }}
        }});
        
        // Helper to calculate % and color
        const getPct = (completed, total) => total > 0 ? ((completed / total) * 100).toFixed(1) : '0.0';
        const getColor = (pct) => {{
            if (pct >= 80) return 'text-green-600 font-bold';
            if (pct >= 50) return 'text-yellow-600';
            return 'text-red-600';
        }};
        
        // Build FSM rows data
        fsmRowsData = Object.entries(fsmStats)
            .map(([fsm, phases]) => {{
                const ph1Pct = getPct(phases.PH1.completed, phases.PH1.total);
                const ph2Pct = getPct(phases.PH2.completed, phases.PH2.total);
                const ph3Pct = getPct(phases.PH3.completed, phases.PH3.total);
                const totalCompleted = phases.PH1.completed + phases.PH2.completed + phases.PH3.completed;
                const totalAll = phases.PH1.total + phases.PH2.total + phases.PH3.total;
                const overallPct = getPct(totalCompleted, totalAll);
                return {{
                    name: fsm,
                    ph1Pct: parseFloat(ph1Pct),
                    ph1Completed: phases.PH1.completed,
                    ph1Total: phases.PH1.total,
                    ph2Pct: parseFloat(ph2Pct),
                    ph2Completed: phases.PH2.completed,
                    ph2Total: phases.PH2.total,
                    ph3Pct: parseFloat(ph3Pct),
                    ph3Completed: phases.PH3.completed,
                    ph3Total: phases.PH3.total,
                    overallPct: parseFloat(overallPct),
                    totalCompleted: totalCompleted,
                    total: totalAll
                }};
            }})
            .filter(r => r.total > 0);
        
        renderFsmTable();
        
        // Build RFM rows data
        rfmRowsData = Object.entries(rfmStats)
            .map(([rfm, phases]) => {{
                const ph1Pct = getPct(phases.PH1.completed, phases.PH1.total);
                const ph2Pct = getPct(phases.PH2.completed, phases.PH2.total);
                const ph3Pct = getPct(phases.PH3.completed, phases.PH3.total);
                const totalCompleted = phases.PH1.completed + phases.PH2.completed + phases.PH3.completed;
                const totalAll = phases.PH1.total + phases.PH2.total + phases.PH3.total;
                const overallPct = getPct(totalCompleted, totalAll);
                return {{
                    name: rfm,
                    ph1Pct: parseFloat(ph1Pct),
                    ph1Completed: phases.PH1.completed,
                    ph1Total: phases.PH1.total,
                    ph2Pct: parseFloat(ph2Pct),
                    ph2Completed: phases.PH2.completed,
                    ph2Total: phases.PH2.total,
                    ph3Pct: parseFloat(ph3Pct),
                    ph3Completed: phases.PH3.completed,
                    ph3Total: phases.PH3.total,
                    overallPct: parseFloat(overallPct),
                    totalCompleted: totalCompleted,
                    total: totalAll
                }};
            }})
            .filter(r => r.total > 0);
        
        renderRfmTable();
    }}
    
    // Helper for color
    function getCompletionColor(pct) {{
        if (pct >= 80) return 'text-green-600 font-bold';
        if (pct >= 50) return 'text-yellow-600';
        return 'text-red-600';
    }}
    
    // Render FSM table with current sort
    function renderFsmTable() {{
        const sorted = [...fsmRowsData].sort((a, b) => {{
            let aVal, bVal;
            if (fsmSortField === 'name') {{
                aVal = a.name || '';
                bVal = b.name || '';
                return fsmSortDesc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            }} else if (fsmSortField === 'ph1') {{
                aVal = a.ph1Pct; bVal = b.ph1Pct;
            }} else if (fsmSortField === 'ph2') {{
                aVal = a.ph2Pct; bVal = b.ph2Pct;
            }} else if (fsmSortField === 'ph3') {{
                aVal = a.ph3Pct; bVal = b.ph3Pct;
            }} else {{
                aVal = a.overallPct; bVal = b.overallPct;
            }}
            return fsmSortDesc ? bVal - aVal : aVal - bVal;
        }});
        
        const table = document.getElementById('fsmCompletionTable');
        table.innerHTML = sorted.map(r => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 text-sm font-medium text-gray-800">${{r.name}}</td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph1Pct)}}">${{r.ph1Pct}}% <span class="text-gray-400 text-xs">(${{r.ph1Completed}}/${{r.ph1Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph2Pct)}}">${{r.ph2Pct}}% <span class="text-gray-400 text-xs">(${{r.ph2Completed}}/${{r.ph2Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph3Pct)}}">${{r.ph3Pct}}% <span class="text-gray-400 text-xs">(${{r.ph3Completed}}/${{r.ph3Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.overallPct)}}">${{r.overallPct}}% <span class="text-gray-400 text-xs">(${{r.totalCompleted}}/${{r.total}})</span></td>
            </tr>
        `).join('');
    }}
    
    // Render RFM table with current sort
    function renderRfmTable() {{
        const sorted = [...rfmRowsData].sort((a, b) => {{
            let aVal, bVal;
            if (rfmSortField === 'name') {{
                aVal = a.name || '';
                bVal = b.name || '';
                return rfmSortDesc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            }} else if (rfmSortField === 'ph1') {{
                aVal = a.ph1Pct; bVal = b.ph1Pct;
            }} else if (rfmSortField === 'ph2') {{
                aVal = a.ph2Pct; bVal = b.ph2Pct;
            }} else if (rfmSortField === 'ph3') {{
                aVal = a.ph3Pct; bVal = b.ph3Pct;
            }} else {{
                aVal = a.overallPct; bVal = b.overallPct;
            }}
            return rfmSortDesc ? bVal - aVal : aVal - bVal;
        }});
        
        const table = document.getElementById('rfmCompletionTable');
        table.innerHTML = sorted.map(r => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 text-sm font-medium text-gray-800">${{r.name}}</td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph1Pct)}}">${{r.ph1Pct}}% <span class="text-gray-400 text-xs">(${{r.ph1Completed}}/${{r.ph1Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph2Pct)}}">${{r.ph2Pct}}% <span class="text-gray-400 text-xs">(${{r.ph2Completed}}/${{r.ph2Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.ph3Pct)}}">${{r.ph3Pct}}% <span class="text-gray-400 text-xs">(${{r.ph3Completed}}/${{r.ph3Total}})</span></td>
                <td class="px-3 py-2 text-sm text-center ${{getCompletionColor(r.overallPct)}}">${{r.overallPct}}% <span class="text-gray-400 text-xs">(${{r.totalCompleted}}/${{r.total}})</span></td>
            </tr>
        `).join('');
    }}
    
    // Director Summary
    let dirSummarySortField = 'pct';
    let dirSummarySortAsc = false;
    
    // Build store -> realty region map from EMBEDDED_STORE_DATA
    const storeRegionMap = {{}};
    if (typeof EMBEDDED_STORE_DATA !== 'undefined') {{
        EMBEDDED_STORE_DATA.forEach(s => {{
            if (s.store_number && s.realty_ops_region) {{
                storeRegionMap[String(s.store_number)] = String(s.realty_ops_region);
            }}
        }});
    }}
    
    function sortDirSummary(field) {{
        if (dirSummarySortField === field) {{
            dirSummarySortAsc = !dirSummarySortAsc;
        }} else {{
            dirSummarySortField = field;
            dirSummarySortAsc = field === 'name' || field === 'region';
        }}
        renderDirSummary();
    }}
    
    function updateDirSummary() {{
        renderDirSummary();
    }}
    
    function renderDirSummary() {{
        const dirMap = {{}};
        wtwFilteredData.forEach(wo => {{
            const dir = wo.fm || 'Unknown';
            if (!dirMap[dir]) {{
                // Get unique realty regions for this director
                dirMap[dir] = {{ name: dir, total: 0, completed: 0, ip: 0, stores: new Set(),
                    regions: new Set(), hours: 0, ready: 0,
                    ph1: 0, ph1Done: 0, ph2: 0, ph2Done: 0, ph3: 0, ph3Done: 0 }};
            }}
            const d = dirMap[dir];
            d.total++;
            d.stores.add(wo.s);
            const region = storeRegionMap[wo.s] || '—';
            d.regions.add(region);
            if (wo.st === 'COMPLETED') d.completed++;
            else if (wo.st === 'IN PROGRESS') {{
                d.ip++;
                if (wo.allP === 'PASS') d.ready++;
            }}
            const hrs = parseFloat(wo.totH) || 0;
            d.hours += hrs;
            if (wo.ph === 'PH1') {{ d.ph1++; if (wo.st === 'COMPLETED') d.ph1Done++; }}
            if (wo.ph === 'PH2') {{ d.ph2++; if (wo.st === 'COMPLETED') d.ph2Done++; }}
            if (wo.ph === 'PH3') {{ d.ph3++; if (wo.st === 'COMPLETED') d.ph3Done++; }}
        }});
        
        let rows = Object.values(dirMap).map(d => ({{
            ...d,
            pct: d.total > 0 ? (d.completed / d.total * 100) : 0,
            ph1Pct: d.ph1 > 0 ? (d.ph1Done / d.ph1 * 100) : 0,
            ph2Pct: d.ph2 > 0 ? (d.ph2Done / d.ph2 * 100) : 0,
            ph3Pct: d.ph3 > 0 ? (d.ph3Done / d.ph3 * 100) : 0,
            storeCount: d.stores.size,
            regionStr: [...d.regions].filter(r => r !== '—').sort().join(', ') || '—'
        }}));
        
        const sortKey = dirSummarySortField;
        rows.sort((a, b) => {{
            let av, bv;
            if (sortKey === 'name') {{ av = a.name; bv = b.name; }}
            else if (sortKey === 'region') {{ av = a.regionStr; bv = b.regionStr; }}
            else if (sortKey === 'stores') {{ av = a.storeCount; bv = b.storeCount; }}
            else if (sortKey === 'total') {{ av = a.total; bv = b.total; }}
            else if (sortKey === 'completed') {{ av = a.completed; bv = b.completed; }}
            else if (sortKey === 'ip') {{ av = a.ip; bv = b.ip; }}
            else if (sortKey === 'pct') {{ av = a.pct; bv = b.pct; }}
            else if (sortKey === 'ph1') {{ av = a.ph1Pct; bv = b.ph1Pct; }}
            else if (sortKey === 'ph2') {{ av = a.ph2Pct; bv = b.ph2Pct; }}
            else if (sortKey === 'ph3') {{ av = a.ph3Pct; bv = b.ph3Pct; }}
            else if (sortKey === 'hours') {{ av = a.hours; bv = b.hours; }}
            else if (sortKey === 'ready') {{ av = a.ready; bv = b.ready; }}
            else {{ av = a.pct; bv = b.pct; }}
            if (typeof av === 'string') return dirSummarySortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
            return dirSummarySortAsc ? av - bv : bv - av;
        }});
        
        const pctBadge = (pct) => {{
            const cls = pct >= 40 ? 'bg-green-100 text-green-700' : pct >= 20 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
            return `<span class="px-2 py-0.5 rounded text-xs font-semibold ${{cls}}">${{pct.toFixed(1)}}%</span>`;
        }};
        
        const table = document.getElementById('wtwDirSummaryTable');
        table.innerHTML = rows.map(r => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 text-sm font-semibold text-gray-900">${{r.name}}</td>
                <td class="px-3 py-2 text-sm text-center"><span class="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 text-xs font-semibold">${{r.regionStr}}</span></td>
                <td class="px-3 py-2 text-sm text-center text-gray-600">${{r.storeCount}}</td>
                <td class="px-3 py-2 text-sm text-center font-semibold">${{r.total}}</td>
                <td class="px-3 py-2 text-sm text-center text-green-600 font-semibold">${{r.completed}}</td>
                <td class="px-3 py-2 text-sm text-center text-yellow-600">${{r.ip}}</td>
                <td class="px-3 py-2 text-sm text-center">${{pctBadge(r.pct)}}</td>
                <td class="px-3 py-2 text-sm text-center">${{pctBadge(r.ph1Pct)}}</td>
                <td class="px-3 py-2 text-sm text-center">${{pctBadge(r.ph2Pct)}}</td>
                <td class="px-3 py-2 text-sm text-center">${{pctBadge(r.ph3Pct)}}</td>
                <td class="px-3 py-2 text-sm text-center text-indigo-600">${{r.hours.toLocaleString(undefined, {{maximumFractionDigits: 0}})}}</td>
                <td class="px-3 py-2 text-sm text-center"><span class="px-2 py-0.5 rounded bg-teal-50 text-teal-700 text-xs font-semibold">${{r.ready}}</span></td>
            </tr>
        `).join('');
        
        // Add total row
        if (rows.length > 1) {{
            const totals = rows.reduce((acc, r) => ({{
                total: acc.total + r.total, completed: acc.completed + r.completed, ip: acc.ip + r.ip,
                hours: acc.hours + r.hours, ready: acc.ready + r.ready, stores: acc.stores + r.storeCount,
                ph1: acc.ph1 + r.ph1, ph1Done: acc.ph1Done + r.ph1Done,
                ph2: acc.ph2 + r.ph2, ph2Done: acc.ph2Done + r.ph2Done,
                ph3: acc.ph3 + r.ph3, ph3Done: acc.ph3Done + r.ph3Done
            }}), {{ total: 0, completed: 0, ip: 0, hours: 0, ready: 0, stores: 0, ph1: 0, ph1Done: 0, ph2: 0, ph2Done: 0, ph3: 0, ph3Done: 0 }});
            const tPct = totals.total > 0 ? (totals.completed / totals.total * 100) : 0;
            const p1Pct = totals.ph1 > 0 ? (totals.ph1Done / totals.ph1 * 100) : 0;
            const p2Pct = totals.ph2 > 0 ? (totals.ph2Done / totals.ph2 * 100) : 0;
            const p3Pct = totals.ph3 > 0 ? (totals.ph3Done / totals.ph3 * 100) : 0;
            table.innerHTML += `
                <tr class="bg-blue-50 font-bold border-t-2 border-blue-300">
                    <td class="px-3 py-2 text-sm text-blue-800">Total</td>
                    <td class="px-3 py-2 text-sm text-center"></td>
                    <td class="px-3 py-2 text-sm text-center">${{totals.stores}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{totals.total}}</td>
                    <td class="px-3 py-2 text-sm text-center text-green-600">${{totals.completed}}</td>
                    <td class="px-3 py-2 text-sm text-center text-yellow-600">${{totals.ip}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{pctBadge(tPct)}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{pctBadge(p1Pct)}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{pctBadge(p2Pct)}}</td>
                    <td class="px-3 py-2 text-sm text-center">${{pctBadge(p3Pct)}}</td>
                    <td class="px-3 py-2 text-sm text-center text-indigo-600">${{totals.hours.toLocaleString(undefined, {{maximumFractionDigits: 0}})}}</td>
                    <td class="px-3 py-2 text-sm text-center"><span class="px-2 py-0.5 rounded bg-teal-50 text-teal-700 text-xs font-semibold">${{totals.ready}}</span></td>
                </tr>
            `;
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
                labels: ['Completed', 'In Progress', 'Open'],
                datasets: [{{
                    data: [0, 0, 0],
                    backgroundColor: ['#2a8703', '#ffc220', '#6b7280'],
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
        
        // Phase chart - stacked bar showing Completed / In Progress / Open
        const phaseCtx = document.getElementById('wtwPhaseChart').getContext('2d');
        wtwPhaseChart = new Chart(phaseCtx, {{
            type: 'bar',
            data: {{
                labels: ['Phase 1', 'Phase 2', 'Phase 3'],
                datasets: [
                    {{ label: 'Completed', data: [0, 0, 0], backgroundColor: '#2a8703' }},
                    {{ label: 'In Progress', data: [0, 0, 0], backgroundColor: '#ffc220' }},
                    {{ label: 'Open', data: [0, 0, 0], backgroundColor: '#9ca3af' }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'top', labels: {{ boxWidth: 12, padding: 15 }} }},
                    datalabels: {{
                        color: '#fff',
                        anchor: 'center',
                        font: {{ weight: 'bold', size: 12 }},
                        formatter: (value) => value > 0 ? value.toLocaleString() : ''
                    }}
                }},
                scales: {{
                    x: {{ stacked: true }},
                    y: {{ stacked: true, beginAtZero: true }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
        
        updateWtwCharts();
    }}
    
    function updateWtwCharts() {{
        if (!wtwStatusChart || !wtwPhaseChart) return;
        
        // Count main statuses in filtered data
        const statusCounts = {{'COMPLETED': 0, 'IN PROGRESS': 0, 'OPEN': 0}};
        const phaseCounts = {{'PH1': 0, 'PH2': 0, 'PH3': 0}};
        
        wtwFilteredData.forEach(wo => {{
            if (wo.st === 'COMPLETED') statusCounts['COMPLETED']++;
            else if (wo.st === 'IN PROGRESS') statusCounts['IN PROGRESS']++;
            else statusCounts['OPEN']++;
            phaseCounts[wo.ph] = (phaseCounts[wo.ph] || 0) + 1;
        }});
        
        // Update KPI cards
        const total = wtwFilteredData.length;
        document.getElementById('wtwKpiCompleted').textContent = statusCounts['COMPLETED'].toLocaleString();
        document.getElementById('wtwKpiCompletionRate').textContent = total > 0 ? ((statusCounts['COMPLETED'] / total) * 100).toFixed(1) + '% complete' : '0% complete';
        document.getElementById('wtwKpiInProgress').textContent = statusCounts['IN PROGRESS'].toLocaleString();
        document.getElementById('wtwKpiOpen').textContent = statusCounts['OPEN'].toLocaleString();
        document.getElementById('wtwKpiTotal').textContent = total.toLocaleString();
        
        wtwStatusChart.data.datasets[0].data = [
            statusCounts['COMPLETED'],
            statusCounts['IN PROGRESS'],
            statusCounts['OPEN']
        ];
        wtwStatusChart.update();
        
        // Count phase statuses for stacked bars
        const phaseStatus = {{
            'PH1': {{c: 0, ip: 0, o: 0}},
            'PH2': {{c: 0, ip: 0, o: 0}},
            'PH3': {{c: 0, ip: 0, o: 0}}
        }};
        wtwFilteredData.forEach(wo => {{
            const ps = phaseStatus[wo.ph];
            if (ps) {{
                if (wo.st === 'COMPLETED') ps.c++;
                else if (wo.st === 'IN PROGRESS') ps.ip++;
                else ps.o++;
            }}
        }});
        wtwPhaseChart.data.datasets[0].data = [phaseStatus.PH1.c, phaseStatus.PH2.c, phaseStatus.PH3.c];
        wtwPhaseChart.data.datasets[1].data = [phaseStatus.PH1.ip, phaseStatus.PH2.ip, phaseStatus.PH3.ip];
        wtwPhaseChart.data.datasets[2].data = [phaseStatus.PH1.o, phaseStatus.PH2.o, phaseStatus.PH3.o];
        wtwPhaseChart.update();
    }}
    </script>
    '''
    
    # Insert WTW content before Footer
    html = re.sub(
        r'(\s*<!-- Footer -->)',
        '\n' + wtw_content + '\n\n    <!-- Footer -->',
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
