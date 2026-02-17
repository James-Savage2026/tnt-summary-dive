/**
 * PDF Export Module — TnT/WTW/Leak Dashboard
 * Executive-level PDF reports with charts, insights, and action items.
 */

/* ── state ── */
var pdfExportTab = 'tnt';

/* ── banner helpers ── */
function isWalmart(d) {
    var b = (d.banner_desc || d.bn || '').toLowerCase();
    return (b.indexOf('walmart') >= 0 || b.indexOf('wal-mart') >= 0 || b.indexOf('supercenter') >= 0 ||
            b.indexOf('neighborhood') >= 0) && b.indexOf('sam') < 0;
}
function isSams(d) {
    var b = (d.banner_desc || d.bn || '').toLowerCase();
    return b.indexOf('sam') >= 0;
}
function splitByBanner(stores) {
    return {
        wm: stores.filter(isWalmart),
        sams: stores.filter(isSams),
        all: stores
    };
}

/* ── helpers ── */
function getPeopleForLevel(level) {
    if (level === 'sr_director')
        return Array.from(new Set(storeData.map(function(d){return d.fm_sr_director_name;}).filter(Boolean))).sort();
    return Array.from(new Set(storeData.map(function(d){return d.fm_director_name;}).filter(Boolean))).sort();
}
function getStoresForPerson(level, person) {
    if (level === 'sr_director') return storeData.filter(function(d){return d.fm_sr_director_name===person;});
    return storeData.filter(function(d){return d.fm_director_name===person;});
}

/* ── modal (updated for combined report) ── */
function openPdfModal(tab) {
    pdfExportTab = tab;
    document.getElementById('pdfExportModal').classList.remove('hidden');
    var labels = {tnt:'TnT Dashboard', wtw:'Win the Winter', leak:'Leak Management', all:'Executive Summary (All Tabs)'};
    document.getElementById('pdfTabLabel').textContent = labels[tab] || tab;
    document.getElementById('pdfViewLevel').value = 'sr_director';
    updatePdfPersonList();
}
function closePdfModal() { document.getElementById('pdfExportModal').classList.add('hidden'); }
function updatePdfPersonList() {
    var level = document.getElementById('pdfViewLevel').value;
    var sel = document.getElementById('pdfPersonSelect');
    var people = getPeopleForLevel(level);
    sel.innerHTML = '<option value="__all__">All (Full Report)</option>' +
        people.map(function(p){return '<option value="'+p+'">'+p+'</option>';}).join('');
}

/* ══════════ STYLE HELPERS (polished) ══════════ */

/* ══════════ BANNER COMPARISON TABLE ══════════ */
function bannerComparisonRow(stores) {
    var sp = splitByBanner(stores);
    var labels = [{key:'all',name:'Combined',icon:'🏢',stores:sp.all},
                  {key:'wm',name:'Walmart',icon:'🟦',stores:sp.wm},
                  {key:'sams',name:"Sam's Club",icon:'🟩',stores:sp.sams}];
    var h = '<div class="no-break" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0 20px;">';
    labels.forEach(function(b) {
        var s = b.stores;
        var r30 = safeAvg(s,'twt_ref_30_day'), h30 = safeAvg(s,'twt_hvac_30_day');
        var loss = s.reduce(function(a,d){return a+(d.total_loss||0);},0);
        var b90 = s.filter(function(d){return d.twt_ref_30_day!=null&&d.twt_ref_30_day<90;}).length;
        var borderC = b.key==='wm'?'#0053e2':b.key==='sams'?'#16a34a':'#334155';
        h += '<div style="border:2px solid '+borderC+';border-radius:12px;padding:14px;background:#fff;">';
        h += '<div style="font-size:13px;font-weight:800;color:'+borderC+';margin-bottom:10px;display:flex;align-items:center;gap:6px;">'+b.icon+' '+b.name;
        h += '<span style="font-size:10px;font-weight:500;color:#94a3b8;margin-left:auto;">'+s.length+' stores</span></div>';
        h += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;">';
        h += '<div style="text-align:center;"><div style="font-size:18px;font-weight:800;'+scoreColor(r30)+'">'+r30.toFixed(1)+'%</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;">Ref 30d</div></div>';
        h += '<div style="text-align:center;"><div style="font-size:18px;font-weight:800;'+scoreColor(h30)+'">'+h30.toFixed(1)+'%</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;">HVAC 30d</div></div>';
        h += '<div style="text-align:center;"><div style="font-size:14px;font-weight:700;color:#dc2626;">$'+(loss/1e6).toFixed(1)+'M</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;">Loss</div></div>';
        h += '<div style="text-align:center;"><div style="font-size:14px;font-weight:700;'+(b90>0?'color:#dc2626;':'color:#16a34a;')+'">'+b90+'</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;">&lt;90%</div></div>';
        h += '</div></div>';
    });
    h += '</div>';
    return h;
}

