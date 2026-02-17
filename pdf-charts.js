/**
 * PDF Chart Helpers — SVG gauges, bars, donuts, trend lines, style utilities.
 */

/* ══════════ SVG TREND LINE CHART (90-day) ══════════ */
function svgTrendChart(title, series, opts) {
    /* series: [{label, color, data:[{d:'2025-01-01',v:92.3},...]},...] */
    var o = opts || {};
    var W = o.width || 540, H = o.height || 180;
    var padL = 50, padR = 16, padT = 32, padB = 40;
    var cW = W - padL - padR, cH = H - padT - padB;
    /* Compute global min/max */
    var allV = [];
    series.forEach(function(s) { s.data.forEach(function(p) { allV.push(p.v); }); });
    if (allV.length === 0) return '';
    var vMin = Math.min.apply(null, allV), vMax = Math.max.apply(null, allV);
    var range = vMax - vMin;
    if (range < 2) { vMin -= 1; vMax += 1; range = vMax - vMin; }
    /* Collect all unique dates */
    var dateSet = {};
    series.forEach(function(s) { s.data.forEach(function(p) { dateSet[p.d] = 1; }); });
    var dates = Object.keys(dateSet).sort();
    var nDates = dates.length;
    if (nDates < 2) return '';
    var dateIdx = {};
    dates.forEach(function(d, i) { dateIdx[d] = i; });
    function xPos(d) { return padL + (dateIdx[d] / (nDates - 1)) * cW; }
    function yPos(v) { return padT + cH - ((v - vMin) / range) * cH; }
    var svg = '<svg width="'+W+'" height="'+H+'" xmlns="http://www.w3.org/2000/svg" style="break-inside:avoid;page-break-inside:avoid;">';
    /* Title */
    svg += '<text x="'+padL+'" y="18" font-size="13" font-weight="700" fill="#1e293b">'+title+'</text>';
    /* Grid lines + Y labels */
    var nGrid = 4;
    for (var g = 0; g <= nGrid; g++) {
        var gv = vMin + (range * g / nGrid);
        var gy = yPos(gv);
        svg += '<line x1="'+padL+'" y1="'+gy+'" x2="'+(W-padR)+'" y2="'+gy+'" stroke="#e2e8f0" stroke-width="1"/>';
        svg += '<text x="'+(padL-6)+'" y="'+(gy+4)+'" text-anchor="end" font-size="10" fill="#94a3b8">'+gv.toFixed(1)+'</text>';
    }
    /* 90% target line */
    if (vMin < 90 && vMax > 85) {
        var ty = yPos(90);
        svg += '<line x1="'+padL+'" y1="'+ty+'" x2="'+(W-padR)+'" y2="'+ty+'" stroke="#dc2626" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>';
        svg += '<text x="'+(W-padR-2)+'" y="'+(ty-4)+'" text-anchor="end" font-size="9" fill="#dc2626" opacity="0.7">90% target</text>';
    }
    /* X-axis labels (show ~6 dates) */
    var step = Math.max(1, Math.floor(nDates / 6));
    for (var xi = 0; xi < nDates; xi += step) {
        var xp = xPos(dates[xi]);
        var lbl = dates[xi].substring(5); /* MM-DD */
        svg += '<text x="'+xp+'" y="'+(H-6)+'" text-anchor="middle" font-size="9" fill="#94a3b8">'+lbl+'</text>';
    }
    /* Draw lines */
    series.forEach(function(s) {
        if (s.data.length < 2) return;
        var sorted = s.data.slice().sort(function(a,b) { return a.d < b.d ? -1 : 1; });
        var pts = sorted.map(function(p) { return xPos(p.d)+','+yPos(p.v); });
        svg += '<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+s.color+'" stroke-width="2" stroke-linejoin="round"/>';
    });
    /* Legend */
    var lx = padL + 10;
    series.forEach(function(s, idx) {
        var ly = padT + 6 + idx * 14;
        svg += '<rect x="'+lx+'" y="'+(ly-6)+'" width="12" height="3" rx="1" fill="'+s.color+'"/>';
        svg += '<text x="'+(lx+16)+'" y="'+ly+'" font-size="10" fill="#475569">'+s.label+'</text>';
    });
    svg += '</svg>';
    return '<div style="break-inside:avoid;page-break-inside:avoid;margin:12px 0;">'+svg+'</div>';
}

