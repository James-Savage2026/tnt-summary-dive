"""JS builder for Leak Management tab — v5 with burn rate."""

THRESHOLD = 9
B = '#0053e2'
S = '#ffc220'
R = '#ea1100'
G = '#2a8703'


def build_leak_js(store_json, mgmt_json, cumul_json, burn_json, wo_json='{}'):
    T = THRESHOLD
    return f'''
    <script>
    // Leak Management Data
    const LK_STORES = {store_json};
    const LK_MGMT = {mgmt_json};
    const LK_CUMUL = {cumul_json};
    const LK_BURN = {burn_json};
    const LK_WOS = {wo_json};
    const LK_T = {T};
    let lkExpandedStore = null;

    let lkFiltered = [];
    let lkSortField = 'cylr';
    let lkSortAsc = false;
    let lkInit = false;
    let lkMgmtChart = null;

    // --- Burn rate helpers ---
    function calcBurn(cytq, sc) {{
        const now = new Date();
        const jan1 = new Date(now.getFullYear(), 0, 1);
        const elapsed = Math.max(1, Math.floor((now - jan1) / 86400000));
        const diy = now.getFullYear() % 4 === 0 ? 366 : 365;
        const daily = cytq / elapsed;
        const projTq = daily * diy;
        const projRate = sc > 0 ? (projTq / sc * 100) : 0;
        const threshLbs = sc * LK_T / 100;
        let crossDay = -1;
        if (daily > 0 && cytq < threshLbs) crossDay = elapsed + (threshLbs - cytq) / daily;
        return {{ elapsed, diy, daily, projTq, projRate, crossDay }};
    }}

    function dayToDate(dayNum) {{
        const d = new Date(new Date().getFullYear(), 0, 1);
        d.setDate(d.getDate() + dayNum - 1);
        return d.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
    }}

    function initLeakTab() {{
        if (lkInit) return;
        lkInit = true;
        initLeakYoyChart();
        filterLeakData();
    }}

    function initLeakYoyChart() {{
        const colors = {{ 2024: '{S}', 2025: '{B}', 2026: '{G}' }};
        const datasets = LK_CUMUL.years.map(y => ({{
            label: '' + y,
            data: LK_CUMUL.data[y],
            borderColor: colors[y] || '#999',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            pointRadius: 4,
            pointBackgroundColor: colors[y] || '#999',
            borderWidth: y === 2026 ? 3 : 2,
        }}));
        datasets.push({{
            label: LK_T + '% Threshold',
            data: Array(12).fill(LK_T),
            borderColor: '{R}',
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
        const mgmtMap = {{}};
        lkFiltered.forEach(s => {{
            const key = s.fm || 'Unknown';
            if (!mgmtMap[key]) mgmtMap[key] = {{ fm: key, charge: 0, cytq: 0 }};
            mgmtMap[key].charge += s.sc;
            mgmtMap[key].cytq += s.cytq;
        }});
        const mgmtArr = Object.values(mgmtMap).map(m => {{
            const cylr = m.charge > 0 ? (m.cytq / m.charge * 100) : 0;
            const burn = calcBurn(m.cytq, m.charge);
            return {{ ...m, cylr, burnRate: burn.projRate }};
        }});
        mgmtArr.sort((a, b) => b.burnRate - a.burnRate);

        if (lkMgmtChart) lkMgmtChart.destroy();
        lkMgmtChart = new Chart(document.getElementById('leakMgmtChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: mgmtArr.map(m => m.fm),
                datasets: [{{
                    label: '\U0001f525 Burn Rate (EOY Proj) %',
                    data: mgmtArr.map(m => m.burnRate),
                    backgroundColor: mgmtArr.map(m => m.burnRate > LK_T ? '{R}cc' : '{G}cc'),
                    borderRadius: 3
                }}, {{
                    label: 'CY2026 Actual %',
                    data: mgmtArr.map(m => m.cylr),
                    backgroundColor: '{B}88',
                    borderRadius: 3
                }}, {{
                    label: LK_T + '% Threshold',
                    data: Array(mgmtArr.length).fill(LK_T),
                    type: 'line', borderColor: '{R}', borderDash: [6, 3],
                    borderWidth: 2, pointRadius: 0, fill: false
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }},
                    datalabels: {{
                        anchor: 'end', align: 'end', color: '#333',
                        font: {{ size: 9, weight: 'bold' }},
                        formatter: (v, ctx) => ctx.datasetIndex < 2 ? v.toFixed(1) + '%' : ''
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
        const burnOver = document.getElementById('leakBurnOver').checked;

        lkFiltered = LK_STORES.filter(s => {{
            if (srd && s.srd !== srd) return false;
            if (fm && s.fm !== fm) return false;
            if (rm && s.rm !== rm) return false;
            if (fsm && s.fsm !== fsm) return false;
            if (ban && s.ban !== ban) return false;
            if (over && s.cylr <= LK_T) return false;
            if (burnOver) {{
                const b = calcBurn(s.cytq, s.sc);
                if (b.projRate <= LK_T) return false;
            }}
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
        let sc = 0, cytq = 0, cyl = 0;
        lkFiltered.forEach(s => {{ sc += s.sc; cytq += s.cytq; cyl += s.cyl; }});
        const rate = sc > 0 ? (cytq / sc * 100) : 0;
        const burn = calcBurn(cytq, sc);
        const thresh = Math.round(sc * LK_T / 100);
        const remain = Math.max(0, thresh - cytq);
        const pct = thresh > 0 ? Math.min(100, cytq / thresh * 100) : 0;

        // KPI cards
        const rEl = document.getElementById('lkKpiRate');
        rEl.textContent = rate.toFixed(2) + '%';
        rEl.className = 'text-xl font-bold ' + (rate > LK_T ? 'text-[{R}]' : 'text-[{G}]');

        const brEl = document.getElementById('lkKpiBurnRate');
        brEl.textContent = burn.projRate.toFixed(1) + '%';
        brEl.className = 'text-xl font-bold ' + (burn.projRate > LK_T ? 'text-[{R}]' : 'text-[{G}]');

        document.getElementById('lkKpiThreshold').textContent = thresh.toLocaleString();
        document.getElementById('lkKpiRecords').textContent = cyl.toLocaleString();
        document.getElementById('lkKpiAdded').textContent = Math.round(cytq).toLocaleString();
        document.getElementById('lkKpiCharge').textContent = Math.round(sc).toLocaleString();

        // Threshold bar
        const bar = document.getElementById('lkThresholdBar');
        bar.style.width = pct.toFixed(0) + '%';
        bar.style.background = cytq > thresh ? '{R}' : '{G}';
        document.getElementById('lkBarLabel').textContent = lkFiltered.length < LK_STORES.length ? 'Filtered' : 'All Stores';
        document.getElementById('lkBarValue').textContent = Math.round(cytq).toLocaleString() + ' lbs';
        document.getElementById('lkThreshLbs').textContent = thresh.toLocaleString() + ' lbs';
        const addEl = document.getElementById('lkAddedLbs');
        addEl.textContent = Math.round(cytq).toLocaleString() + ' lbs';
        addEl.className = 'text-sm font-bold ' + (cytq > thresh ? 'text-[{R}]' : 'text-[{G}]');
        const remEl = document.getElementById('lkRemainLbs');
        remEl.textContent = Math.round(remain).toLocaleString() + ' lbs';
        remEl.className = 'text-sm font-bold ' + (remain <= 0 ? 'text-[{R}]' : 'text-[{G}]');

        // Burn rate projection card
        document.getElementById('lkBurnDaily').textContent = Math.round(burn.daily).toLocaleString() + ' lbs/day';
        const eoyEl = document.getElementById('lkBurnEoyRate');
        eoyEl.textContent = burn.projRate.toFixed(1) + '%';
        eoyEl.className = 'text-lg font-bold ' + (burn.projRate > LK_T ? 'text-[{R}]' : 'text-[{G}]');
        document.getElementById('lkBurnEoyLbs').textContent = Math.round(burn.projTq).toLocaleString();

        const crossEl = document.getElementById('lkBurnCrossDate');
        if (burn.crossDay > 0 && burn.crossDay <= burn.diy) {{
            crossEl.textContent = dayToDate(Math.round(burn.crossDay));
            crossEl.className = 'text-lg font-bold text-[{R}]';
        }} else if (burn.projRate <= LK_T) {{
            crossEl.textContent = 'Safe \u2705';
            crossEl.className = 'text-lg font-bold text-[{G}]';
        }} else {{
            crossEl.textContent = 'Already Over';
            crossEl.className = 'text-lg font-bold text-[{R}]';
        }}

        // Verdict
        const vEl = document.getElementById('lkBurnVerdict');
        if (burn.projRate <= LK_T) {{
            vEl.innerHTML = '\u2705 <strong>On pace to finish under ' + LK_T + '%.</strong> Projected EOY: ' + burn.projRate.toFixed(1) + '%';
            vEl.className = 'mt-3 p-2 rounded text-xs text-center bg-green-50 text-[{G}] border border-green-200';
        }} else if (burn.projRate <= LK_T * 1.5) {{
            vEl.innerHTML = '\u26A0\uFE0F <strong>Warning:</strong> At current pace, will hit ' + burn.projRate.toFixed(1) + '% by EOY. Crosses ' + LK_T + '% around <strong>' + (burn.crossDay > 0 ? dayToDate(Math.round(burn.crossDay)) : 'N/A') + '</strong>.';
            vEl.className = 'mt-3 p-2 rounded text-xs text-center bg-amber-50 text-amber-800 border border-amber-200';
        }} else {{
            vEl.innerHTML = '\U0001f6a8 <strong>Critical:</strong> Projected ' + burn.projRate.toFixed(1) + '% by EOY (' + (burn.projRate / LK_T).toFixed(1) + 'x threshold). Crosses ' + LK_T + '% around <strong>' + (burn.crossDay > 0 ? dayToDate(Math.round(burn.crossDay)) : 'N/A') + '</strong>.';
            vEl.className = 'mt-3 p-2 rounded text-xs text-center bg-red-50 text-[{R}] border border-red-200';
        }}
    }}

    function clearLeakFilters() {{
        ['leakFilterSrDir','leakFilterFmDir','leakFilterRm','leakFilterFsm','leakFilterBanner'].forEach(id => document.getElementById(id).value = '');
        document.getElementById('leakSearch').value = '';
        document.getElementById('leakOverOnly').checked = false;
        document.getElementById('leakBurnOver').checked = false;
        filterLeakData();
    }}

    function sortLeakTable(f) {{
        if (lkSortField === f) lkSortAsc = !lkSortAsc;
        else {{ lkSortField = f; lkSortAsc = false; }}
        renderLeakTable();
    }}

    function toggleLeakWo(storeNbr) {{
        lkExpandedStore = lkExpandedStore === storeNbr ? null : storeNbr;
        renderLeakTable();
    }}

    function buildWoRows(storeNbr) {{
        const wos = LK_WOS[storeNbr];
        if (!wos || wos.length === 0) {{
            return `<tr class="bg-gray-50"><td colspan="10" class="px-6 py-3 text-sm text-gray-400 italic">No CY2026 leak work orders found for store ${{storeNbr}}</td></tr>`;
        }}
        let html = `<tr class="bg-blue-50"><td colspan="10" class="px-0 py-0">
            <div class="px-6 py-3">
                <div class="flex items-center gap-2 mb-2">
                    <span class="text-xs font-bold text-[{B}]">\U0001f4cb CY2026 Leak Events — Store ${{storeNbr}}</span>
                    <span class="text-xs text-gray-500">(${{wos.length}} event${{wos.length > 1 ? 's' : ''}})</span>
                </div>
                <table class="w-full text-xs">
                    <thead><tr class="text-left text-gray-500 border-b border-blue-200">
                        <th class="px-2 py-1">Tracking #</th>
                        <th class="px-2 py-1">Leak Date</th>
                        <th class="px-2 py-1">Tag ID</th>
                        <th class="px-2 py-1 text-right">Trigger Qty (lbs)</th>
                        <th class="px-2 py-1">Repair Date</th>
                        <th class="px-2 py-1">Status</th>
                    </tr></thead>
                    <tbody>`;
        wos.forEach(w => {{
            const repaired = w.rep && w.rep !== 'null' && w.rep !== '';
            const statusBadge = repaired
                ? '<span class="px-1.5 py-0.5 rounded bg-[{G}] text-white text-xs">Repaired</span>'
                : '<span class="px-1.5 py-0.5 rounded bg-amber-500 text-white text-xs">Open</span>';
            html += `<tr class="border-b border-blue-100 hover:bg-blue-100">
                <td class="px-2 py-1.5">
                    <a href="https://www.servicechannel.com/sc/wo/Workorders/index?id=${{w.tr}}" target="_blank"
                       class="text-[{B}] font-semibold hover:underline">#${{w.tr}}</a>
                </td>
                <td class="px-2 py-1.5 text-gray-700">${{w.dt || '-'}}</td>
                <td class="px-2 py-1.5 text-gray-500 font-mono">${{w.tag || '-'}}</td>
                <td class="px-2 py-1.5 text-right font-semibold ${{parseFloat(w.qty) > 100 ? 'text-[{R}]' : 'text-gray-700'}}">${{parseFloat(w.qty || 0).toLocaleString()}}</td>
                <td class="px-2 py-1.5 text-gray-700">${{repaired ? w.rep : '-'}}</td>
                <td class="px-2 py-1.5">${{statusBadge}}</td>
            </tr>`;
        }});
        html += '</tbody></table></div></td></tr>';
        return html;
    }}

    function renderLeakTable() {{
        const sorted = [...lkFiltered].map(s => {{
            const b = calcBurn(s.cytq, s.sc);
            return {{ ...s, burn: b.projRate }};
        }}).sort((a, b) => {{
            let av = a[lkSortField], bv = b[lkSortField];
            if (typeof av === 'string') {{ av = av || ''; bv = bv || ''; }}
            return lkSortAsc ? (av < bv ? -1 : av > bv ? 1 : 0) : (av > bv ? -1 : av < bv ? 1 : 0);
        }});
        const disp = sorted.slice(0, 300);
        const t = document.getElementById('leakStoreTable');
        const hasWos = Object.keys(LK_WOS).length > 0;
        t.innerHTML = disp.map(s => {{
            const ban = s.ban && s.ban.includes('Sam')
                ? '<span class="px-1.5 py-0.5 rounded text-xs font-semibold bg-[{B}] text-white">SAMS</span>'
                : '<span class="px-1.5 py-0.5 rounded text-xs font-semibold bg-[{S}] text-[{B}]">WMT</span>';
            const rClass = s.cylr > LK_T ? 'bg-[{R}] text-white' : s.cylr > LK_T * 0.7 ? 'bg-amber-500 text-white' : 'bg-[{G}] text-white';
            const bRate = s.burn;
            const bClass = bRate > LK_T ? 'text-[{R}] font-bold' : 'text-[{G}]';
            const icon = bRate > LK_T * 1.5 ? '\U0001f6a8' : bRate > LK_T ? '\u26A0\uFE0F' : '\u2705';
            const woCount = (LK_WOS[s.s] || []).length;
            const isExpanded = lkExpandedStore === s.s;
            const expandIcon = woCount > 0 ? (isExpanded ? '\u25BC' : '\u25B6') : '';
            const clickAttr = woCount > 0 ? `onclick="toggleLeakWo('${{s.s}}')" style="cursor:pointer"` : '';
            let row = `
                <tr class="hover:bg-gray-50 ${{s.cylr > LK_T ? 'bg-red-50' : ''}} ${{isExpanded ? 'bg-blue-50' : ''}}" ${{clickAttr}}>
                    <td class="px-3 py-1.5 text-sm font-medium text-gray-800">
                        <span class="text-xs text-gray-400 mr-1">${{expandIcon}}</span>${{s.s}}
                    </td>
                    <td class="px-3 py-1.5 text-sm text-gray-600">${{s.city}}${{s.city && s.st ? ', ' : ''}}${{s.st}}</td>
                    <td class="px-3 py-1.5 text-center">${{ban}}</td>
                    <td class="px-3 py-1.5 text-xs text-gray-600">${{s.mkt || '-'}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.sc).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-sm text-center">${{Math.round(s.cytq).toLocaleString()}}</td>
                    <td class="px-3 py-1.5 text-center">
                        <span class="px-2 py-0.5 rounded text-xs font-bold ${{rClass}}">${{s.cylr.toFixed(1)}}%</span>
                    </td>
                    <td class="px-3 py-1.5 text-center text-sm ${{bClass}}">${{bRate.toFixed(1)}}%</td>
                    <td class="px-3 py-1.5 text-sm text-center">
                        ${{s.cyl}}
                        ${{woCount > 0 ? `<span class="ml-1 px-1 py-0.5 rounded bg-[{B}] text-white text-xs">${{woCount}} WO${{woCount > 1 ? 's' : ''}}</span>` : ''}}
                    </td>
                    <td class="px-3 py-1.5 text-center text-sm">${{icon}}</td>
                </tr>
            `;
            if (isExpanded) row += buildWoRows(s.s);
            return row;
        }}).join('');
        if (sorted.length > 300) {{
            t.innerHTML += `<tr><td colspan="10" class="px-3 py-3 text-center text-gray-400 text-sm bg-gray-50">Showing 300 of ${{sorted.length.toLocaleString()}} stores.</td></tr>`;
        }}
    }}
    </script>
    '''