/* ══════════ OPS REGION BREAKOUT ══════════ */
function buildOpsRegionBreakout(stores) {
    /* Group by realty_ops_region, only show regions with significant presence (>=10 stores) */
    var regionMap = {};
    stores.forEach(function(s) {
        var r = s.realty_ops_region;
        if (!r) return;
        if (!regionMap[r]) regionMap[r] = [];
        regionMap[r].push(s);
    });
    var regions = Object.entries(regionMap)
        .map(function(e) { return { id: e[0], stores: e[1] }; })
        .filter(function(r) { return r.stores.length >= 10; })
        .sort(function(a, b) { return b.stores.length - a.stores.length; });
    if (regions.length <= 1) return '';
    /* Build rows: Combined first, then each region sorted by Ref 30d desc */
    var rows = [];
    var r30All = safeAvg(stores,'twt_ref_30_day'), h30All = safeAvg(stores,'twt_hvac_30_day');
    var lossAll = stores.reduce(function(a,d){return a+(d.total_loss||0);},0);
    var b90All = stores.filter(function(d){return d.twt_ref_30_day!=null&&d.twt_ref_30_day<90;}).length;
    rows.push({name:'Combined',count:stores.length,r30:r30All,h30:h30All,loss:lossAll,b90:b90All,isCombined:true});
    regions.forEach(function(reg) {
        var s = reg.stores;
        rows.push({
            name:'Region '+reg.id, count:s.length,
            r30:safeAvg(s,'twt_ref_30_day'), h30:safeAvg(s,'twt_hvac_30_day'),
            loss:s.reduce(function(a,d){return a+(d.total_loss||0);},0),
            b90:s.filter(function(d){return d.twt_ref_30_day!=null&&d.twt_ref_30_day<90;}).length,
            isCombined:false
        });
    });
    /* Sort non-combined rows by Ref 30d descending */
    var dataRows = rows.slice(1).sort(function(a,b){return b.r30-a.r30;});
    var h = sectionTitle('\ud83d\uddfa\ufe0f', 'Performance by Ops Realty Region');
    h += '<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
    h += '<th style="'+th()+'">Region</th><th style="'+th()+'">Stores</th>';
    h += '<th style="'+th()+'">Ref 30d</th><th style="'+th()+'">HVAC 30d</th>';
    h += '<th style="'+th()+'">Loss</th><th style="'+th()+'">&lt;90%</th></tr></thead><tbody>';
    /* Combined row (bold, slight background) */
    h += '<tr style="background:#e2e8f0;font-weight:700;">';
    h += '<td style="'+td()+'">'+rows[0].name+'</td>';
    h += '<td style="'+td()+'">'+rows[0].count+'</td>';
    h += '<td style="'+td()+scoreColor(rows[0].r30)+'">'+rows[0].r30.toFixed(1)+'%</td>';
    h += '<td style="'+td()+scoreColor(rows[0].h30)+'">'+rows[0].h30.toFixed(1)+'%</td>';
    h += '<td style="'+td()+'color:#dc2626;">$'+(rows[0].loss/1e6).toFixed(1)+'M</td>';
    h += '<td style="'+td()+(rows[0].b90>0?'color:#dc2626;':'')+'">'+rows[0].b90+'</td></tr>';
    /* Data rows */
    dataRows.forEach(function(r,i) {
        var bg = i%2===0?'#f8fafc':'#fff';
        h += '<tr style="background:'+bg+';">';
        h += '<td style="'+td()+'font-weight:600;">'+r.name+'</td>';
        h += '<td style="'+td()+'">'+r.count+'</td>';
        h += '<td style="'+td()+scoreColor(r.r30)+'">'+r.r30.toFixed(1)+'%</td>';
        h += '<td style="'+td()+scoreColor(r.h30)+'">'+r.h30.toFixed(1)+'%</td>';
        h += '<td style="'+td()+'color:#dc2626;">$'+(r.loss/1e6).toFixed(1)+'M</td>';
        h += '<td style="'+td()+(r.b90>0?'color:#dc2626;':'')+'">'+r.b90+'</td></tr>';
    });
    h += '</tbody></table>';
    return h;
}

/* ══════════ RM BREAKOUT TABLE ══════════ */
function buildRmBreakout(stores, level) {
    /* Show Regional Manager breakout if the selected person has >1 RM */
    var rmMap = {};
    stores.forEach(function(s) {
        var rm = s.fm_regional_manager_name;
        if (!rm) return;
        if (!rmMap[rm]) rmMap[rm] = [];
        rmMap[rm].push(s);
    });
    var rms = Object.entries(rmMap).map(function(e) {
        var name = e[0], ss = e[1];
        var sp = splitByBanner(ss);
        return {
            name: name, count: ss.length,
            wmCount: sp.wm.length, samsCount: sp.sams.length,
            avgRef30: safeAvg(ss,'twt_ref_30_day'), avgHvac30: safeAvg(ss,'twt_hvac_30_day'),
            wmRef30: sp.wm.length > 0 ? safeAvg(sp.wm,'twt_ref_30_day') : null,
            samsRef30: sp.sams.length > 0 ? safeAvg(sp.sams,'twt_ref_30_day') : null,
            totalLoss: ss.reduce(function(a,d){return a+(d.total_loss||0);},0),
            casesOOT: ss.reduce(function(a,d){return a+(d.cases_out_of_target||0);},0)
        };
    }).sort(function(a,b){return b.avgRef30-a.avgRef30;});
    if (rms.length <= 1) return '';  /* Only show if >1 RM */
    var h = sectionTitle('📍','Performance by Regional Manager');
    h += '<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
    h += '<th style="'+th()+'">Regional Manager</th><th style="'+th()+'">Stores</th>';
    h += '<th style="'+th()+'">Ref 30d</th><th style="'+th()+'">WM Ref</th><th style="'+th()+'">Sam\'s Ref</th>';
    h += '<th style="'+th()+'">HVAC 30d</th><th style="'+th()+'">Loss</th></tr></thead><tbody>';
    rms.forEach(function(g,i) {
        var bg = i%2===0?'#f8fafc':'#fff';
        h += '<tr style="background:'+bg+';">';
        h += '<td style="'+td()+'font-weight:600;">'+g.name+'</td>';
        h += '<td style="'+td()+'">'+g.count+'</td>';
        h += '<td style="'+td()+scoreColor(g.avgRef30)+'">'+g.avgRef30.toFixed(1)+'%</td>';
        h += '<td style="'+td()+(g.wmRef30!=null?scoreColor(g.wmRef30):'')+'">'+( g.wmRef30!=null?g.wmRef30.toFixed(1)+'%':'—')+'</td>';
        h += '<td style="'+td()+(g.samsRef30!=null?scoreColor(g.samsRef30):'')+'">'+( g.samsRef30!=null?g.samsRef30.toFixed(1)+'%':'—')+'</td>';
        h += '<td style="'+td()+scoreColor(g.avgHvac30)+'">'+g.avgHvac30.toFixed(1)+'%</td>';
        h += '<td style="'+td()+'color:#dc2626;">$'+g.totalLoss.toLocaleString(undefined,{maximumFractionDigits:0})+'</td></tr>';
    });
    h += '</tbody></table>';
    return h;
}

