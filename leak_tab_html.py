"""HTML builder for Leak Management tab — v5."""

THRESHOLD = 9
B = '#0053e2'   # Walmart blue.100
S = '#ffc220'   # spark.100
R = '#ea1100'   # red.100
G = '#2a8703'   # green.100


def build_leak_html(fleet_charge, cy_tq, cy_rate, cy_leaks, threshold_lbs, burn):
    T = THRESHOLD
    rate_cls = f'text-[{R}]' if cy_rate > T else f'text-[{G}]'
    bar_pct = min(100, (cy_tq / threshold_lbs * 100)) if threshold_lbs else 0
    bar_color = R if cy_tq > threshold_lbs else G
    remain = max(0, threshold_lbs - cy_tq)
    remain_cls = f'text-[{R}]' if remain <= 0 else f'text-[{G}]'
    added_cls = f'text-[{R}]' if cy_tq > threshold_lbs else f'text-[{G}]'

    proj_rate = burn['projected_eoy_rate']
    proj_cls = f'text-[{R}]' if proj_rate > T else f'text-[{G}]'
    daily_burn = burn['daily_burn_lbs']
    proj_eoy_tq = burn['projected_eoy_tq']
    cross_day = burn['cross_day']
    days_elapsed = burn['days_elapsed']
    days_in_year = burn['days_in_year']

    # Burn rate gauge angle (0-180 degrees for a half-circle gauge)
    gauge_pct = min(100, proj_rate / (T * 2) * 100)  # scale: 0% to 2x threshold

    return f'''
    <!-- Leak Tab Content -->
    <div id="leak-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">

            <!-- Header -->
            <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-10 h-10 bg-[{B}] rounded-lg flex items-center justify-center">
                        <span class="text-white text-lg">\U0001f9ca</span>
                    </div>
                    <div>
                        <h1 class="text-xl font-bold text-gray-800">Refrigerant Leak Report — CY2026</h1>
                        <p class="text-xs text-gray-400">Calendar Year &bull; Cumulative Rates &bull; Day {days_elapsed} of {days_in_year}</p>
                    </div>
                </div>

                <!-- KPI Bar -->
                <div class="grid grid-cols-2 md:grid-cols-6 gap-0">
                    <div class="text-center">
                        <div class="bg-[{B}] text-white px-2 py-2 text-xs font-semibold rounded-t">CY2026 Leak Rate</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold {rate_cls}" id="lkKpiRate">{cy_rate:.2f}%</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[{R}] text-white px-2 py-2 text-xs font-semibold rounded-t">\U0001f525 Burn Rate (EOY Proj)</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold {proj_cls}" id="lkKpiBurnRate">{proj_rate:.1f}%</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[{B}] text-white px-2 py-2 text-xs font-semibold rounded-t">{T}% Threshold (lbs)</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiThreshold">{threshold_lbs:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[{B}] text-white px-2 py-2 text-xs font-semibold rounded-t">CY2026 Added (lbs)</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiAdded">{cy_tq:,.0f}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[{B}] text-white px-2 py-2 text-xs font-semibold rounded-t">Leak Events</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiRecords">{cy_leaks:,}</p>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="bg-[{B}] text-white px-2 py-2 text-xs font-semibold rounded-t">Fleet Charge</div>
                        <div class="border border-gray-200 px-2 py-3 rounded-b">
                            <p class="text-xl font-bold text-gray-800" id="lkKpiCharge">{fleet_charge:,.0f}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Row 2: Threshold Bar + Burn Rate Projection -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <!-- Threshold Progress -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[{B}] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">{T}% Leak Rate Threshold</div>
                    <div class="flex items-center gap-3">
                        <span class="text-sm text-gray-500 whitespace-nowrap" id="lkBarLabel">All Stores</span>
                        <div class="flex-1 relative">
                            <div class="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                                <div id="lkThresholdBar" class="h-8 rounded-full transition-all duration-500"
                                     style="width: {bar_pct:.0f}%; background: {bar_color};"></div>
                            </div>
                            <div class="absolute top-0 right-0 h-8 flex items-center pr-1">
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
                            <p class="text-sm font-bold {added_cls}" id="lkAddedLbs">{cy_tq:,.0f} lbs</p>
                        </div>
                        <div class="bg-gray-50 rounded p-2">
                            <p class="text-xs text-gray-500">Remaining</p>
                            <p class="text-sm font-bold {remain_cls}" id="lkRemainLbs">{remain:,.0f} lbs</p>
                        </div>
                    </div>
                </div>

                <!-- Burn Rate Projection Card -->
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-gradient-to-r from-[{R}] to-[{S}] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">\U0001f525 Burn Rate Projection</div>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-gray-500 uppercase">Daily Burn</p>
                            <p class="text-lg font-bold text-gray-800" id="lkBurnDaily">{daily_burn:,.0f} lbs/day</p>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-gray-500 uppercase">Projected EOY</p>
                            <p class="text-lg font-bold {proj_cls}" id="lkBurnEoyRate">{proj_rate:.1f}%</p>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-gray-500 uppercase">Projected EOY lbs</p>
                            <p class="text-lg font-bold text-gray-800" id="lkBurnEoyLbs">{proj_eoy_tq:,}</p>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-gray-500 uppercase">{T}% Crossing</p>
                            <p class="text-lg font-bold" id="lkBurnCrossDate"></p>
                        </div>
                    </div>
                    <div class="mt-3 p-2 rounded text-xs text-center" id="lkBurnVerdict"></div>
                </div>
            </div>

            <!-- Row 3: Cumulative YoY Chart + FM Director Chart -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[{B}] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">Monthly Cumulative Leak Rate vs {T}%</div>
                    <div style="height: 280px;"><canvas id="leakYoyChart"></canvas></div>
                </div>
                <div class="bg-white rounded-lg shadow p-4">
                    <div class="bg-[{B}] text-white px-3 py-2 text-sm font-semibold rounded-t text-center mb-3">FM Director CY2026 Leak Rate vs {T}%</div>
                    <div style="height: 280px;"><canvas id="leakMgmtChart"></canvas></div>
                </div>
            </div>

            <!-- Filters -->
            <div class="bg-white rounded-lg shadow p-4 mb-4">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-sm font-medium text-gray-700">\U0001f50d Store Filters</h3>
                    <button onclick="clearLeakFilters()" class="px-3 py-1 bg-[{B}] hover:bg-[#003da5] text-white text-sm rounded-md transition">Clear All</button>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
                    <div>
                        <label class="text-xs text-gray-500">Sr. Director</label>
                        <select id="leakFilterSrDir" onchange="filterLeakData()" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-[{B}] focus:border-[{B}]"><option value="">All</option></select>
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
                    <p class="text-sm text-gray-500">Showing <span id="leakFilteredCount" class="font-bold text-[{B}]">0</span> stores</p>
                    <label class="flex items-center gap-1 text-sm text-gray-500 cursor-pointer">
                        <input type="checkbox" id="leakOverOnly" onchange="filterLeakData()" class="rounded text-[{B}]">
                        Over {T}% only
                    </label>
                    <label class="flex items-center gap-1 text-sm text-gray-500 cursor-pointer">
                        <input type="checkbox" id="leakBurnOver" onchange="filterLeakData()" class="rounded text-[{R}]">
                        \U0001f525 Burn rate over {T}%
                    </label>
                </div>
            </div>

            <!-- Store Table -->
            <div class="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div class="bg-[{B}] text-white px-3 py-2 text-sm font-semibold text-center">Store Detail</div>
                <div class="overflow-x-auto" style="max-height: 600px; overflow-y: auto;">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('s')">Store ⇅</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Type</th>
                                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Market</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('sc')">Charge ⇅</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cytq')">Added CY26 ⇅</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cylr')">CY26 Rate ⇅</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('burn')"><span class="text-[{R}]">\U0001f525</span> Burn ⇅</th>
                                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100" onclick="sortLeakTable('cyl')">Events ⇅</th>
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