/* Build 90-day trend for a set of stores */
function buildHistTrend(stores, dirName) {
    if (typeof HIST_TIT === 'undefined') return '';
    /* Filter HIST_TIT to this director */
    var dirData = HIST_TIT.filter(function(h) { return h.dir === dirName; });
    if (dirData.length === 0) return '';
    /* Build combined + per-banner series */
    var byDate = {};
    dirData.forEach(function(h) {
        if (!byDate[h.d]) byDate[h.d] = { sum: 0, cnt: 0, wSum: 0, wCnt: 0, sSum: 0, sCnt: 0 };
        byDate[h.d].sum += h.t * h.n;
        byDate[h.d].cnt += h.n;
        if (h.bn === 'W') { byDate[h.d].wSum += h.t * h.n; byDate[h.d].wCnt += h.n; }
        else { byDate[h.d].sSum += h.t * h.n; byDate[h.d].sCnt += h.n; }
    });
    var combined = [], wm = [], sams = [];
    Object.keys(byDate).sort().forEach(function(d) {
        var b = byDate[d];
        if (b.cnt > 0) combined.push({ d: d, v: b.sum / b.cnt });
        if (b.wCnt > 0) wm.push({ d: d, v: b.wSum / b.wCnt });
        if (b.sCnt > 0) sams.push({ d: d, v: b.sSum / b.sCnt });
    });
    var chartSeries = [{ label: 'Combined', color: '#334155', data: combined }];
    if (wm.length > 5) chartSeries.push({ label: 'Walmart', color: '#0053e2', data: wm });
    if (sams.length > 5) chartSeries.push({ label: "Sam's", color: '#16a34a', data: sams });
    var h = svgTrendChart('90-Day TIT Trend — ' + dirName, chartSeries);
    /* Also build realty ops region trend if available */
    if (typeof HIST_ROR !== 'undefined') {
        var rorData = HIST_ROR.filter(function(r) { return r.dir === dirName; });
        var rorRegions = {};
        rorData.forEach(function(r) {
            if (!rorRegions[r.r]) rorRegions[r.r] = [];
            rorRegions[r.r].push({ d: r.d, v: r.t });
        });
        var regionIds = Object.keys(rorRegions).filter(function(r) { return rorRegions[r].length >= 10; });
        if (regionIds.length > 1) {
            var rorColors = ['#7c3aed', '#0891b2', '#c2410c', '#4f46e5', '#059669'];
            var rorSeries = regionIds.map(function(rid, i) {
                return { label: 'Region ' + rid, color: rorColors[i % rorColors.length], data: rorRegions[rid] };
            });
            h += svgTrendChart('90-Day TIT by Ops Realty Region', rorSeries);
        }
    }
    return h;
}