/* ══════════ BOTTOM 10 STORES TABLE ══════════ */
function buildBottom10Table(stores) {
    var bot = stores.filter(function(d) { return d.twt_ref_30_day != null; })
        .sort(function(a, b) { return (a.twt_ref_30_day || 0) - (b.twt_ref_30_day || 0); }).slice(0, 10);
    if (bot.length === 0) return '';
    var h = '<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="' + S.hdr + '">';
    h += '<th style="' + th() + '">Store</th><th style="' + th() + '">Banner</th><th style="' + th() + '">RM</th>';
    h += '<th style="' + th() + '">Ref 30d</th><th style="' + th() + '">HVAC 30d</th>';
    h += '<th style="' + th() + '">Loss</th><th style="' + th() + '">Cases OOT</th></tr></thead><tbody>';
    bot.forEach(function(s, i) {
        var bg = i % 2 === 0 ? '#f8fafc' : '#fff';
        var bn = isSams(s) ? "Sam's" : isWalmart(s) ? 'WM' : (s.banner_desc || '').substring(0, 10);
        h += '<tr style="background:' + bg + ';">';
        h += '<td style="' + td() + 'font-weight:600;">' + s.store_number + '</td>';
        h += '<td style="' + td() + 'font-size:10px;">' + bn + '</td>';
        h += '<td style="' + td() + '">' + (s.fm_regional_manager_name || '-') + '</td>';
        h += '<td style="' + td() + scoreColor(s.twt_ref_30_day) + '">' + pct(s.twt_ref_30_day) + '</td>';
        h += '<td style="' + td() + scoreColor(s.twt_hvac_30_day) + '">' + pct(s.twt_hvac_30_day) + '</td>';
        h += '<td style="' + td() + 'color:#dc2626;">$' + ((s.total_loss || 0) / 1e3).toFixed(0) + 'K</td>';
        h += '<td style="' + td() + '">' + ((s.cases_out_of_target || 0)).toLocaleString() + '</td></tr>';
    });
    h += '</tbody></table>';
    return sectionBlock('\u26a0\ufe0f', 'Bottom 10 Stores (Ref 30-Day)', h);
}

/* ══════════ BUILD PDF CONTENT ══════════ */
function buildPdfContent(tab,level,person) {
    var isAll=person==='__all__';
    var stores=isAll?storeData:getStoresForPerson(level,person);
    var levelLabel=level==='sr_director'?'Sr. Director':'FM Director';
    var personLabel=isAll?'All Regions':person;
    var now=new Date();
    var dateStr=(now.getMonth()+1)+'/'+now.getDate()+'/'+now.getFullYear();
    var container=document.createElement('div');
    container.style.cssText=S.page;
    var tabNames={tnt:'\ud83d\udcca Time in Target Report',wtw:'\u2744\ufe0f Win the Winter Report',leak:'\ud83e\uddca Leak Management Report',all:'\ud83d\udcca Executive Summary Report'};
    var tabName=tabNames[tab]||tab;
    // Header
    container.innerHTML='<div style="background:linear-gradient(135deg,#0053e2 0%,#003da5 100%);border-radius:12px;padding:24px 28px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;">'
        +'<div><h1 style="font-size:22px;font-weight:800;color:#fff;margin:0;letter-spacing:-0.5px;">'+tabName+'</h1>'
        +'<p style="font-size:12px;color:rgba(255,255,255,0.8);margin:6px 0 0;">'+levelLabel+': <strong style="color:#ffc220;">'+personLabel+'</strong></p></div>'
        +'<div style="text-align:right;"><div style="font-size:20px;color:#ffc220;font-weight:800;letter-spacing:1px;">&#x2726;</div>'
        +'<p style="font-size:10px;color:rgba(255,255,255,0.7);margin:4px 0 0;">Generated '+dateStr+'</p>'
        +'<p style="font-size:10px;color:rgba(255,255,255,0.7);margin:2px 0 0;">'+stores.length.toLocaleString()+' stores</p></div></div>';
    if (tab==='tnt') container.innerHTML+=buildTntPdf(stores,level,person,isAll);
    else if (tab==='wtw') container.innerHTML+=buildWtwPdf(stores,level,person,isAll);
    else if (tab==='leak') container.innerHTML+=buildLeakPdf(stores,level,person,isAll);
    else if (tab==='all') container.innerHTML+=buildCombinedPdf(stores,level,person,isAll);
    // Footer
    container.innerHTML+='<div style="margin-top:32px;padding-top:12px;border-top:2px solid #e2e8f0;font-size:9px;color:#94a3b8;display:flex;justify-content:space-between;align-items:center;">'
        +'<span>North BU HVAC/R Report Hub \u2022 '+dateStr+'</span>'
        +'<span style="color:#0053e2;font-weight:600;">\u2726 Walmart</span>'
        +'<span>'+levelLabel+': '+personLabel+' \u2022 '+stores.length.toLocaleString()+' stores</span></div>';
    return container;
}

