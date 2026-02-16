/**
 * PDF Export Module — TnT/WTW/Leak Dashboard
 * Executive-level PDF reports with insights and action items.
 */

/* ── state ── */
let pdfExportTab = 'tnt';

/* ── helpers ── */
function getPeopleForLevel(level) {
    if (level === 'sr_director')
        return [...new Set(storeData.map(d => d.fm_sr_director_name).filter(Boolean))].sort();
    return [...new Set(storeData.map(d => d.fm_director_name).filter(Boolean))].sort();
}

function getStoresForPerson(level, person) {
    if (level === 'sr_director')
        return storeData.filter(d => d.fm_sr_director_name === person);
    return storeData.filter(d => d.fm_director_name === person);
}

/* ── modal ── */
function openPdfModal(tab) {
    pdfExportTab = tab;
    document.getElementById('pdfExportModal').classList.remove('hidden');
    document.getElementById('pdfTabLabel').textContent =
        tab === 'tnt' ? 'TnT Dashboard' : tab === 'wtw' ? 'Win the Winter' : 'Leak Management';
    document.getElementById('pdfViewLevel').value = 'sr_director';
    updatePdfPersonList();
}

function closePdfModal() {
    document.getElementById('pdfExportModal').classList.add('hidden');
}

function updatePdfPersonList() {
    var level = document.getElementById('pdfViewLevel').value;
    var sel = document.getElementById('pdfPersonSelect');
    var people = getPeopleForLevel(level);
    sel.innerHTML = '<option value="__all__">All (Full Report)</option>' +
        people.map(function(p) { return '<option value="' + p + '">' + p + '</option>'; }).join('');
}

/* ── shared style helpers ── */
function th() { return 'padding:6px 8px; text-align:left; font-size:11px; font-weight:600;'; }
function td() { return 'padding:5px 8px; border-bottom:1px solid #e5e7eb;'; }
function pct(v) { return v != null ? parseFloat(v).toFixed(1) + '%' : 'N/A'; }

function scoreColor(v) {
    if (v == null) return 'color:#999;';
    if (v >= 90) return 'color:#2a8703; font-weight:700;';
    if (v >= 80) return 'color:#f59e0b; font-weight:600;';
    return 'color:#ea1100; font-weight:700;';
}

function kpiBox(label, value, suffix, color) {
    var c = color || (parseFloat(value) >= 90 ? '#2a8703' : parseFloat(value) >= 80 ? '#f59e0b' : '#ea1100');
    var dv = typeof value === 'number' ? value.toFixed(1) : value;
    return '<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;text-align:center;background:#fafafa;">'
        + '<div style="font-size:20px;font-weight:800;color:' + c + ';">' + dv + (suffix || '') + '</div>'
        + '<div style="font-size:10px;color:#666;margin-top:4px;">' + label + '</div></div>';
}

function safeAvg(data, field) {
    var valid = data.filter(function(d) { return d[field] != null && !isNaN(d[field]); });
    return valid.length ? valid.reduce(function(s, d) { return s + parseFloat(d[field]); }, 0) / valid.length : 0;
}

function insightBox(items) {
    var html = '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px;margin:16px 0;">';
    html += '<div style="font-size:13px;font-weight:700;color:#0053e2;margin-bottom:8px;">💡 Key Insights & Action Items</div>';
    html += '<ul style="margin:0;padding-left:20px;font-size:11px;color:#1e3a5f;line-height:1.7;">';
    items.forEach(function(item) { html += '<li>' + item + '</li>'; });
    html += '</ul></div>';
    return html;
}

function sectionTitle(icon, text) {
    return '<h3 style="font-size:14px;font-weight:700;margin:20px 0 8px;color:#0053e2;border-bottom:1px solid #e5e7eb;padding-bottom:4px;">' + icon + ' ' + text + '</h3>';
}