var S = {
    th: 'padding:10px 12px;text-align:left;font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;',
    td: 'padding:9px 12px;border-bottom:1px solid #e2e8f0;font-size:11px;',
    hdr: 'background:linear-gradient(135deg,#0053e2 0%,#003da5 100%);color:#fff;',
    card: 'border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;text-align:center;background:linear-gradient(180deg,#fff 0%,#f8fafc 100%);box-shadow:0 1px 3px rgba(0,0,0,0.06);break-inside:avoid;page-break-inside:avoid;',
    section: 'font-size:15px;font-weight:800;margin:28px 0 12px;color:#0053e2;padding-bottom:8px;border-bottom:3px solid #0053e2;display:flex;align-items:center;gap:8px;break-after:avoid;page-break-after:avoid;',
    page: 'width:1100px;padding:40px 44px;font-family:"Segoe UI",system-ui,-apple-system,sans-serif;background:#fff;color:#1e293b;line-height:1.6;'
};
function th(){return S.th;} function td(){return S.td;}
function pct(v){return v!=null?parseFloat(v).toFixed(1)+'%':'N/A';}
function scoreColor(v) {
    if (v==null) return 'color:#94a3b8;';
    if (v>=95) return 'color:#15803d;font-weight:700;';  /* dark green — excellent */
    if (v>=90) return 'color:#16a34a;font-weight:700;';  /* green — target met */
    if (v>=85) return 'color:#65a30d;font-weight:600;';  /* lime/light green — close */
    if (v>=80) return 'color:#d97706;font-weight:600;';  /* amber — needs attention */
    if (v>=70) return 'color:#ea580c;font-weight:600;';  /* orange — concerning */
    return 'color:#dc2626;font-weight:700;';              /* red — critical */
}
function kpiBox(label, value, suffix, color) {
    var pv=parseFloat(value);
    var c = color || (pv>=95?'#15803d':pv>=90?'#16a34a':pv>=85?'#65a30d':pv>=80?'#d97706':pv>=70?'#ea580c':'#dc2626');
    var dv = typeof value==='number' ? (Number.isInteger(value)||value>999?value.toLocaleString():value.toFixed(1)) : value;
    return '<div style="'+S.card+'">'
        +'<div style="font-size:26px;font-weight:800;color:'+c+';line-height:1.1;letter-spacing:-0.5px;">'+dv+(suffix||'')+'</div>'
        +'<div style="font-size:10px;color:#64748b;margin-top:8px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">'+label+'</div></div>';
}
function safeAvg(data,field) {
    var v=data.filter(function(d){return d[field]!=null&&!isNaN(d[field]);});
    return v.length?v.reduce(function(s,d){return s+parseFloat(d[field]);},0)/v.length:0;
}
function insightBox(items) {
    return '<div style="background:linear-gradient(135deg,#eff6ff 0%,#f0f9ff 100%);border:1px solid #93c5fd;border-left:4px solid #0053e2;border-radius:10px;padding:20px 22px;margin:20px 0;break-inside:avoid;page-break-inside:avoid;">'
        +'<div style="font-size:13px;font-weight:800;color:#0053e2;margin-bottom:12px;display:flex;align-items:center;gap:6px;">💡 Key Insights & Action Items</div>'
        +'<ul style="margin:0;padding-left:20px;font-size:11.5px;color:#1e40af;line-height:2;">'
        +items.map(function(i){return '<li style="margin-bottom:2px;">'+i+'</li>';}).join('')
        +'</ul></div>';
}
function sectionTitle(icon,text) {
    return '<h3 style="'+S.section+'"><span style="font-size:18px;">'+icon+'</span> '+text+'</h3>';
}
function divider() {
    return '<div style="border-top:3px solid #0053e2;margin:32px 0 24px;opacity:0.15;"></div>';
}