/* ══════════ TnT PDF ══════════ */
function buildTntPdf(stores,level,person,isAll) {
    var a30=safeAvg(stores,'twt_ref_30_day'),a7=safeAvg(stores,'twt_ref_7_day');
    var a90=safeAvg(stores,'twt_ref_90_day'),aH=safeAvg(stores,'twt_hvac_30_day');
    var loss=stores.reduce(function(s,d){return s+(d.total_loss||0);},0);
    var oot=stores.reduce(function(s,d){return s+(d.cases_out_of_target||0);},0);
    var b80=stores.filter(function(s){return s.twt_ref_30_day!=null&&s.twt_ref_30_day<80;}).length;
    var b90=stores.filter(function(s){return s.twt_ref_30_day!=null&&s.twt_ref_30_day<90;}).length;
    var a90c=stores.filter(function(s){return s.twt_ref_30_day!=null&&s.twt_ref_30_day>=90;}).length;
    var trend=a7>a30?'\ud83d\udcc8 Up':a7<a30-1?'\ud83d\udcc9 Down':'\u27a1\ufe0f Stable';
    var h='';
    // KPIs + Gauges (keep together)
    h+='<div class="no-break">';
    h+='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px;">';
    h+=kpiBox('Ref 7-Day',a7,'%')+kpiBox('Ref 30-Day',a30,'%')+kpiBox('Ref 90-Day',a90,'%');
    h+=kpiBox('HVAC 30-Day',aH,'%')+kpiBox('7d Trend',trend,'',a7>=a30?'#16a34a':'#dc2626');
    h+='</div>';
    h+=chartRow(svgGauge('Ref 7-Day',a7),svgGauge('Ref 30-Day',a30),svgGauge('Ref 90-Day',a90),svgGauge('HVAC 30-Day',aH));
    h+='</div>';

    // Banner Comparison
    h+=sectionBlock('\ud83c\udfe2','Performance by Banner',bannerComparisonRow(stores));

    // Ops Region Breakout
    var opsContent=buildOpsRegionBreakout(stores);
    if(opsContent) h+=opsContent;

    // 90-Day Historical Trend
    var histContent=buildHistTrend(stores, person);
    if(histContent) h+=histContent;

    // Insights
    var ins=[];
    var sp=splitByBanner(stores);
    if (a7>a30+0.5) ins.push('<strong>Positive momentum:</strong> 7-day ('+a7.toFixed(1)+'%) is above 30-day ('+a30.toFixed(1)+'%).');
    if (a7<a30-0.5) ins.push('<strong>Declining trend:</strong> 7-day ('+a7.toFixed(1)+'%) is below 30-day ('+a30.toFixed(1)+'%).');
    if (sp.wm.length>0&&sp.sams.length>0) {
        var wmR=safeAvg(sp.wm,'twt_ref_30_day'),saR=safeAvg(sp.sams,'twt_ref_30_day');
        ins.push('Walmart Ref 30d: <strong>'+wmR.toFixed(1)+'%</strong> ('+sp.wm.length+' stores) vs Sam\'s: <strong>'+saR.toFixed(1)+'%</strong> ('+sp.sams.length+' stores).');
    }
    if (b80>0) ins.push('<strong>'+b80+' stores below 80%</strong> \u2014 likely equipment failures or sensor issues.');
    ins.push(a90c+' of '+stores.length+' stores ('+(a90c/stores.length*100).toFixed(0)+'%) meeting 90% target.');
    ins.push('Product loss: <strong>$'+(loss/1e6).toFixed(1)+'M</strong> with '+oot.toLocaleString()+' cases OOT.');
    h+=insightBox(ins);

    // Regional Manager Breakout (skip for Sr Director — Top/Bottom 5 below is sufficient)
    if(level!=='sr_director') {
        var rmContent=buildRmBreakout(stores,level);
        if(rmContent) h+=rmContent;
    }

    // Group breakdown bar chart + table
    var gBy=level==='sr_director'?'fm_sr_director_name':'fm_director_name';
    var cBy=level==='sr_director'?'fm_director_name':'fm_regional_manager_name';
    var cLbl=level==='sr_director'?'Director':'Regional Manager';
    var grps=isAll?groupStores(stores,gBy):groupStores(stores,cBy);
    var grpLabel=isAll?(level==='sr_director'?'Sr. Director':'Director'):cLbl;
    var gcd=grps.slice(0,15).map(function(g){
        return {label:g.name.substring(0,22),value:g.avgRef30,color:g.avgRef30>=95?'#15803d':g.avgRef30>=90?'#16a34a':g.avgRef30>=85?'#65a30d':g.avgRef30>=80?'#d97706':'#dc2626'};
    });
    h+='<div class="no-break">';
    h+=svgBarChart('Ref 30-Day by '+grpLabel,gcd,{width:480,labelWidth:160,max:100,suffix:'%'});
    h+='</div>';
    h+=buildGroupTable(grps,grpLabel);

    // Bottom 10
    h+=buildBottom10Table(stores);

    // Top 5 / Bottom 5 Regionals (skip for Sr Director — keep it at Director level)
    if(level!=='sr_director') {
        h+=buildTopBottomRegionals(stores);
    }

    return h;
}