/* ── group stores by field ── */
function groupStores(stores, groupBy) {
    var map = {};
    stores.forEach(function(s) {
        var key = s[groupBy] || 'Unknown';
        if (!map[key]) map[key] = [];
        map[key].push(s);
    });
    return Object.entries(map)
        .map(function(entry) {
            var name = entry[0], ss = entry[1];
            return {
                name: name, count: ss.length,
                avgRef30: safeAvg(ss, 'twt_ref_30_day'),
                avgHvac30: safeAvg(ss, 'twt_hvac_30_day'),
                totalLoss: ss.reduce(function(s, d) { return s + (d.total_loss || 0); }, 0),
                casesOOT: ss.reduce(function(s, d) { return s + (d.cases_out_of_target || 0); }, 0)
            };
        })
        .sort(function(a, b) { return a.avgRef30 - b.avgRef30; });
}

function buildGroupTable(groups, label) {
    var html = sectionTitle('📊', 'Performance by ' + label);
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#0053e2;color:#fff;">';
    html += '<th style="' + th() + '">' + label + '</th><th style="' + th() + '">Stores</th>';
    html += '<th style="' + th() + '">Ref 30d</th><th style="' + th() + '">HVAC 30d</th>';
    html += '<th style="' + th() + '">Total Loss</th><th style="' + th() + '">Cases OOT</th>';
    html += '</tr></thead><tbody>';
    groups.forEach(function(g, i) {
        var bg = i % 2 === 0 ? '#f9fafb' : '#fff';
        html += '<tr style="background:' + bg + ';">';
        html += '<td style="' + td() + 'font-weight:600;">' + g.name + '</td>';
        html += '<td style="' + td() + '">' + g.count + '</td>';
        html += '<td style="' + td() + scoreColor(g.avgRef30) + '">' + g.avgRef30.toFixed(1) + '%</td>';
        html += '<td style="' + td() + scoreColor(g.avgHvac30) + '">' + g.avgHvac30.toFixed(1) + '%</td>';
        html += '<td style="' + td() + 'color:#ea1100;">$' + g.totalLoss.toLocaleString(undefined,{maximumFractionDigits:0}) + '</td>';
        html += '<td style="' + td() + '">' + g.casesOOT.toLocaleString() + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table>';
    return html;
}

/* ═══════════════════════════════════════════════════════════
 *  BUILD PDF CONTENT
 * ═══════════════════════════════════════════════════════════ */
function buildPdfContent(tab, level, person) {
    var isAll = person === '__all__';
    var stores = isAll ? storeData : getStoresForPerson(level, person);
    var levelLabel = level === 'sr_director' ? 'Sr. Director' : 'FM Director';
    var personLabel = isAll ? 'All Regions' : person;
    var dateStr = new Date().toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' });

    var container = document.createElement('div');
    container.style.cssText = 'width:1100px;padding:32px;font-family:system-ui,sans-serif;background:#fff;color:#1a1a1a;';

    var tabName = tab === 'tnt' ? '📊 Time in Target Report' : tab === 'wtw' ? '❄️ Win the Winter Report' : '🧊 Leak Management Report';

    // Header
    container.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:3px solid #0053e2;">'
        + '<div><h1 style="font-size:22px;font-weight:800;color:#0053e2;margin:0;">' + tabName + '</h1>'
        + '<p style="font-size:13px;color:#666;margin:4px 0 0;">' + levelLabel + ' Report: ' + personLabel + '</p></div>'
        + '<div style="text-align:right;"><p style="font-size:12px;color:#666;margin:0;">Generated ' + dateStr + '</p>'
        + '<p style="font-size:12px;color:#666;margin:2px 0 0;">' + stores.length + ' stores</p></div></div>';

    if (tab === 'tnt')  container.innerHTML += buildTntPdf(stores, level, person, isAll);
    if (tab === 'wtw')  container.innerHTML += buildWtwPdf(stores, level, person, isAll);
    if (tab === 'leak') container.innerHTML += buildLeakPdf(stores, level, person, isAll);

    // Footer
    container.innerHTML += '<div style="margin-top:24px;padding-top:12px;border-top:2px solid #0053e2;font-size:10px;color:#999;display:flex;justify-content:space-between;">'
        + '<span>Generated by HVAC/R TnT Dashboard • ' + dateStr + '</span>'
        + '<span>' + levelLabel + ': ' + personLabel + ' • ' + stores.length + ' stores</span></div>';

    return container;
}

/* ═══════════════════════════════════════════════════════════
 *  TnT PDF — Executive Summary
 * ═══════════════════════════════════════════════════════════ */
function buildTntPdf(stores, level, person, isAll) {
    var avg30d = safeAvg(stores, 'twt_ref_30_day');
    var avg7d = safeAvg(stores, 'twt_ref_7_day');
    var avg90d = safeAvg(stores, 'twt_ref_90_day');
    var avgHvac = safeAvg(stores, 'twt_hvac_30_day');
    var totalLoss = stores.reduce(function(s, d) { return s + (d.total_loss || 0); }, 0);
    var casesOOT = stores.reduce(function(s, d) { return s + (d.cases_out_of_target || 0); }, 0);
    var below80 = stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day < 80; }).length;
    var below90 = stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day < 90; }).length;
    var above90 = stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day >= 90; }).length;
    var trendDir = avg7d > avg30d ? '📈 Trending Up' : avg7d < avg30d - 1 ? '📉 Trending Down' : '➡️ Stable';

    var html = '';

    // KPI Grid
    html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px;">';
    html += kpiBox('Ref 7-Day', avg7d, '%');
    html += kpiBox('Ref 30-Day', avg30d, '%');
    html += kpiBox('Ref 90-Day', avg90d, '%');
    html += kpiBox('HVAC 30-Day', avgHvac, '%');
    html += kpiBox('7d Trend', trendDir, '', avg7d >= avg30d ? '#2a8703' : '#ea1100');
    html += '</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">';
    html += kpiBox('Total Stores', stores.length, '', '#333');
    html += kpiBox('Total Loss', '$' + (totalLoss/1000000).toFixed(1) + 'M', '', '#ea1100');
    html += kpiBox('Cases OOT', casesOOT.toLocaleString(), '', '#ea1100');
    html += kpiBox('Stores <90%', below90, '', below90 > 0 ? '#ea1100' : '#2a8703');
    html += '</div>';

    // Executive Insights
    var insights = [];
    if (avg7d > avg30d + 0.5) insights.push('<strong>Positive momentum:</strong> 7-day avg (' + avg7d.toFixed(1) + '%) is above 30-day (' + avg30d.toFixed(1) + '%), indicating recent improvement.');
    if (avg7d < avg30d - 0.5) insights.push('<strong>Declining trend:</strong> 7-day avg (' + avg7d.toFixed(1) + '%) is below 30-day (' + avg30d.toFixed(1) + '%). Investigate recent changes.');
    if (below80 > 0) insights.push('<strong>' + below80 + ' stores below 80% (critical):</strong> These stores need immediate review — likely equipment failures or sensor issues.');
    if (below90 > 0) insights.push(below90 + ' of ' + stores.length + ' stores (' + (below90/stores.length*100).toFixed(0) + '%) are below 90% target. ' + above90 + ' stores (' + (above90/stores.length*100).toFixed(0) + '%) are meeting target.');
    insights.push('Total estimated product loss: <strong>$' + (totalLoss/1000000).toFixed(1) + 'M</strong> with ' + casesOOT.toLocaleString() + ' cases out of target.');
    if (avgHvac >= 93) insights.push('HVAC performance is strong at ' + avgHvac.toFixed(1) + '% — well above target.');
    else insights.push('HVAC at ' + avgHvac.toFixed(1) + '% — room for improvement vs 93% benchmark.');

    html += insightBox(insights);

    // Store Distribution
    html += sectionTitle('📊', 'Store Distribution');
    var dist = [
        { range: '≥95%', count: stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day >= 95; }).length, color: '#2a8703' },
        { range: '90-95%', count: stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day >= 90 && s.twt_ref_30_day < 95; }).length, color: '#2a8703' },
        { range: '80-90%', count: stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day >= 80 && s.twt_ref_30_day < 90; }).length, color: '#f59e0b' },
        { range: '70-80%', count: stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day >= 70 && s.twt_ref_30_day < 80; }).length, color: '#ea1100' },
        { range: '<70%', count: stores.filter(function(s) { return s.twt_ref_30_day != null && s.twt_ref_30_day < 70; }).length, color: '#ea1100' },
        { range: 'No Data', count: stores.filter(function(s) { return s.twt_ref_30_day == null; }).length, color: '#999' }
    ];
    html += '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:16px;">';
    dist.forEach(function(d) {
        html += '<div style="text-align:center;padding:8px;border-radius:6px;background:#f9fafb;border:1px solid #e5e7eb;">'
            + '<div style="font-size:18px;font-weight:700;color:' + d.color + ';">' + d.count + '</div>'
            + '<div style="font-size:10px;color:#666;">' + d.range + '</div></div>';
    });
    html += '</div>';

    // Group breakdown
    var groupBy = level === 'sr_director' ? 'fm_sr_director_name' : 'fm_director_name';
    var childGroupBy = level === 'sr_director' ? 'fm_director_name' : 'fm_regional_manager_name';
    var childLabel = level === 'sr_director' ? 'Director' : 'Regional Manager';
    var groups = isAll ? groupStores(stores, groupBy) : groupStores(stores, childGroupBy);
    html += buildGroupTable(groups, isAll ? (level === 'sr_director' ? 'Sr. Director' : 'Director') : childLabel);

    // Bottom 10
    var bottom10 = stores.filter(function(d) { return d.twt_ref_30_day != null; })
        .sort(function(a, b) { return (a.twt_ref_30_day || 0) - (b.twt_ref_30_day || 0); }).slice(0, 10);
    html += sectionTitle('⚠️', 'Bottom 10 Stores (Ref 30-Day)');
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#0053e2;color:#fff;">';
    html += '<th style="' + th() + '">Store</th><th style="' + th() + '">City</th><th style="' + th() + '">RM</th>';
    html += '<th style="' + th() + '">Ref 30d</th><th style="' + th() + '">HVAC 30d</th>';
    html += '<th style="' + th() + '">Loss</th><th style="' + th() + '">Cases OOT</th>';
    html += '</tr></thead><tbody>';
    bottom10.forEach(function(s, i) {
        var bg = i % 2 === 0 ? '#f9fafb' : '#fff';
        html += '<tr style="background:' + bg + ';">';
        html += '<td style="' + td() + 'font-weight:600;">' + s.store_number + '</td>';
        html += '<td style="' + td() + '">' + (s.store_city || '') + ', ' + (s.store_state || '') + '</td>';
        html += '<td style="' + td() + '">' + (s.fm_regional_manager_name || '-') + '</td>';
        html += '<td style="' + td() + scoreColor(s.twt_ref_30_day) + '">' + pct(s.twt_ref_30_day) + '</td>';
        html += '<td style="' + td() + scoreColor(s.twt_hvac_30_day) + '">' + pct(s.twt_hvac_30_day) + '</td>';
        html += '<td style="' + td() + 'color:#ea1100;">$' + ((s.total_loss||0)/1000).toFixed(0) + 'K</td>';
        html += '<td style="' + td() + '">' + (s.cases_out_of_target||0).toLocaleString() + '</td></tr>';
    });
    html += '</tbody></table>';
    return html;
}