/* ══════════ SVG CHART HELPERS ══════════ */
function svgBarChart(title,data,opts) {
    opts=opts||{};
    var W=opts.width||520,barH=opts.barHeight||24,gap=5,labelW=opts.labelWidth||140;
    var maxVal=opts.max||Math.max.apply(null,data.map(function(d){return d.value;}))||1;
    var chartW=W-labelW-65;
    var H=data.length*(barH+gap)+32;
    var svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+W+'" height="'+H+'" style="font-family:Segoe UI,system-ui,sans-serif;">';
    if (title) svg+='<text x="0" y="15" font-size="12" font-weight="700" fill="#334155">'+title+'</text>';
    var y0=title?28:6;
    data.forEach(function(d,i) {
        var y=y0+i*(barH+gap);
        var barW=Math.max(3,(d.value/maxVal)*chartW);
        var c=d.color||'#0053e2';
        svg+='<text x="'+(labelW-6)+'" y="'+(y+barH/2+4)+'" font-size="10" fill="#475569" text-anchor="end">'+d.label+'</text>';
        svg+='<rect x="'+labelW+'" y="'+y+'" width="'+chartW+'" height="'+barH+'" rx="4" fill="#f1f5f9"/>';
        svg+='<rect x="'+labelW+'" y="'+y+'" width="'+barW+'" height="'+barH+'" rx="4" fill="'+c+'"/>';
        var valStr=opts.suffix==='%'?d.value.toFixed(1)+'%':d.value.toLocaleString();
        var tx=barW>55?(labelW+barW-6):(labelW+barW+6);
        var ta=barW>55?'end':'start';
        var tc=barW>55?'#fff':'#334155';
        svg+='<text x="'+tx+'" y="'+(y+barH/2+4)+'" font-size="10" font-weight="600" fill="'+tc+'" text-anchor="'+ta+'">'+valStr+'</text>';
    });
    svg+='</svg>';
    return '<div style="margin:8px 0;">'+svg+'</div>';
}
function svgDonutChart(title,data,opts) {
    opts=opts||{};
    var size=opts.size||150,r=size*0.35,stroke=opts.stroke||22;
    var cx=size/2,cy=size/2;
    var total=data.reduce(function(s,d){return s+d.value;},0)||1;
    var W=size+210,H=Math.max(size,data.length*24+30);
    var svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+W+'" height="'+H+'" style="font-family:Segoe UI,system-ui,sans-serif;">';
    if (title) svg+='<text x="0" y="14" font-size="12" font-weight="700" fill="#334155">'+title+'</text>';
    var offy=title?20:0;
    svg+='<text x="'+cx+'" y="'+(cy+offy-4)+'" font-size="20" font-weight="800" fill="#1e293b" text-anchor="middle">'+total.toLocaleString()+'</text>';
    svg+='<text x="'+cx+'" y="'+(cy+offy+12)+'" font-size="9" fill="#94a3b8" text-anchor="middle">Total</text>';
    var cumAngle=-90;
    data.forEach(function(d) {
        var angle=(d.value/total)*360;
        if (angle<0.5){cumAngle+=angle;return;}
        var s1=cumAngle*Math.PI/180,s2=(cumAngle+angle)*Math.PI/180;
        var x1=cx+r*Math.cos(s1),y1=(cy+offy)+r*Math.sin(s1);
        var x2=cx+r*Math.cos(s2),y2=(cy+offy)+r*Math.sin(s2);
        svg+='<path d="M '+x1+' '+y1+' A '+r+' '+r+' 0 '+(angle>180?1:0)+' 1 '+x2+' '+y2+'" fill="none" stroke="'+d.color+'" stroke-width="'+stroke+'"/>';
        cumAngle+=angle;
    });
    var lx=size+16,ly=offy+12;
    data.forEach(function(d,i) {
        var y=ly+i*24;
        svg+='<rect x="'+lx+'" y="'+(y-8)+'" width="14" height="14" rx="3" fill="'+d.color+'"/>';
        svg+='<text x="'+(lx+20)+'" y="'+(y+3)+'" font-size="10" font-weight="600" fill="#334155">'+d.label+'</text>';
        svg+='<text x="'+(lx+20)+'" y="'+(y+16)+'" font-size="9" fill="#64748b">'+d.value.toLocaleString()+' ('+(d.value/total*100).toFixed(1)+'%)</text>';
    });
    svg+='</svg>';
    return '<div style="margin:4px 0;">'+svg+'</div>';
}
function svgGauge(label,value,opts) {
    opts=opts||{};
    var size=opts.size||130,stroke=18;
    var r=size*0.35,cx=size/2,cy=size*0.55;
    var color=value>=95?'#15803d':value>=90?'#16a34a':value>=85?'#65a30d':value>=80?'#d97706':'#dc2626';
    var angle=Math.min(180,value/100*180);
    var sR=Math.PI,eR=Math.PI-(angle*Math.PI/180);
    var x1=cx+r*Math.cos(sR),y1=cy+r*Math.sin(sR);
    var x2=cx+r*Math.cos(eR),y2=cy+r*Math.sin(eR);
    var svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+size+'" height="'+(size*0.72)+'" style="font-family:Segoe UI,system-ui,sans-serif;">';
    svg+='<path d="M '+(cx-r)+' '+cy+' A '+r+' '+r+' 0 0 1 '+(cx+r)+' '+cy+'" fill="none" stroke="#e2e8f0" stroke-width="'+stroke+'" stroke-linecap="round"/>';
    if (angle>0.5)
        svg+='<path d="M '+x1+' '+y1+' A '+r+' '+r+' 0 '+(angle>90?1:0)+' 1 '+x2+' '+y2+'" fill="none" stroke="'+color+'" stroke-width="'+stroke+'" stroke-linecap="round"/>';
    svg+='<text x="'+cx+'" y="'+(cy-2)+'" font-size="20" font-weight="800" fill="'+color+'" text-anchor="middle">'+value.toFixed(1)+'%</text>';
    svg+='<text x="'+cx+'" y="'+(cy+14)+'" font-size="9" fill="#64748b" text-anchor="middle">'+label+'</text>';
    svg+='</svg>';
    return svg;
}
function chartRow() {
    var charts=Array.prototype.slice.call(arguments);
    return '<div style="display:flex;gap:20px;margin:14px 0;align-items:flex-start;flex-wrap:wrap;break-inside:avoid;page-break-inside:avoid;">'+charts.join('')+'</div>';
}