/* ══════════ WTW PDF ══════════ */
function buildWtwPdf(stores,level,person,isAll) {
    if (typeof WTW_DATA==='undefined') return '<p style="color:#94a3b8;">No WTW data loaded.</p>';
    var nums=new Set(stores.map(function(s){return String(s.store_number);}));
    var wos=WTW_DATA.filter(function(w){return nums.has(String(w.s));});
    var done=wos.filter(function(w){return w.st==='COMPLETED';});
    var opn=wos.length-done.length;
    var cpct=wos.length>0?(done.length/wos.length*100):0;
    var pmV=wos.filter(function(w){return w.pm!=null&&!isNaN(parseFloat(w.pm));});
    var pmA=pmV.length>0?pmV.reduce(function(s,w){return s+parseFloat(w.pm);},0)/pmV.length:0;
    if(isNaN(pmA))pmA=0;
    var pmB90=pmV.filter(function(w){return parseFloat(w.pm)<90;}).length;
    var p1=wos.filter(function(w){return w.ph==='PH1';}),p2=wos.filter(function(w){return w.ph==='PH2';}),p3=wos.filter(function(w){return w.ph==='PH3';});
    var p1d=p1.filter(function(w){return w.st==='COMPLETED';}).length;
    var p2d=p2.filter(function(w){return w.st==='COMPLETED';}).length;
    var p3d=p3.filter(function(w){return w.st==='COMPLETED';}).length;
    var p1p=p1.length>0?p1d/p1.length*100:0,p2p=p2.length>0?p2d/p2.length*100:0,p3p=p3.length>0?p3d/p3.length*100:0;
    var rdy=wos.filter(function(w){return w.st!=='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)>=90;}).length;
    var rev=wos.filter(function(w){return w.st==='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)>=90;}).length;
    var crit=wos.filter(function(w){return w.st==='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)<90;}).length;
    var h='';
    h+='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px;">';
    h+=kpiBox('Total WOs',wos.length,'','#334155')+kpiBox('Completed',done.length,'','#16a34a');
    h+=kpiBox('Open',opn,'',opn>0?'#dc2626':'#16a34a')+kpiBox('Completion',cpct.toFixed(1),'%');
    h+=kpiBox('Avg PM',pmA>0?pmA.toFixed(1):'N/A',pmA>0?'%':'',pmA>=90?'#16a34a':pmA>0?'#dc2626':'#94a3b8');
    h+='</div>';
    h+=chartRow(
        svgDonutChart('WO Status',[{label:'Completed',value:done.length,color:'#16a34a'},{label:'Open',value:opn,color:'#dc2626'}]),
        svgDonutChart('PM Readiness',[{label:'Ready to Close',value:rdy,color:'#16a34a'},{label:'Review Needed',value:rev,color:'#d97706'},{label:'Critical Reopen',value:crit,color:'#dc2626'}])
    );
    h+=svgBarChart('Phase Completion',[
        {label:'Phase 1 ('+p1d+'/'+p1.length+')',value:p1p,color:p1p>=50?'#16a34a':'#d97706'},
        {label:'Phase 2 ('+p2d+'/'+p2.length+')',value:p2p,color:p2p>=50?'#16a34a':p2p>=20?'#d97706':'#dc2626'},
        {label:'Phase 3 ('+p3d+'/'+p3.length+')',value:p3p,color:p3p>=50?'#16a34a':p3p>=20?'#d97706':'#dc2626'}
    ],{width:480,labelWidth:150,max:100,suffix:'%',barHeight:28});
    h+='<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0;">';
    h+=kpiBox('\u2713 Ready to Close',rdy,'','#16a34a');
    h+=kpiBox('\ud83d\udd0d Review Needed',rev,'','#d97706');
    h+=kpiBox('\u26a0 Critical Reopen',crit,'',crit>0?'#dc2626':'#16a34a');
    h+='</div>';
    var ins=[];
    ins.push('Overall completion at <strong>'+cpct.toFixed(1)+'%</strong> \u2014 '+opn+' work orders still open.');
    if(p1p>50&&p2p<20) ins.push('<strong>Phase 2 lagging:</strong> '+p2p.toFixed(0)+'% vs Phase 1 at '+p1p.toFixed(0)+'%.');
    if(p3p<15) ins.push('<strong>Phase 3 needs attention:</strong> Only '+p3p.toFixed(0)+'% complete.');
    if(pmB90>0) ins.push('<strong>'+pmB90+' WOs have PM <90%</strong> \u2014 may need reopening.');
    if(crit>0) ins.push('<strong>'+crit+' critical reopens</strong> \u2014 completed WOs with PM <90%.');
    if(rdy>0) ins.push(rdy+' open WOs are <strong>ready to close</strong> (PM \u226590%).');
    if(pmV.length>0) ins.push('Average PM Score: <strong>'+pmA.toFixed(1)+'%</strong> across '+pmV.length+' scored WOs.');
    h+=insightBox(ins);
    // Group breakdown (descending by completion)
    var cKey=level==='sr_director'?'fm':'rm',cLbl=level==='sr_director'?'Director':'Regional Manager';
    var gm={};
    wos.forEach(function(w){var g=w[cKey]||'Unknown';if(!gm[g])gm[g]={t:0,d:0,ps:0,pn:0};gm[g].t++;if(w.st==='COMPLETED')gm[g].d++;if(w.pm!=null&&!isNaN(parseFloat(w.pm))){gm[g].ps+=parseFloat(w.pm);gm[g].pn++;}});
    var gl=Object.entries(gm).map(function(e){var n=e[0],d=e[1];return{name:n,total:d.t,done:d.d,pct:d.t>0?d.d/d.t*100:0,pmAvg:d.pn>0?d.ps/d.pn:0};}).sort(function(a,b){return b.pct-a.pct;});
    if(gl.length>1) {
        var gbd=gl.slice(0,15).map(function(g){return{label:g.name.substring(0,22),value:g.pct,color:g.pct>=50?'#16a34a':g.pct>=20?'#d97706':'#dc2626'};});
        h+=svgBarChart('Completion by '+cLbl,gbd,{width:480,labelWidth:160,max:100,suffix:'%'});
        h+=sectionTitle('\ud83d\udcca','WTW by '+cLbl);
        h+='<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
        h+='<th style="'+th()+'">'+cLbl+'</th><th style="'+th()+'">Total</th><th style="'+th()+'">Done</th><th style="'+th()+'">Completion</th><th style="'+th()+'">Avg PM</th></tr></thead><tbody>';
        gl.forEach(function(g,i){var bg=i%2===0?'#f8fafc':'#fff';h+='<tr style="background:'+bg+';">';h+='<td style="'+td()+'font-weight:600;">'+g.name+'</td>';h+='<td style="'+td()+'">'+g.total+'</td>';h+='<td style="'+td()+'">'+g.done+'</td>';h+='<td style="'+td()+scoreColor(g.pct)+'">'+g.pct.toFixed(1)+'%</td>';h+='<td style="'+td()+scoreColor(g.pmAvg)+'">'+g.pmAvg.toFixed(1)+'%</td></tr>';});
        h+='</tbody></table>';
    }
    // Manager × Phase completion matrix
    h+=buildWtwManagerMatrix(wos, level);
    return h;
}

/* ══════════ LEAK PDF ══════════ */
function buildLeakPdf(stores,level,person,isAll) {
    if (typeof LK_STORES==='undefined') return '<p style="color:#94a3b8;">No leak data loaded.</p>';
    var nums=new Set(stores.map(function(s){return String(s.store_number);}));
    var ls=LK_STORES.filter(function(s){return nums.has(String(s.s));});
    var LKT=typeof LK_T!=='undefined'?LK_T:20;
    var tc=ls.reduce(function(s,d){return s+(d.sc||0);},0);
    var tq=ls.reduce(function(s,d){return s+(d.cytq||0);},0);
    var tl=ls.reduce(function(s,d){return s+(d.cyl||0);},0);
    var ar=tc>0?(tq/tc*100):0;
    var ov=ls.filter(function(s){return(s.cylr||0)>LKT;}).length;
    var cr=ls.filter(function(s){return(s.cylr||0)>LKT*1.5;}).length;
    var h='';
    h+='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px;">';
    h+=kpiBox('Stores',ls.length,'','#334155')+kpiBox('System Charge',(tc/1e6).toFixed(1)+'M lbs','','#334155');
    h+=kpiBox('Qty Leaked',(tq/1e3).toFixed(0)+'K lbs','','#dc2626');
    h+=kpiBox('Leak Rate',ar.toFixed(1),'%',ar>LKT?'#dc2626':'#16a34a');
    h+=kpiBox('Over '+LKT+'%',ov,'',ov>0?'#dc2626':'#16a34a');
    h+='</div>';
    var und=ls.length-ov;
    h+=chartRow(svgGauge('Fleet Leak Rate',ar,{size:140}),
        svgDonutChart('Threshold Compliance',[{label:'Under '+LKT+'%',value:und,color:'#16a34a'},{label:'Over '+LKT+'%',value:ov,color:'#dc2626'},{label:'Critical (>'+(LKT*1.5).toFixed(0)+'%)',value:cr,color:'#991b1b'}])
    );
    var ins=[];
    ins.push('Fleet leak rate: <strong>'+ar.toFixed(1)+'%</strong> across '+ls.length+' stores ('+(tc/1e6).toFixed(1)+'M lbs charge).');
    if(ar<=LKT) ins.push('Fleet is <strong>within threshold</strong> ('+LKT+'%).');else ins.push('<strong>Fleet exceeds '+LKT+'%</strong> \u2014 systemic issues.');
    if(ov>0) ins.push('<strong>'+ov+' stores over '+LKT+'%</strong> \u2014 prioritize repairs.');
    if(cr>0) ins.push('<strong>'+cr+' critically high</strong> (>'+(LKT*1.5).toFixed(0)+'%).');
    ins.push('<strong>'+tl.toLocaleString()+' leak events</strong>, '+(tq/1e3).toFixed(0)+'K lbs lost.');
    h+=insightBox(ins);
    // Top leakers
    var t15=ls.sort(function(a,b){return(b.cylr||0)-(a.cylr||0);}).slice(0,15);
    h+=sectionTitle('\ud83d\udea8','Top Leaking Stores');
    h+='<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
    h+='<th style="'+th()+'">Store</th><th style="'+th()+'">Location</th><th style="'+th()+'">Charge</th><th style="'+th()+'">Leaked</th><th style="'+th()+'">Rate</th><th style="'+th()+'">Events</th></tr></thead><tbody>';
    t15.forEach(function(s,i){var bg=i%2===0?'#f8fafc':'#fff';var rc=(s.cylr||0)>LKT?'color:#dc2626;font-weight:700;':'color:#16a34a;';h+='<tr style="background:'+bg+';">';h+='<td style="'+td()+'font-weight:600;">'+s.s+'</td>';h+='<td style="'+td()+'">'+(s.city||'')+', '+(s.st||'')+'</td>';h+='<td style="'+td()+'">'+Math.round(s.sc).toLocaleString()+'</td>';h+='<td style="'+td()+'color:#dc2626;">'+Math.round(s.cytq).toLocaleString()+'</td>';h+='<td style="'+td()+rc+'">'+(s.cylr||0).toFixed(1)+'%</td>';h+='<td style="'+td()+'">'+(s.cyl||0)+'</td></tr>';});
    h+='</tbody></table>';
    // Group
    var gk=level==='sr_director'?'fm':'rm',gl2=level==='sr_director'?'Director':'Regional Manager';
    var gm={};
    ls.forEach(function(x){var g=x[gk]||'Unknown';if(!gm[g])gm[g]={c:0,q:0,l:0,n:0,o:0};gm[g].c+=x.sc||0;gm[g].q+=x.cytq||0;gm[g].l+=x.cyl||0;gm[g].n++;if((x.cylr||0)>LKT)gm[g].o++;});
    var gls=Object.entries(gm).map(function(e){var n=e[0],d=e[1];return{name:n,stores:d.n,charge:d.c,qty:d.q,leaks:d.l,over:d.o,rate:d.c>0?d.q/d.c*100:0};}).sort(function(a,b){return a.rate-b.rate;});
    if(gls.length>1) {
        var lbd=gls.slice(0,15).map(function(g){return{label:g.name.substring(0,22),value:g.rate,color:g.rate>LKT?'#dc2626':'#16a34a'};});
        h+=svgBarChart('Leak Rate by '+gl2,lbd,{width:480,labelWidth:160,suffix:'%'});
        h+=sectionTitle('\ud83d\udcca','Leak Rate by '+gl2);
        h+='<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
        h+='<th style="'+th()+'">'+gl2+'</th><th style="'+th()+'">Stores</th><th style="'+th()+'">Charge</th><th style="'+th()+'">Leaked</th><th style="'+th()+'">Rate</th><th style="'+th()+'">Over '+LKT+'%</th></tr></thead><tbody>';
        gls.forEach(function(g,i){var bg=i%2===0?'#f8fafc':'#fff';var rc=g.rate>LKT?'color:#dc2626;font-weight:700;':'color:#16a34a;';h+='<tr style="background:'+bg+';">';h+='<td style="'+td()+'font-weight:600;">'+g.name+'</td>';h+='<td style="'+td()+'">'+g.stores+'</td>';h+='<td style="'+td()+'">'+Math.round(g.charge).toLocaleString()+'</td>';h+='<td style="'+td()+'">'+Math.round(g.qty).toLocaleString()+'</td>';h+='<td style="'+td()+rc+'">'+g.rate.toFixed(1)+'%</td>';h+='<td style="'+td()+(g.over>0?'color:#dc2626;':'')+'">'+g.over+'</td></tr>';});
        h+='</tbody></table>';
    }
    // Manager × Leak & Burn Rate matrix
    h+=buildLeakManagerMatrix(ls, level);
    return h;
}

/* ══════════ COMBINED EXECUTIVE SUMMARY ══════════ */
function buildCombinedPdf(stores,level,person,isAll) {
    var h='';
    // ---- TnT Section (condensed) ----
    var a30=safeAvg(stores,'twt_ref_30_day'),a7=safeAvg(stores,'twt_ref_7_day');
    var a90=safeAvg(stores,'twt_ref_90_day'),aH=safeAvg(stores,'twt_hvac_30_day');
    var loss=stores.reduce(function(s,d){return s+(d.total_loss||0);},0);
    var oot=stores.reduce(function(s,d){return s+(d.cases_out_of_target||0);},0);
    var b90=stores.filter(function(s){return s.twt_ref_30_day!=null&&s.twt_ref_30_day<90;}).length;
    var a90c=stores.filter(function(s){return s.twt_ref_30_day!=null&&s.twt_ref_30_day>=90;}).length;
    h+=sectionTitle('\ud83d\udcca','Refrigeration & HVAC Time in Target');
    h+='<div class="no-break">';
    h+='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:14px;">';
    h+=kpiBox('Ref 7d',a7,'%')+kpiBox('Ref 30d',a30,'%')+kpiBox('Ref 90d',a90,'%');
    h+=kpiBox('HVAC 30d',aH,'%')+kpiBox('<90%',b90,'',b90>0?'#dc2626':'#16a34a');
    h+='</div>';
    h+=chartRow(svgGauge('Ref 7-Day',a7),svgGauge('Ref 30-Day',a30),svgGauge('HVAC 30-Day',aH));
    h+='</div>';
    // Banner comparison in exec summary
    h+=bannerComparisonRow(stores);
    // Ops region breakout in exec summary
    h+=buildOpsRegionBreakout(stores);
    // 90-day trend in exec summary
    h+=buildHistTrend(stores, person);
    var tIns=[];
    var sp=splitByBanner(stores);
    var trend=a7>a30?'trending up':'trending down';
    tIns.push('Refrigeration '+trend+' (7d: '+a7.toFixed(1)+'% vs 30d: '+a30.toFixed(1)+'%). HVAC at '+aH.toFixed(1)+'%.');
    if (sp.wm.length>0&&sp.sams.length>0) {
        tIns.push('WM Ref 30d: <strong>'+safeAvg(sp.wm,'twt_ref_30_day').toFixed(1)+'%</strong> ('+sp.wm.length+') vs Sam\'s: <strong>'+safeAvg(sp.sams,'twt_ref_30_day').toFixed(1)+'%</strong> ('+sp.sams.length+').');
    }
    tIns.push(a90c+' of '+stores.length+' stores ('+(a90c/stores.length*100).toFixed(0)+'%) meeting 90% target. $'+(loss/1e6).toFixed(1)+'M estimated loss.');
    h+=insightBox(tIns);
    // RM breakout in exec summary (skip for Sr Director — Top/Bottom 5 below is sufficient)
    if(level!=='sr_director') {
        var rmExec=buildRmBreakout(stores,level);
        if(rmExec) h+=rmExec;
    }
    // Top/bottom performers bar
    var gBy=level==='sr_director'?'fm_sr_director_name':'fm_director_name';
    var cBy=level==='sr_director'?'fm_director_name':'fm_regional_manager_name';
    var grps=isAll?groupStores(stores,gBy):groupStores(stores,cBy);
    var gLbl=isAll?(level==='sr_director'?'Sr. Director':'Director'):(level==='sr_director'?'Director':'Regional Manager');
    var gcd=grps.slice(0,10).map(function(g){return{label:g.name.substring(0,22),value:g.avgRef30,color:g.avgRef30>=95?'#15803d':g.avgRef30>=90?'#16a34a':g.avgRef30>=85?'#65a30d':g.avgRef30>=80?'#d97706':'#dc2626'};});
    h+=svgBarChart('Ref 30-Day by '+gLbl,gcd,{width:480,labelWidth:160,max:100,suffix:'%'});

    // Bottom 10 + Top/Bottom Regionals (skip regionals for Sr Director)
    h+=buildBottom10Table(stores);
    if(level!=='sr_director') {
        h+=buildTopBottomRegionals(stores);
    }

    /* WTW and Leak sections */

    // ---- WTW Section (dashboard-style) ----
    if (typeof WTW_DATA!=='undefined') {
        var nums=new Set(stores.map(function(s){return String(s.store_number);}));
        var wos=WTW_DATA.filter(function(w){return nums.has(String(w.s));});
        var done=wos.filter(function(w){return w.st==='COMPLETED';});
        var opn=wos.length-done.length;
        var cpct=wos.length>0?(done.length/wos.length*100):0;
        var pmV=wos.filter(function(w){return w.pm!=null&&!isNaN(parseFloat(w.pm));});
        var pmA=pmV.length>0?pmV.reduce(function(s,w){return s+parseFloat(w.pm);},0)/pmV.length:0;
        if(isNaN(pmA))pmA=0;
        var p1=wos.filter(function(w){return w.ph==='PH1';}),p2=wos.filter(function(w){return w.ph==='PH2';}),p3=wos.filter(function(w){return w.ph==='PH3';});
        var p1d=p1.filter(function(w){return w.st==='COMPLETED';}).length;
        var p2d=p2.filter(function(w){return w.st==='COMPLETED';}).length;
        var p3d=p3.filter(function(w){return w.st==='COMPLETED';}).length;
        var p1p=p1.length>0?p1d/p1.length*100:0,p2p=p2.length>0?p2d/p2.length*100:0,p3p=p3.length>0?p3d/p3.length*100:0;
        var rdy=wos.filter(function(w){return w.st!=='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)>=90;}).length;
        var crit=wos.filter(function(w){return w.st==='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)<90;}).length;
        /* Gradient header like dashboard */
        h+='<div style="background:linear-gradient(135deg,#2563eb 0%,#06b6d4 100%);border-radius:12px;padding:18px 22px;margin:20px 0 14px;display:flex;justify-content:space-between;align-items:center;">';
        h+='<div><h2 style="font-size:17px;font-weight:800;color:#fff;margin:0;">\u2744\ufe0f Win the Winter FY26</h2>';
        h+='<p style="font-size:11px;color:rgba(255,255,255,0.8);margin:4px 0 0;">Preventive Maintenance Work Order Tracking</p></div>';
        h+='<div style="text-align:right;"><p style="font-size:24px;font-weight:800;color:#fff;margin:0;">'+wos.length.toLocaleString()+'</p>';
        h+='<p style="font-size:10px;color:rgba(255,255,255,0.8);margin:2px 0 0;">Total Work Orders</p></div></div>';
        h+='<div class="no-break">';
        /* Phase cards (matching dashboard style) */
        var phaseData=[
            {label:'All Phases',count:wos.length,done:done.length,open:opn,pct:cpct,bg:'#f8fafc',border:'#94a3b8',color:'#334155'},
            {label:'\ud83d\udfe6 Phase 1',count:p1.length,done:p1d,open:p1.length-p1d,pct:p1p,bg:'#eff6ff',border:'#60a5fa',color:'#1d4ed8'},
            {label:'\ud83d\udfe2 Phase 2',count:p2.length,done:p2d,open:p2.length-p2d,pct:p2p,bg:'#f0fdf4',border:'#4ade80',color:'#15803d'},
            {label:'\ud83d\udfe3 Phase 3',count:p3.length,done:p3d,open:p3.length-p3d,pct:p3p,bg:'#faf5ff',border:'#c084fc',color:'#7e22ce'}
        ];
        h+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;">';
        phaseData.forEach(function(ph){
            var donePct=ph.count>0?(ph.done/ph.count*100):0;
            var openPct=100-donePct;
            h+='<div style="background:'+ph.bg+';border:2px solid '+ph.border+';border-radius:10px;padding:12px;">';
            h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
            h+='<span style="font-size:12px;font-weight:700;color:'+ph.color+';">'+ph.label+'</span>';
            h+='<span style="font-size:16px;font-weight:800;color:'+ph.color+';">'+ph.count+'</span></div>';
            /* Status bar */
            h+='<div style="height:8px;border-radius:4px;overflow:hidden;display:flex;background:#e2e8f0;">';
            if(ph.done>0) h+='<div style="width:'+donePct+'%;background:#16a34a;"></div>';
            if(ph.open>0) h+='<div style="width:'+openPct+'%;background:#dc2626;"></div>';
            h+='</div>';
            h+='<div style="display:flex;justify-content:space-between;margin-top:5px;font-size:9px;color:#64748b;">';
            h+='<span>\u2713 '+ph.done+' done ('+donePct.toFixed(0)+'%)</span>';
            h+='<span>'+ph.open+' open</span></div>';
            h+='</div>';
        });
        h+='</div>';
        /* PM Readiness strip */
        h+='<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px;">';
        h+='<div style="background:#f0fdf4;border:2px solid #4ade80;border-radius:10px;padding:10px;text-align:center;">';
        h+='<div style="font-size:20px;font-weight:800;color:#16a34a;">'+rdy+'</div>';
        h+='<div style="font-size:9px;font-weight:600;color:#15803d;text-transform:uppercase;">\u2713 Ready to Close</div></div>';
        h+='<div style="background:#fefce8;border:2px solid #facc15;border-radius:10px;padding:10px;text-align:center;">';
        var rev=wos.filter(function(w){return w.st==='COMPLETED'&&w.pm!=null&&parseFloat(w.pm)>=90;}).length;
        h+='<div style="font-size:20px;font-weight:800;color:#a16207;">'+rev+'</div>';
        h+='<div style="font-size:9px;font-weight:600;color:#a16207;text-transform:uppercase;">\ud83d\udd0d Review Needed</div></div>';
        h+='<div style="background:#fef2f2;border:2px solid #f87171;border-radius:10px;padding:10px;text-align:center;">';
        h+='<div style="font-size:20px;font-weight:800;color:#dc2626;">'+crit+'</div>';
        h+='<div style="font-size:9px;font-weight:600;color:#dc2626;text-transform:uppercase;">\u26a0 Critical Reopen</div></div>';
        h+='</div>';
        /* Insights */
        var wIns=[];
        wIns.push('WTW at <strong>'+cpct.toFixed(1)+'%</strong> completion. '+opn+' WOs open, '+rdy+' ready to close.');
        if(crit>0) wIns.push('<strong>'+crit+' critical reopens</strong> needed (completed with PM <90%).');
        if(pmA>0) wIns.push('Average PM Score: <strong>'+pmA.toFixed(1)+'%</strong> across '+pmV.length+' scored WOs.');
        h+=insightBox(wIns);
        h+='</div>';
        h+=buildWtwManagerMatrix(wos, level);
    }

    // ---- Leak Section (condensed) ----
    if (typeof LK_STORES!=='undefined') {
        var nums2=new Set(stores.map(function(s){return String(s.store_number);}));
        var lks=LK_STORES.filter(function(s){return nums2.has(String(s.s));});
        var LKT=typeof LK_T!=='undefined'?LK_T:20;
        var tc2=lks.reduce(function(s,d){return s+(d.sc||0);},0);
        var tq2=lks.reduce(function(s,d){return s+(d.cytq||0);},0);
        var ar2=tc2>0?(tq2/tc2*100):0;
        var ov2=lks.filter(function(s){return(s.cylr||0)>LKT;}).length;
        h+=sectionTitle('\ud83e\uddca','Leak Management');
        h+='<div class="no-break">';
        h+='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:14px;">';
        h+=kpiBox('Stores',lks.length,'','#334155')+kpiBox('Charge',(tc2/1e6).toFixed(1)+'M lbs','','#334155');
        h+=kpiBox('Leaked',(tq2/1e3).toFixed(0)+'K lbs','','#dc2626');
        h+=kpiBox('Rate',ar2.toFixed(1),'%',ar2>LKT?'#dc2626':'#16a34a');
        h+=kpiBox('Over '+LKT+'%',ov2,'',ov2>0?'#dc2626':'#16a34a');
        h+='</div>';
        h+=chartRow(svgGauge('Leak Rate',ar2,{size:130}),
            svgDonutChart('Compliance',[{label:'Under '+LKT+'%',value:lks.length-ov2,color:'#16a34a'},{label:'Over '+LKT+'%',value:ov2,color:'#dc2626'}],{size:120}));
        var lIns=[];
        lIns.push('Fleet leak rate: <strong>'+ar2.toFixed(1)+'%</strong>'+(ar2<=LKT?' (within threshold).':' \u2014 exceeds '+LKT+'% threshold.'));
        if(ov2>0) lIns.push(ov2+' stores over threshold need priority repair.');
        h+=insightBox(lIns);
        h+='</div>'; /* close leak break-inside wrapper */
        h+=buildLeakManagerMatrix(lks, level);
    }
    return h;
}

/* ══════════ GENERATE PDF ══════════ */
async function generatePdf() {
    var level=document.getElementById('pdfViewLevel').value;
    var person=document.getElementById('pdfPersonSelect').value;
    var btn=document.getElementById('pdfGenerateBtn');
    btn.disabled=true;btn.textContent='\u23f3 Generating...';
    try {
        var content=buildPdfContent(pdfExportTab,level,person);
        var htmlStr=content.innerHTML;
        if(!htmlStr||htmlStr.length<50){alert('No data to export.');return;}
        var ls2=level==='sr_director'?'SrDir':'Dir';
        var ps=person==='__all__'?'All':person.replace(/[^a-zA-Z0-9]/g,'_').substring(0,20);
        var ts=pdfExportTab.toUpperCase();
        var ds=new Date().toISOString().slice(0,10);
        var fn=ts+'_'+ls2+'_'+ps+'_'+ds+'.pdf';
        var iframe=document.createElement('iframe');
        iframe.style.cssText='position:fixed;left:0;top:0;width:1200px;height:900px;opacity:0.01;z-index:-1;border:none;';
        document.body.appendChild(iframe);
        var idoc=iframe.contentDocument||iframe.contentWindow.document;
        idoc.open();
        idoc.write('<!DOCTYPE html><html><head><style>'
            +'*{margin:0;padding:0;box-sizing:border-box;}'
            +'body{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;background:#fff;color:#1e293b;padding:36px 40px;width:1100px;line-height:1.5;}'
            +'table{border-collapse:collapse;width:100%;}'
            +'.no-break{}'
            +'.page-break{break-before:page;page-break-before:always;}'
            +'h3{break-after:avoid;page-break-after:avoid;}'
            +'</style></head><body>'+htmlStr+'</body></html>');
        idoc.close();
        await new Promise(function(r){setTimeout(r,600);});
        var opt={margin:[0.3,0.3,0.3,0.3],filename:fn,image:{type:'jpeg',quality:0.95},
            html2canvas:{scale:2,useCORS:true,logging:false},
            jsPDF:{unit:'in',format:'letter',orientation:'landscape'},
            pagebreak:{mode:['css'],before:'.page-break',avoid:'.no-break'}};
        await html2pdf().set(opt).from(idoc.body).save();
        document.body.removeChild(iframe);
        closePdfModal();
    }catch(err){console.error('PDF failed:',err);alert('PDF generation failed: '+err.message);}
    finally{btn.disabled=false;btn.textContent='\ud83d\udcc4 Generate PDF';}
}