/* ═══════════════════════════════════════════════════════════
 *  WTW PDF — Executive Summary
 * ═══════════════════════════════════════════════════════════ */
function buildWtwPdf(stores, level, person, isAll) {
    if (typeof WTW_DATA === 'undefined') return '<p style="color:#999;">No WTW data loaded.</p>';

    var storeNums = new Set(stores.map(function(s) { return String(s.store_number); }));
    var wos = WTW_DATA.filter(function(w) { return storeNums.has(String(w.s)); });
    var completed = wos.filter(function(w) { return w.st === 'COMPLETED'; });
    var open = wos.length - completed.length;
    var compPct = wos.length > 0 ? (completed.length / wos.length * 100) : 0;
    var pmValid = wos.filter(function(w) { return w.pm != null; });
    var pmAvg = pmValid.length > 0 ? pmValid.reduce(function(s, w) { return s + parseFloat(w.pm); }, 0) / pmValid.length : 0;
    var pmBelow90 = pmValid.filter(function(w) { return parseFloat(w.pm) < 90; }).length;

    var p1 = wos.filter(function(w) { return w.ph === 'PH1'; });
    var p2 = wos.filter(function(w) { return w.ph === 'PH2'; });
    var p3 = wos.filter(function(w) { return w.ph === 'PH3'; });
    var p1done = p1.filter(function(w) { return w.st === 'COMPLETED'; }).length;
    var p2done = p2.filter(function(w) { return w.st === 'COMPLETED'; }).length;
    var p3done = p3.filter(function(w) { return w.st === 'COMPLETED'; }).length;
    var p1pct = p1.length > 0 ? (p1done/p1.length*100) : 0;
    var p2pct = p2.length > 0 ? (p2done/p2.length*100) : 0;
    var p3pct = p3.length > 0 ? (p3done/p3.length*100) : 0;

    // Readiness
    var ready = wos.filter(function(w) { return w.st !== 'COMPLETED' && w.pm != null && parseFloat(w.pm) >= 90; }).length;
    var reviewNeeded = wos.filter(function(w) { return w.st === 'COMPLETED' && w.pm != null && parseFloat(w.pm) >= 90; }).length;
    var critical = wos.filter(function(w) { return w.st === 'COMPLETED' && w.pm != null && parseFloat(w.pm) < 90; }).length;

    var html = '';

    // KPIs
    html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px;">';
    html += kpiBox('Total WOs', wos.length, '', '#333');
    html += kpiBox('Completed', completed.length, '', '#2a8703');
    html += kpiBox('Open', open, '', open > 0 ? '#ea1100' : '#2a8703');
    html += kpiBox('Completion', compPct.toFixed(1), '%');
    html += kpiBox('Avg PM Score', pmAvg.toFixed(1), '%');
    html += '</div>';

    // Phase breakdown
    html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px;">';
    html += kpiBox('Phase 1: ' + p1done + '/' + p1.length, p1pct.toFixed(0), '%');
    html += kpiBox('Phase 2: ' + p2done + '/' + p2.length, p2pct.toFixed(0), '%');
    html += kpiBox('Phase 3: ' + p3done + '/' + p3.length, p3pct.toFixed(0), '%');
    html += '</div>';

    // Readiness
    html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">';
    html += kpiBox('✓ Ready to Close', ready, '', '#2a8703');
    html += kpiBox('🔍 Review Needed', reviewNeeded, '', '#f59e0b');
    html += kpiBox('⚠ Critical Reopen', critical, '', critical > 0 ? '#ea1100' : '#2a8703');
    html += '</div>';

    // Insights
    var insights = [];
    insights.push('Overall completion at <strong>' + compPct.toFixed(1) + '%</strong> — ' + open + ' work orders still open.');
    if (p1pct > 50 && p2pct < 20) insights.push('<strong>Phase 2 is lagging:</strong> Only ' + p2pct.toFixed(0) + '% complete vs Phase 1 at ' + p1pct.toFixed(0) + '%. This phase needs immediate focus.');
    if (p3pct < 15) insights.push('<strong>Phase 3 needs attention:</strong> Only ' + p3pct.toFixed(0) + '% complete. Accelerate scheduling to avoid winter readiness gaps.');
    if (pmBelow90 > 0) insights.push('<strong>' + pmBelow90 + ' work orders have PM Score below 90%</strong> — these may need to be reopened for additional work.');
    if (critical > 0) insights.push('<strong>' + critical + ' critical reopens needed:</strong> Completed WOs with PM <90% should be reopened and reworked.');
    if (ready > 0) insights.push(ready + ' open WOs are <strong>ready to close</strong> (PM ≥90%, all criteria passing).');
    insights.push('Average PM Score: <strong>' + pmAvg.toFixed(1) + '%</strong> across ' + pmValid.length + ' scored work orders.');
    html += insightBox(insights);

    // Group breakdown
    var childKey = level === 'sr_director' ? 'fm' : 'rm';
    var childLabel = level === 'sr_director' ? 'Director' : 'Regional Manager';
    var grpMap = {};
    wos.forEach(function(w) {
        var grp = w[childKey] || 'Unknown';
        if (!grpMap[grp]) grpMap[grp] = { total: 0, done: 0, pmSum: 0, pmN: 0 };
        grpMap[grp].total++;
        if (w.st === 'COMPLETED') grpMap[grp].done++;
        if (w.pm != null) { grpMap[grp].pmSum += parseFloat(w.pm); grpMap[grp].pmN++; }
    });
    var grpList = Object.entries(grpMap)
        .map(function(e) { var n=e[0],d=e[1]; return {name:n,total:d.total,done:d.done,pct:d.total>0?d.done/d.total*100:0,pmAvg:d.pmN>0?d.pmSum/d.pmN:0}; })
        .sort(function(a,b) { return a.pct - b.pct; });

    if (grpList.length > 1) {
        html += sectionTitle('📊', 'WTW Completion by ' + childLabel);
        html += '<table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#0053e2;color:#fff;">';
        html += '<th style="' + th() + '">' + childLabel + '</th><th style="' + th() + '">Total</th>';
        html += '<th style="' + th() + '">Done</th><th style="' + th() + '">Completion</th><th style="' + th() + '">Avg PM</th></tr></thead><tbody>';
        grpList.forEach(function(g, i) {
            var bg = i % 2 === 0 ? '#f9fafb' : '#fff';
            html += '<tr style="background:' + bg + ';">';
            html += '<td style="' + td() + 'font-weight:600;">' + g.name + '</td>';
            html += '<td style="' + td() + '">' + g.total + '</td>';
            html += '<td style="' + td() + '">' + g.done + '</td>';
            html += '<td style="' + td() + scoreColor(g.pct) + '">' + g.pct.toFixed(1) + '%</td>';
            html += '<td style="' + td() + scoreColor(g.pmAvg) + '">' + g.pmAvg.toFixed(1) + '%</td></tr>';
        });
        html += '</tbody></table>';
    }

    return html;
}

