"""JS builder for store detail panel — HVAC, Refrigeration, WTW cross-ref."""

B = '#0053e2'
S = '#ffc220'
R = '#ea1100'
G = '#2a8703'


def build_store_detail_js():
    """Return the JS functions for the store detail panel.

    These functions rely on global vars from the leak tab:
    - STORE_ASSETS, LK_WOS, WTW_DATA
    - lkDetailFilter, lkExpandedStore
    """
    return f'''
    function toggleLeakWo(storeNbr) {{
        lkExpandedStore = lkExpandedStore === storeNbr ? null : storeNbr;
        lkDetailFilter = 'all';
        renderLeakTable();
    }}

    function setDetailFilter(filter) {{
        lkDetailFilter = filter;
        renderLeakTable();
    }}

    function buildStoreDetail(storeNbr) {{
        const assets = STORE_ASSETS[storeNbr] || {{}};
        const wos = LK_WOS[storeNbr] || [];
        const ref = assets.r || null;
        const hv = assets.h || null;
        const showRefrig = lkDetailFilter === 'all' || lkDetailFilter === 'refrig';
        const showHvac = lkDetailFilter === 'all' || lkDetailFilter === 'hvac';

        // WTW PM cross-reference
        let wtwHtml = '';
        if (typeof WTW_DATA !== 'undefined') {{
            const wtwWos = WTW_DATA.filter(w => w.s === storeNbr);
            if (wtwWos.length > 0) {{
                const completed = wtwWos.filter(w => w.st === 'COMPLETED');
                const latest = wtwWos[0];
                const pmScore = latest.pm !== null && latest.pm !== undefined ? parseFloat(latest.pm) : null;
                const pmClass = pmScore === null ? 'bg-gray-200 text-gray-600' : pmScore >= 90 ? 'bg-[{G}] text-white' : pmScore >= 70 ? 'bg-amber-500 text-white' : 'bg-[{R}] text-white';
                const pmText = pmScore !== null ? pmScore.toFixed(0) + '%' : 'N/A';
                const statusBadge = completed.length === wtwWos.length
                    ? '<span class="px-2 py-0.5 rounded text-xs font-bold bg-[{G}] text-white">\u2713 PM Completed</span>'
                    : completed.length > 0
                    ? `<span class="px-2 py-0.5 rounded text-xs font-bold bg-amber-500 text-white">${{completed.length}}/${{wtwWos.length}} Completed</span>`
                    : '<span class="px-2 py-0.5 rounded text-xs font-bold bg-[{R}] text-white">\u2717 PM Not Completed</span>';
                wtwHtml = `
                    <div class="flex items-center gap-3 mb-3 p-2 bg-gray-50 rounded-lg border border-gray-200">
                        <span class="text-xs font-bold text-gray-600">\u2744\uFE0F WTW FY26:</span>
                        ${{statusBadge}}
                        <span class="px-2 py-0.5 rounded text-xs font-bold ${{pmClass}}">PM Score: ${{pmText}}</span>
                        <span class="text-xs text-gray-400">${{wtwWos.length}} WO(s)</span>
                    </div>`;
            }} else {{
                wtwHtml = `<div class="flex items-center gap-2 mb-3 p-2 bg-gray-50 rounded-lg border border-gray-200">
                    <span class="text-xs text-gray-400">\u2744\uFE0F WTW FY26: No WTW work orders for this store</span>
                </div>`;
            }}
        }}

        // Filter toggle buttons
        const filterHtml = `
            <div class="flex items-center gap-1 mb-3">
                <button onclick="setDetailFilter('all'); event.stopPropagation();" class="px-3 py-1 rounded text-xs font-semibold ${{lkDetailFilter === 'all' ? 'bg-[{B}] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}}">All</button>
                <button onclick="setDetailFilter('refrig'); event.stopPropagation();" class="px-3 py-1 rounded text-xs font-semibold ${{lkDetailFilter === 'refrig' ? 'bg-[{B}] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}}">
                    \u2744\uFE0F Refrigeration
                </button>
                <button onclick="setDetailFilter('hvac'); event.stopPropagation();" class="px-3 py-1 rounded text-xs font-semibold ${{lkDetailFilter === 'hvac' ? 'bg-[{B}] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}}">
                    \U0001f321\uFE0F HVAC
                </button>
            </div>`;

        const refrigHtml = showRefrig ? buildRefrigSection(ref) : '';
        const leakHtml = showRefrig ? buildLeakEventsTable(wos) : '';
        const hvacHtml = showHvac ? buildHvacSection(hv) : '';

        const noData = !ref && !hv && wos.length === 0
            ? '<div class="text-sm text-gray-400 italic py-2">No asset data available for this store</div>'
            : '';

        return `<tr class="bg-blue-50"><td colspan="10" class="px-0 py-0">
            <div class="px-6 py-3" onclick="event.stopPropagation()">
                ${{wtwHtml}}
                ${{filterHtml}}
                ${{refrigHtml}}
                ${{leakHtml}}
                ${{hvacHtml}}
                ${{noData}}
            </div>
        </td></tr>`;
    }}

    function buildRefrigSection(ref) {{
        if (!ref) return '';
        const rScore = ref.rs !== null && ref.rs !== undefined ? ref.rs.toFixed(1) + '%' : 'N/A';
        const rScoreClass = ref.rs >= 90 ? 'bg-[{G}] text-white' : ref.rs >= 70 ? 'bg-amber-500 text-white' : ref.rs !== null ? 'bg-[{R}] text-white' : 'bg-gray-200 text-gray-600';
        let html = `
            <div class="mb-3">
                <div class="text-xs font-bold text-[{B}] mb-2">\u2744\uFE0F Refrigeration Assets</div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold text-gray-800">${{ref.rc || 0}}</div>
                        <div class="text-xs text-gray-500">Racks</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold"><span class="px-2 py-0.5 rounded ${{rScoreClass}}">${{rScore}}</span></div>
                        <div class="text-xs text-gray-500">Rack Scorecard</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold ${{ref.cl > 0 ? 'text-[{R}]' : 'text-[{G}]'}}">${{ref.cl || 0}}</div>
                        <div class="text-xs text-gray-500">\U0001f6a8 Comp. Lockouts</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold ${{(ref.la + ref.fa) > 0 ? 'text-amber-600' : 'text-[{G}]'}}">${{(ref.la || 0) + (ref.fa || 0)}}</div>
                        <div class="text-xs text-gray-500">Active Alarms</div>
                    </div>
                </div>`;
        if (ref.tp || ref.tf) {{
            const total = (ref.tp || 0) + (ref.tf || 0);
            const passPct = total > 0 ? ((ref.tp / total) * 100).toFixed(0) : 0;
            html += `
                <div class="flex items-center gap-2 mb-2">
                    <span class="text-xs text-gray-500">Scorecard Tests:</span>
                    <span class="text-xs font-semibold text-[{G}]">${{ref.tp || 0}} passed</span>
                    <span class="text-xs text-gray-300">|</span>
                    <span class="text-xs font-semibold text-[{R}]">${{ref.tf || 0}} failed</span>
                    <div class="flex-1 bg-gray-200 rounded-full h-1.5 max-w-[120px]">
                        <div class="bg-[{G}] h-1.5 rounded-full" style="width: ${{passPct}}%"></div>
                    </div>
                </div>`;
        }}
        if (ref.cc) {{
            const caseClass = ref.ctp > 20 ? 'text-[{R}]' : ref.ctp > 5 ? 'text-amber-600' : 'text-[{G}]';
            html += `
                <div class="flex items-center gap-3 text-xs mt-1">
                    <span class="font-semibold text-gray-600">Cases:</span>
                    <span>${{ref.cc}} total</span>
                    <span class="text-blue-600">${{ref.mt || 0}} MT</span>
                    <span class="text-purple-600">${{ref.lt || 0}} LT</span>
                    <span class="${{caseClass}} font-bold">${{ref.ctp !== null ? ref.ctp.toFixed(1) + '% terminal' : ''}}</span>
                    ${{ref.cow > 0 ? `<span class="text-amber-600">${{ref.cow}} open WOs</span>` : ''}}
                </div>`;
        }}
        html += '</div>';
        return html;
    }}

    function buildLeakEventsTable(wos) {{
        if (!wos || wos.length === 0) return '';
        let html = `
            <div class="mb-3">
                <div class="text-xs font-bold text-[{B}] mb-1">\U0001f4cb CY2026 Leak Events (${{wos.length}})</div>
                <table class="w-full text-xs">
                    <thead><tr class="text-left text-gray-500 border-b border-blue-200">
                        <th class="px-2 py-1">Tracking #</th>
                        <th class="px-2 py-1">Leak Date</th>
                        <th class="px-2 py-1 text-right">Qty (lbs)</th>
                        <th class="px-2 py-1">Repair Date</th>
                        <th class="px-2 py-1">Status</th>
                    </tr></thead><tbody>`;
        wos.forEach(w => {{
            const repaired = w.rep && w.rep !== 'null' && w.rep !== '';
            const sBadge = repaired
                ? '<span class="px-1.5 py-0.5 rounded bg-[{G}] text-white">Repaired</span>'
                : '<span class="px-1.5 py-0.5 rounded bg-amber-500 text-white">Open</span>';
            html += `<tr class="border-b border-blue-100 hover:bg-blue-100">
                <td class="px-2 py-1"><a href="https://www.servicechannel.com/sc/wo/Workorders/index?id=${{w.tr}}" target="_blank" class="text-[{B}] font-semibold hover:underline" onclick="event.stopPropagation()">#${{w.tr}}</a></td>
                <td class="px-2 py-1 text-gray-700">${{w.dt || '-'}}</td>
                <td class="px-2 py-1 text-right font-semibold ${{parseFloat(w.qty) > 100 ? 'text-[{R}]' : ''}}">${{parseFloat(w.qty || 0).toLocaleString()}}</td>
                <td class="px-2 py-1 text-gray-700">${{repaired ? w.rep : '-'}}</td>
                <td class="px-2 py-1">${{sBadge}}</td>
            </tr>`;
        }});
        html += '</tbody></table></div>';
        return html;
    }}

    function buildHvacSection(hv) {{
        if (!hv) return '';
        const tntClass = hv.tnt >= 90 ? 'bg-[{G}] text-white' : hv.tnt >= 70 ? 'bg-amber-500 text-white' : hv.tnt !== null ? 'bg-[{R}] text-white' : 'bg-gray-200 text-gray-600';
        const dpClass = hv.dp !== null && hv.dp <= 52 ? 'bg-[{G}] text-white' : hv.dp !== null ? 'bg-[{R}] text-white' : 'bg-gray-200 text-gray-600';
        let html = `
            <div class="mb-3">
                <div class="text-xs font-bold text-[{B}] mb-2">\U0001f321\uFE0F HVAC Assets</div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold text-gray-800">${{hv.u || 0}}</div>
                        <div class="text-xs text-gray-500">Total Units (${{hv.rt || 0}} RTU, ${{hv.ah || 0}} AHU)</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold"><span class="px-2 py-0.5 rounded ${{tntClass}}">${{hv.tnt !== null ? hv.tnt + '%' : 'N/A'}}</span></div>
                        <div class="text-xs text-gray-500">HVAC TnT</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold"><span class="px-2 py-0.5 rounded ${{dpClass}}">${{hv.dp !== null ? hv.dp + '\u00B0F' : 'N/A'}}</span></div>
                        <div class="text-xs text-gray-500">Avg Dewpoint</div>
                    </div>
                    <div class="bg-white border rounded p-2 text-center">
                        <div class="text-lg font-bold ${{hv.al > 0 ? 'text-[{R}]' : 'text-[{G}]'}}">${{hv.al || 0}}</div>
                        <div class="text-xs text-gray-500">Alerts (${{hv.hdp || 0}} high DP, ${{hv.cdp || 0}} crit)</div>
                    </div>
                </div>`;
        if (hv.terms && hv.terms.length > 0) {{
            html += `<div class="text-xs text-gray-500 mb-1">Terminal Unit Breakdown:</div>
                <div class="flex flex-wrap gap-2 mb-1">`;
            hv.terms.forEach(t => {{
                const failPct = t.n > 0 ? ((t.f / t.n) * 100).toFixed(0) : 0;
                const fClass = failPct > 20 ? 'border-[{R}]' : failPct > 5 ? 'border-amber-400' : 'border-[{G}]';
                const issues = [];
                if (t.term > 0) issues.push(`${{t.term}} terminal`);
                if (t.se > 0) issues.push(`${{t.se}} sensor err`);
                if (t.sl > 0) issues.push(`${{t.sl}} sensor loss`);
                if (t.cl > 0) issues.push(`${{t.cl}} comm loss`);
                html += `
                    <div class="bg-white border-l-4 ${{fClass}} rounded px-2 py-1 text-xs">
                        <div class="font-semibold capitalize">${{t.t}} <span class="text-gray-400">(${{t.n}})</span></div>
                        ${{issues.length > 0
                            ? '<div class="text-[{R}]">' + issues.join(', ') + '</div>'
                            : '<div class="text-[{G}]">\u2713 No issues</div>'}}
                    </div>`;
            }});
            html += '</div>';
        }}
        if (hv.wo > 0) {{
            html += `<div class="text-xs text-gray-500 mt-1">${{hv.wo}} work orders in last 30 days</div>`;
        }}
        html += '</div>';
        return html;
    }}
'''