/* ══════════ GROUP STORES (descending — best on top) ══════════ */
function groupStores(stores,groupBy) {
    var map={};
    stores.forEach(function(s){var k=s[groupBy]||'Unknown';if(!map[k])map[k]=[];map[k].push(s);});
    return Object.entries(map).map(function(e){
        var name=e[0],ss=e[1];
        return {name:name,count:ss.length,avgRef30:safeAvg(ss,'twt_ref_30_day'),avgHvac30:safeAvg(ss,'twt_hvac_30_day'),
            totalLoss:ss.reduce(function(s,d){return s+(d.total_loss||0);},0),
            casesOOT:ss.reduce(function(s,d){return s+(d.cases_out_of_target||0);},0)};
    }).sort(function(a,b){return b.avgRef30-a.avgRef30;});
}
function buildGroupTable(groups,label) {
    var html=sectionTitle('\ud83d\udcca','Performance by '+label);
    html+='<table style="width:100%;border-collapse:collapse;font-size:11px;border-radius:8px;overflow:hidden;"><thead><tr style="'+S.hdr+'">';
    html+='<th style="'+th()+'">'+label+'</th><th style="'+th()+'">Stores</th>';
    html+='<th style="'+th()+'">Ref 30d</th><th style="'+th()+'">HVAC 30d</th>';
    html+='<th style="'+th()+'">Total Loss</th><th style="'+th()+'">Cases OOT</th></tr></thead><tbody>';
    groups.forEach(function(g,i) {
        var bg=i%2===0?'#f8fafc':'#fff';
        html+='<tr style="background:'+bg+';">';
        html+='<td style="'+td()+'font-weight:600;">'+g.name+'</td>';
        html+='<td style="'+td()+'">'+g.count+'</td>';
        html+='<td style="'+td()+scoreColor(g.avgRef30)+'">'+g.avgRef30.toFixed(1)+'%</td>';
        html+='<td style="'+td()+scoreColor(g.avgHvac30)+'">'+g.avgHvac30.toFixed(1)+'%</td>';
        html+='<td style="'+td()+'color:#dc2626;">$'+g.totalLoss.toLocaleString(undefined,{maximumFractionDigits:0})+'</td>';
        html+='<td style="'+td()+'">'+g.casesOOT.toLocaleString()+'</td></tr>';
    });
    html+='</tbody></table>';
    return html;
}