/* ═══════════════════════════════════════════════════════════
 *  LEAK PDF — Executive Summary
 * ═══════════════════════════════════════════════════════════ */
function buildLeakPdf(stores, level, person, isAll) {
    if (typeof LK_STORES === 'undefined') return '<p style="color:#999;">No leak data loaded.</p>';

    var storeNums = new Set(stores.map(function(s) { return String(s.store_number); }));
    var leakStores = LK_STORES.filter(function(s) { return storeNums.has(String(s.s)); });
    var LK_T_VAL = typeof LK_T !== 'undefined' ? LK_T : 20;
    var tc = leakStores.reduce(function(s,d) { return s + (d.sc||0); }, 0);
    var tq = leakStores.reduce(function(s,d) { return s + (d.cytq||0); }, 0);
    var tl = leakStores.reduce(function(s,d) { return s + (d.cyl||0); }, 0);
    var avgRate = tc > 0 ? (tq / tc * 100) : 0;
    var over = leakStores.filter(function(s) { return (s.cylr||0) > LK_T_VAL; }).length;
    var critical = leakStores.filter(function(s) { return (s.cylr||0) > LK_T_VAL * 1.5; }).length;

    var html = '';

    // KPIs
    html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px;">';
    html += kpiBox('Stores', leakStores.length, '', '#333');
    html += kpiBox('System Charge', (tc/1000000).toFixed(1) + 'M lbs', '', '#333');
    html += kpiBox('Qty Leaked', (tq/1000).toFixed(0) + 'K lbs', '', '#ea1100');
    html += kpiBox('Leak Rate', avgRate.toFixed(1), '%', avgRate > LK_T_VAL ? '#ea1100' : '#2a8703');
    html += kpiBox('Over ' + LK_T_VAL + '% Threshold', over, '', over > 0 ? '#ea1100' : '#2a8703');
    html += '</div>';

    // Insights
    var insights = [];
    insights.push('Overall fleet leak rate: <strong>' + avgRate.toFixed(1) + '%</strong> across ' + leakStores.length + ' stores (' + (tc/1000000).toFixed(1) + 'M lbs total charge).');
    if (avgRate <= LK_T_VAL) insights.push('Fleet is <strong>within threshold</strong> (' + LK_T_VAL + '%). Good leak management practices overall.');
    else insights.push('<strong>Fleet exceeds ' + LK_T_VAL + '% threshold</strong> — systemic leak issues to address.');
    if (over > 0) insights.push('<strong>' + over + ' stores exceed ' + LK_T_VAL + '% leak rate</strong> — prioritize for repair/maintenance.');
    if (critical > 0) insights.push('<strong>' + critical + ' stores are critically high</strong> (>' + (LK_T_VAL*1.5).toFixed(0) + '%) — immediate intervention recommended.');
    insights.push('Total of <strong>' + tl.toLocaleString() + ' leak events</strong> recorded, with ' + (tq/1000).toFixed(0) + 'K lbs lost.');
    html += insightBox(insights);

    // Top leaking stores
    var top15 = leakStores.sort(function(a,b) { return (b.cylr||0) - (a.cylr||0); }).slice(0, 15);
    html += sectionTitle('🚨', 'Top Leaking Stores');
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#0053e2;color:#fff;">';
    html += '<th style="' + th() + '">Store</th><th style="' + th() + '">Location</th>';
    html += '<th style="' + th() + '">Charge</th><th style="' + th() + '">Leaked</th>';
    html += '<th style="' + th() + '">Rate</th><th style="' + th() + '">Events</th></tr></thead><tbody>';
    top15.forEach(function(s, i) {
        var bg = i % 2 === 0 ? '#f9fafb' : '#fff';
        var rc = (s.cylr||0) > LK_T_VAL ? 'color:#ea1100;font-weight:700;' : 'color:#2a8703;';
        html += '<tr style="background:' + bg + ';">';
        html += '<td style="' + td() + 'font-weight:600;">' + s.s + '</td>';
        html += '<td style="' + td() + '">' + (s.city||'') + ', ' + (s.st||'') + '</td>';
        html += '<td style="' + td() + '">' + Math.round(s.sc).toLocaleString() + '</td>';
        html += '<td style="' + td() + 'color:#ea1100;">' + Math.round(s.cytq).toLocaleString() + '</td>';
        html += '<td style="' + td() + rc + '">' + (s.cylr||0).toFixed(1) + '%</td>';
        html += '<td style="' + td() + '">' + (s.cyl||0) + '</td></tr>';
    });
    html += '</tbody></table>';

    // Group summary
    var grpKey = level === 'sr_director' ? 'fm' : 'rm';
    var grpLabel = level === 'sr_director' ? 'Director' : 'Regional Manager';
    var grpMap = {};
    leakStores.forEach(function(ls) {
        var grp = ls[grpKey] || 'Unknown';
        if (!grpMap[grp]) grpMap[grp] = { charge:0, qty:0, leaks:0, stores:0, over:0 };
        grpMap[grp].charge += ls.sc || 0;
        grpMap[grp].qty += ls.cytq || 0;
        grpMap[grp].leaks += ls.cyl || 0;
        grpMap[grp].stores++;
        if ((ls.cylr||0) > LK_T_VAL) grpMap[grp].over++;
    });
    var grpList = Object.entries(grpMap)
        .map(function(e) { var n=e[0],d=e[1]; return {name:n,stores:d.stores,charge:d.charge,qty:d.qty,leaks:d.leaks,over:d.over,rate:d.charge>0?d.qty/d.charge*100:0}; })
        .sort(function(a,b) { return b.rate - a.rate; });

    if (grpList.length > 1) {
        html += sectionTitle('📊', 'Leak Rate by ' + grpLabel);
        html += '<table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#0053e2;color:#fff;">';
        html += '<th style="' + th() + '">' + grpLabel + '</th><th style="' + th() + '">Stores</th>';
        html += '<th style="' + th() + '">Charge</th><th style="' + th() + '">Leaked</th>';
        html += '<th style="' + th() + '">Rate</th><th style="' + th() + '">Over ' + LK_T_VAL + '%</th></tr></thead><tbody>';
        grpList.forEach(function(g, i) {
            var bg = i % 2 === 0 ? '#f9fafb' : '#fff';
            var rc = g.rate > LK_T_VAL ? 'color:#ea1100;font-weight:700;' : 'color:#2a8703;';
            html += '<tr style="background:' + bg + ';">';
            html += '<td style="' + td() + 'font-weight:600;">' + g.name + '</td>';
            html += '<td style="' + td() + '">' + g.stores + '</td>';
            html += '<td style="' + td() + '">' + Math.round(g.charge).toLocaleString() + '</td>';
            html += '<td style="' + td() + '">' + Math.round(g.qty).toLocaleString() + '</td>';
            html += '<td style="' + td() + rc + '">' + g.rate.toFixed(1) + '%</td>';
            html += '<td style="' + td() + (g.over > 0 ? 'color:#ea1100;' : '') + '">' + g.over + '</td></tr>';
        });
        html += '</tbody></table>';
    }

    return html;
}

/* ═══════════════════════════════════════════════════════════
 *  GENERATE PDF
 * ═══════════════════════════════════════════════════════════ */
async function generatePdf() {
    var level = document.getElementById('pdfViewLevel').value;
    var person = document.getElementById('pdfPersonSelect').value;
    var btn = document.getElementById('pdfGenerateBtn');

    btn.disabled = true;
    btn.textContent = '⏳ Generating...';

    try {
        var content = buildPdfContent(pdfExportTab, level, person);
        var htmlStr = content.innerHTML;

        if (!htmlStr || htmlStr.length < 50) {
            alert('No data to export. Check your filters.');
            return;
        }

        var levelSlug = level === 'sr_director' ? 'SrDir' : 'Dir';
        var personSlug = person === '__all__' ? 'All' : person.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
        var tabSlug = pdfExportTab.toUpperCase();
        var dateSlug = new Date().toISOString().slice(0, 10);
        var filename = tabSlug + '_' + levelSlug + '_' + personSlug + '_' + dateSlug + '.pdf';

        // Create iframe for html2canvas capture
        var iframe = document.createElement('iframe');
        iframe.style.cssText = 'position:fixed;left:0;top:0;width:1200px;height:900px;opacity:0.01;z-index:-1;border:none;';
        document.body.appendChild(iframe);

        var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write('<!DOCTYPE html><html><head><style>'
            + '* { margin:0; padding:0; box-sizing:border-box; }'
            + 'body { font-family:system-ui,-apple-system,sans-serif; background:#fff; color:#1a1a1a; padding:32px; width:1100px; }'
            + 'table { border-collapse:collapse; width:100%; }'
            + '</style></head><body>' + htmlStr + '</body></html>');
        iframeDoc.close();

        await new Promise(function(r) { setTimeout(r, 500); });

        var opt = {
            margin: [0.3, 0.3, 0.3, 0.3],
            filename: filename,
            image: { type: 'jpeg', quality: 0.95 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'in', format: 'letter', orientation: 'landscape' },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };

        await html2pdf().set(opt).from(iframeDoc.body).save();
        document.body.removeChild(iframe);
        closePdfModal();
    } catch (err) {
        console.error('PDF generation failed:', err);
        alert('PDF generation failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '📄 Generate PDF';
    }
}
