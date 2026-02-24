#!/usr/bin/env python3
"""Build Capital Projects dashboard from LX (BQ) + Wrike data.

Primary source: lx_all_projects_curr (BQ) — 1,850+ active North BU mech projects
Secondary source: Wrike API — ZE flags, POC contacts
Org alignment: store_tabular_view (BQ) — current director/RM/FSM

Usage:
  python3 build_projects.py              # Pull fresh from BQ + Wrike API, build HTML
  python3 build_projects.py --local      # Build from cached JSON files
  python3 build_projects.py --bq-only    # Pull BQ only (skip Wrike), build HTML
"""
import json, re, subprocess, sys, os
from datetime import datetime, date
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)

PROXY = 'http://sysproxy.wal-mart.com:8080'
WRIKE_FOLDER = 'IEAFB7T7I5CT6NKV'

# ── Wrike custom field mapping ─────────────────────────────────────────
CF = {
    'IEAFB7T7JUADF3LD': 'store_nbr',
    'IEAFB7T7JUADF3LF': 'store_type',
    'IEAFB7T7JUADF3LG': 'address',
    'IEAFB7T7JUADF3LI': 'city',
    'IEAFB7T7JUADF3LM': 'state',
    'IEAFB7T7JUAEM6J6': 'business_unit',
    'IEAFB7T7JUADF3M7': 'general_contractor',
    'IEAFB7T7JUADF3ON': 'project_type',
    'IEAFB7T7JUADF3OX': 'scope_of_work',
    'IEAFB7T7JUADF3OM': 'project_year',
    'IEAFB7T7JUADF3OV': 'sap_number',
    'IEAFB7T7JUADF3OW': 'sequence_number',
    'IEAFB7T7JUADAIED': 'reporting_type',
    'IEAFB7T7JUADF3OO': 'project_status_wrike',
    'IEAFB7T7JUADF3OU': 'project_phase',
    'IEAFB7T7JUADF3MB': 'wrike_sr_director',
    'IEAFB7T7JUADGKEL': 'wrike_director',
    'IEAFB7T7JUADF3MD': 'wrike_rm',
    'IEAFB7T7JUADF3MM': 'wrike_fsm',
    'IEAFB7T7JUADF3MP': 'wrike_tech_name',
    'IEAFB7T7JUADF3MS': 'wrike_tech_phone',
    'IEAFB7T7JUAEMQIN': 'market_mgr_name',
    'IEAFB7T7JUAEMQIT': 'market_mgr_email',
    'IEAFB7T7JUADHMEI': 'store_mgr_name',
    'IEAFB7T7JUADHMEJ': 'store_mgr_phone',
    'IEAFB7T7JUADF3LS': 'mc_pm_name',
    'IEAFB7T7JUADF3LT': 'mc_pm_phone',
    'IEAFB7T7JUADF3LV': 'mc_mcm_name',
    'IEAFB7T7JUADF3LX': 'mc_mcm_phone',
    'IEAFB7T7JUADF3MV': 'engineer_company',
    'IEAFB7T7JUADF3MY': 'engineer_name',
}


def bq_query(sql):
    """Run a BQ query and return parsed JSON rows."""
    r = subprocess.run([
        'bq', 'query', '--use_legacy_sql=false', '--format=json',
        '--max_rows=5000', '--project_id=re-crystal-mdm-prod', sql
    ], capture_output=True, text=True, timeout=60)
    match = re.search(r'(\[.*\])', r.stdout, re.DOTALL)
    if not match:
        print(f'  BQ query failed: {r.stdout[-300:]}')
        return []
    return json.loads(match.group(1))


def pull_lx_projects():
    """Pull active mechanical construction projects for North BU from LX."""
    sql = """
    WITH north_stores AS (
      SELECT store_number, store_name, fm_sr_director_name, fm_director_name,
             fm_regional_manager_name, fs_manager_name, CAST(fs_market AS STRING) as market, banner_desc
      FROM `re-crystal-mdm-prod.crystal.store_tabular_view`
      WHERE fm_sr_director_name IN ('Laura Moore','Nick Paladino','Whitney Box','Monique Brennan','B.A. Glass')
    )
    SELECT
      l.ProjectID as project_id,
      l.Store_Nbr as store_nbr,
      n.store_name,
      l.Project_Name as project_name,
      l.Project_Type as project_type,
      l.ProjectStatus as status,
      l.ProjectPhase as phase,
      l.MechanicalPhase as mech_phase,
      CAST(l.Program_Year AS STRING) as program_year,
      l.Sequence_Number as sequence_nbr,
      l.SAPProjectDefinition as sap_project,
      l.Brief_Scope_Of_Work as scope_of_work,
      l.State as state,
      l.City as city,
      CAST(l.ConstructionStart_Projected AS STRING) as const_start_proj,
      CAST(l.ConstructionStart_Actual AS STRING) as const_start_actual,
      CAST(l.ConstructionComplete_Projected AS STRING) as const_end_proj,
      CAST(l.ConstructionComplete_Actual AS STRING) as const_end_actual,
      l.GeneralContractor as gc_contact,
      l.GeneralContractor_Firm as gc_firm,
      l.MechanicalContractor as mech_contractor,
      l.MechanicalContractor_Firm as mech_firm,
      l.MechanicalConstructionDirector as mc_director,
      l.MechanicalConstructionSrManager as mc_sr_mgr,
      l.MechanicalSrProjectManager as mc_sr_pm,
      l.ConstructionManagerMechanical as cmm,
      l.PMOProjectManager as pmo_pm,
      l.PMOSrProjectManager as pmo_sr_pm,
      n.fm_sr_director_name as sr_director,
      n.fm_director_name as director,
      n.fm_regional_manager_name as rm,
      n.fs_manager_name as fsm,
      n.market,
      n.banner_desc as banner,
      l.HVACInstallationBudget as hvac_budget,
      l.RefrigerationInstallationBudget as ref_budget,
      l.WorkingBudget_Total as total_budget
    FROM `re-ods-prod.us_re_ods_prod_pub.lx_all_projects_curr` l
    JOIN north_stores n ON l.Store_Nbr = n.store_number
    WHERE (
        (l.Portfolio = 'Stores - Mechanical Construction'
         AND l.ProjectStatus IN ('Active','Due Diligence','Design Development','Financial Closeout'))
        OR
        (l.Project_Type = 'ZERO EMISSIONS'
         AND l.ProjectStatus NOT IN ('Dropped','Cancelled','Canceled'))
      )
    ORDER BY n.fm_director_name, l.Store_Nbr
    """
    rows = bq_query(sql)
    print(f'  LX: {len(rows)} active mech projects (North BU)')
    with open('lx_projects.json', 'w') as f:
        json.dump(rows, f, indent=2)
    return rows


def pull_wrike():
    """Pull projects from Wrike API."""
    with open('.wrike_tokens.json') as f:
        token = json.load(f)['access_token']
    headers = f'Authorization: Bearer {token}'
    r = subprocess.run(['curl', '-s', '--proxy', PROXY,
        '-H', headers, f'https://www.wrike.com/api/v4/folders/{WRIKE_FOLDER}'
    ], capture_output=True, text=True)
    children = json.loads(r.stdout)['data'][0]['childIds']
    r = subprocess.run(['curl', '-s', '--proxy', PROXY,
        '-H', headers, 'https://www.wrike.com/api/v4/workflows'
    ], capture_output=True, text=True)
    status_map = {}
    for wf in json.loads(r.stdout).get('data', []):
        for cs in wf.get('customStatuses', []):
            status_map[cs['id']] = {'name': cs.get('name', '?'), 'group': cs.get('group', '?')}
    all_projects = []
    for i in range(0, len(children), 100):
        batch = ','.join(children[i:i+100])
        r = subprocess.run(['curl', '-s', '--proxy', PROXY,
            '-H', headers,
            f'https://www.wrike.com/api/v4/folders/{batch}?fields=%5B%22customColumnIds%22%5D'
        ], capture_output=True, text=True)
        data = json.loads(r.stdout)
        all_projects.extend(data.get('data', []))
    records = []
    for p in all_projects:
        proj = p.get('project', {})
        sid = proj.get('customStatusId', '')
        si = status_map.get(sid, {})
        rec = {
            'id': p['id'], 'title': p.get('title', ''),
            'status': si.get('name', '?'), 'status_group': si.get('group', '?'),
            'start_date': proj.get('startDate', ''), 'end_date': proj.get('endDate', ''),
        }
        for cf in p.get('customFields', []):
            fname = CF.get(cf['id'])
            if fname:
                rec[fname] = cf.get('value', '')
        records.append(rec)
    with open('wrike_projects.json', 'w') as f:
        json.dump(records, f, indent=2)
    print(f'  Wrike: {len(records)} projects pulled')
    return records


def clean(val):
    """Clean !Unknown and junk values."""
    if not val:
        return ''
    s = str(val).strip()
    if s in ('!Unknown', 'NULL', 'None', 'null', 'x', '*', '**', 'NA', 'N/A', 'TBD'):
        return ''
    return s


def clean_date(val):
    """Clean dates — suppress 9999, 1899, and other bogus years."""
    if not val:
        return ''
    s = str(val).strip()[:10]
    if s.startswith('9999') or s.startswith('1899') or s.startswith('0001'):
        return ''
    return s


def pull_walkoff_forms():
    """Pull FS Walk-Off Reports and Rack Verification Pre-Project Forms from Wrike."""
    with open('.wrike_tokens.json') as f:
        token = json.load(f)['access_token']
    headers = f'Authorization: Bearer {token}'
    # Get workflow statuses
    r = subprocess.run(['curl', '-s', '--proxy', PROXY, '-H', headers,
        'https://www.wrike.com/api/v4/workflows'], capture_output=True, text=True)
    status_map = {}
    for wf in json.loads(r.stdout).get('data', []):
        for cs in wf.get('customStatuses', []):
            status_map[cs['id']] = {'name': cs.get('name', ''), 'group': cs.get('group', '')}
    # Search all FS tasks
    r = subprocess.run(['curl', '-s', '--proxy', PROXY, '-H', headers,
        'https://www.wrike.com/api/v4/tasks?title=Facilities%20Services&pageSize=1000'],
        capture_output=True, text=True)
    tasks = json.loads(r.stdout).get('data', [])
    walkoffs, prewalks = {}, {}
    for t in tasks:
        title = t.get('title', '')
        m = re.search(r'\[\s*0*(\d{1,5})[\.\-\]\s]', title)
        store = m.group(1) if m and int(m.group(1)) > 1 else ''
        if not store:
            continue
        sid = t.get('customStatusId', '')
        si = status_map.get(sid, {})
        rec = {
            'status': si.get('name', '') or t.get('status', ''),
            'group': si.get('group', t.get('status', '')),
            'due': t.get('dates', {}).get('due', ''),
            'completed': t.get('completedDate', ''),
            'link': t.get('permalink', ''),
        }
        if 'Walk-Off' in title:
            walkoffs[store] = rec
        elif 'Pre-Project' in title or 'Rack Verification' in title:
            prewalks[store] = rec
    print(f'  Wrike: {len(walkoffs)} walk-offs, {len(prewalks)} pre-project forms')
    result = {'walkoffs': walkoffs, 'prewalks': prewalks}
    with open('walkoff_data.json', 'w') as f:
        json.dump(result, f, indent=2)
    return result


def enrich(lx_rows, wrike_projects=None, walkoff_data=None):
    """Build enriched project list from LX + Wrike."""
    # Build Wrike lookup by store number
    wrike_by_store = {}
    ze_stores = set()
    if wrike_projects:
        for p in wrike_projects:
            s = p.get('store_nbr', '').strip().lstrip('0')
            s = re.split(r'[-.]', s)[0]
            if s.isdigit():
                wrike_by_store.setdefault(s, []).append(p)
                title = p.get('title', '').upper()
                if 'ZERO' in title or 'ZE' in p.get('project_type', '').upper():
                    ze_stores.add(s)

    # Walk-off / pre-project form lookups
    wo_map = (walkoff_data or {}).get('walkoffs', {})
    pw_map = (walkoff_data or {}).get('prewalks', {})

    projects = []
    for r in lx_rows:
        store = str(r.get('store_nbr', ''))

        # Classify type
        pt = (r.get('project_type', '') or '').upper()
        if pt == 'ZERO EMISSIONS':
            type_cat = 'ZE'
        elif 'HVAC' in pt:
            type_cat = 'HVAC'
        elif 'REF' in pt:
            type_cat = 'REF'
        elif 'EMS' in pt:
            type_cat = 'EMS'
        elif 'COMBO' in pt:
            type_cat = 'COMBO'
        elif 'SP' in pt:
            type_cat = 'SP'
        elif 'BAS' in pt:
            type_cat = 'BAS'
        else:
            type_cat = 'OTHER'

        # ZE flag from LX project_type OR Wrike title
        is_ze = (pt == 'ZERO EMISSIONS') or (store in ze_stores)

        # Mechanical phase → dashboard category
        mph = clean(r.get('mech_phase', ''))
        if mph == 'Construction':
            dash_status = 'In Construction'
        elif mph == 'Pre-Construction':
            dash_status = 'Pre-Construction'
        elif mph in ('Design', 'OTB', 'Award'):
            dash_status = 'Design / Bidding'
        elif mph == 'Post-Construction':
            dash_status = 'Post-Construction'
        elif mph == 'Complete':
            dash_status = 'Complete'
        else:
            dash_status = 'Active'  # fallback for NULL mech_phase

        # Dates
        start = clean_date(r.get('const_start_actual') or r.get('const_start_proj'))
        end_proj = clean_date(r.get('const_end_proj'))
        end_actual = clean_date(r.get('const_end_actual'))

        # Overdue check
        overdue = False
        if end_proj and dash_status not in ('Complete', 'Post-Construction'):
            try:
                due = datetime.strptime(end_proj, '%Y-%m-%d').date()
                overdue = due < date.today()
            except:
                pass

        # Wrike POC enrichment — MCM + PM with phone numbers
        wm = wrike_by_store.get(store, [None])[0] or {}
        # MCM: prefer Wrike (has phone), fallback to LX mc_sr_mgr
        mcm_name = clean(wm.get('mc_mcm_name', '')) or clean(r.get('mc_sr_mgr', ''))
        mcm_phone = clean(wm.get('mc_mcm_phone', ''))
        # PM: from Wrike
        pm_name = clean(wm.get('mc_pm_name', ''))
        pm_phone = clean(wm.get('mc_pm_phone', ''))

        # Mech contractor — use firm name, fallback to person
        mc_display = clean(r.get('mech_firm', '')) or clean(r.get('mech_contractor', ''))
        # Clean doubled names like "CoolSys Commercial & Industrial Solutions IncCoolSys Commercial"
        if mc_display and len(mc_display) > 30:
            half = len(mc_display) // 2
            if mc_display[:half-5] in mc_display[half:]:
                mc_display = mc_display[:half].strip()

        projects.append({
            'store': store,
            'store_name': clean(r.get('store_name', '')),
            'name': r.get('project_name', ''),
            'type': r.get('project_type', ''),
            'type_cat': type_cat,
            'is_ze': is_ze,
            'status': dash_status,
            'mech_phase': mph,
            'lx_status': r.get('status', ''),
            'year': r.get('program_year', ''),
            'seq': r.get('sequence_nbr', ''),
            'sap': clean(r.get('sap_project', '')),
            'scope': r.get('scope_of_work', '') or '',
            'state': r.get('state', ''),
            'city': r.get('city', ''),
            'start': start,
            'end': end_proj,
            'end_actual': end_actual,
            'overdue': overdue,
            'mech_contractor': mc_display,
            'mc_director': clean(r.get('mc_director', '')),
            'mcm_name': mcm_name,
            'mcm_phone': mcm_phone,
            'pm_name': pm_name,
            'pm_phone': pm_phone,
            'mc_sr_pm': clean(r.get('mc_sr_pm', '')),
            'cmm': clean(r.get('cmm', '')),
            'pmo_pm': clean(r.get('pmo_pm', '')),
            'sr_director': r.get('sr_director', ''),
            'director': r.get('director', ''),
            'rm': r.get('rm', ''),
            'fsm': r.get('fsm', ''),
            'market': r.get('market', ''),
            'banner': r.get('banner', ''),
            'budget': r.get('total_budget', ''),
            # Walk-off / Pre-project forms
            'wo_status': wo_map.get(store, {}).get('status', ''),
            'wo_link': wo_map.get(store, {}).get('link', ''),
            'pw_status': pw_map.get(store, {}).get('status', ''),
            'pw_link': pw_map.get(store, {}).get('link', ''),
        })

    return projects


def build_html(projects):
    """Generate the dashboard HTML."""
    now = datetime.now().strftime('%b %d, %Y %I:%M %p')

    # Gather unique values for filters
    directors = sorted(set(p['director'] for p in projects if p.get('director')))
    sr_directors = sorted(set(p['sr_director'] for p in projects if p.get('sr_director')))
    rms = sorted(set(p['rm'] for p in projects if p.get('rm')))
    states = sorted(set(p['state'] for p in projects if p.get('state')))
    statuses = ['In Construction', 'Pre-Construction', 'Design / Bidding', 'Active', 'Post-Construction', 'Complete']
    years = sorted(set(p['year'] for p in projects if p.get('year')))

    # Build compact JSON
    data = []
    for p in projects:
        data.append({
            's': p['store'], 'n': p['name'], 'sn': p['store_name'],
            'sc': p['status'], 'tc': p['type_cat'], 'pt': p['type'],
            'ze': p['is_ze'], 'mph': p['mech_phase'],
            'd': p['director'], 'sd': p['sr_director'],
            'rm': p['rm'], 'fsm': p['fsm'],
            'mkt': p['market'], 'bn': p['banner'],
            'st': p['state'], 'city': p['city'],
            'ds': p['start'], 'de': p['end'], 'da': p['end_actual'],
            'od': p['overdue'], 'sow': p['scope'],
            'sap': p['sap'], 'seq': p['seq'], 'yr': p['year'],
            'mc': p['mech_contractor'],
            'mcd': p['mc_director'],
            'mcmN': p['mcm_name'], 'mcmP': p['mcm_phone'],
            'pmN': p['pm_name'], 'pmP': p['pm_phone'],
            'mspm': p['mc_sr_pm'], 'cmm': p['cmm'], 'ppm': p['pmo_pm'],
            'bgt': p['budget'],
            'wo': p['wo_status'], 'wol': p['wo_link'],
            'pw': p['pw_status'], 'pwl': p['pw_link'],
        })

    data_json = json.dumps(data, separators=(',', ':')).replace('`', "'")

    # Filter options
    dir_opts = '\n'.join(f'<option value="{d}">{d}</option>' for d in directors)
    sr_dir_opts = '\n'.join(f'<option value="{d}">{d}</option>' for d in sr_directors)
    rm_opts = '\n'.join(f'<option value="{r}">{r}</option>' for r in rms)
    state_opts = '\n'.join(f'<option value="{s}">{s}</option>' for s in states)
    status_opts = '\n'.join(f'<option value="{s}">{s}</option>' for s in statuses)
    year_opts = '\n'.join(f'<option value="{y}">{y}</option>' for y in years)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Capital Projects — North BU</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  .bg-wm {{ background: #0071dc; }}
  .text-wm {{ color: #0071dc; }}
  .ring-wm {{ --tw-ring-color: #0071dc; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  .scope-row {{ display: none; }}
  .scope-row.open {{ display: table-row; }}
  tr.project-row {{ cursor: pointer; }}
  tr.project-row:hover {{ background: #f0f7ff !important; }}
  .ze-row {{ background: #f0fdf4 !important; border-left: 3px solid #22c55e; }}
  .overdue {{ color: #dc2626; font-weight: 600; }}
  @media print {{ .no-print {{ display: none !important; }} }}
</style>
</head>
<body class="bg-gray-100 min-h-screen">

<header class="bg-wm text-white shadow-lg no-print">
  <div class="max-w-[1600px] mx-auto px-4 py-3 flex justify-between items-center">
    <div class="flex items-center gap-3">
      <h1 class="text-xl font-bold">\U0001f3d7\ufe0f North BU — Capital Mechanical Projects</h1>
      <span class="bg-white/20 px-2 py-0.5 rounded text-xs font-medium">LIVE</span>
    </div>
    <span class="text-sm text-blue-200">\U0001f504 LX + BQ + Wrike \u2022 {{now}}</span>
  </div>
</header>

<main class="max-w-[1600px] mx-auto px-4 py-5">

  <!-- KPI Cards -->
  <div class="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-9 gap-3 mb-5" id="kpiRow">
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-blue-500 cursor-pointer hover:shadow-lg transition-all" data-filter="all" onclick="cardFilter('all')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">Total</p>
      <p class="text-2xl font-bold text-blue-600" id="kTotal">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-orange-500 cursor-pointer hover:shadow-lg transition-all" data-filter="const" onclick="cardFilter('const')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">In Construction</p>
      <p class="text-2xl font-bold text-orange-600" id="kConst">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-yellow-500 cursor-pointer hover:shadow-lg transition-all" data-filter="pre" onclick="cardFilter('pre')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">Pre-Construction</p>
      <p class="text-2xl font-bold text-yellow-600" id="kPre">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-indigo-400 cursor-pointer hover:shadow-lg transition-all" data-filter="design" onclick="cardFilter('design')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">Design / Bidding</p>
      <p class="text-2xl font-bold text-indigo-500" id="kDesign">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-red-500 cursor-pointer hover:shadow-lg transition-all" data-filter="overdue" onclick="cardFilter('overdue')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">\u26a0\ufe0f Overdue</p>
      <p class="text-2xl font-bold text-red-600" id="kOver">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-cyan-500 cursor-pointer hover:shadow-lg transition-all" data-filter="ref" onclick="cardFilter('ref')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">\U0001f9ca REF</p>
      <p class="text-2xl font-bold text-cyan-600" id="kREF">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-amber-400 cursor-pointer hover:shadow-lg transition-all" data-filter="hvac" onclick="cardFilter('hvac')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">\U0001f321\ufe0f HVAC</p>
      <p class="text-2xl font-bold text-amber-600" id="kHVAC">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-green-500 cursor-pointer hover:shadow-lg transition-all" data-filter="ze" onclick="cardFilter('ze')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">\u26a1 Zero Emissions</p>
      <p class="text-2xl font-bold text-green-600" id="kZE">0</p>
    </div>
    <div class="kpi-card bg-white rounded-lg shadow p-3 border-l-4 border-violet-500 cursor-pointer hover:shadow-lg transition-all" data-filter="walkoff" onclick="cardFilter('walkoff')">
      <p class="text-[10px] text-gray-500 uppercase font-medium">\U0001f4cb Walk-Offs</p>
      <p class="text-2xl font-bold text-violet-600" id="kWO">0</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-lg shadow p-4 mb-5 no-print">
    <div class="flex justify-between items-center mb-3">
      <h3 class="text-sm font-semibold text-gray-700">\U0001f50d Filters</h3>
      <div class="flex gap-2">
        <button onclick="setFilter('ze')" class="px-3 py-1 bg-green-100 hover:bg-green-200 text-green-700 text-xs rounded-md font-bold">\u26a1 ZE Only</button>
        <button onclick="setFilter('overdue')" class="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 text-xs rounded-md font-bold">\u26a0\ufe0f Overdue</button>
        <button onclick="clearFilters()" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs rounded-md font-medium">\u2715 Clear All</button>
      </div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Phase</label>
        <select id="fStatus" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {status_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Type</label>
        <select id="fType" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          <option value="REF">\U0001f9ca REF</option>
          <option value="HVAC">\U0001f321\ufe0f HVAC</option>
          <option value="EMS">\U0001f4df EMS</option>
          <option value="ZE">\u26a1 Zero Emissions</option>
          <option value="COMBO">\U0001f517 COMBO</option>
          <option value="SP">\U0001f6e0\ufe0f SP</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Sr. Director</label>
        <select id="fSrDir" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {sr_dir_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Director</label>
        <select id="fDir" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {dir_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Regional Mgr</label>
        <select id="fRM" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {rm_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">State</label>
        <select id="fState" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {state_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Year</label>
        <select id="fYear" onchange="applyFilters()" class="w-full border rounded px-2 py-1.5 text-sm">
          <option value="">All</option>
          {year_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">Search</label>
        <input type="text" id="fSearch" oninput="applyFilters()" placeholder="Store, city, scope..." class="w-full border rounded px-2 py-1.5 text-sm">
      </div>
    </div>
  </div>

  <!-- Charts -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">Phase Breakdown</h3>
      <div style="height:220px"><canvas id="chartPhase"></canvas></div>
    </div>
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">Project Types</h3>
      <div style="height:220px"><canvas id="chartType"></canvas></div>
    </div>
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">By Director</h3>
      <div style="height:220px"><canvas id="chartDir"></canvas></div>
    </div>
  </div>

  <!-- Director Summary -->
  <div class="bg-white rounded-lg shadow mb-5">
    <div class="p-4 border-b"><h3 class="text-sm font-semibold text-gray-700">\U0001f464 Director Summary</h3></div>
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50"><tr>
          <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortDir('name')">Director \u21c5</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortDir('total')">Total \u21c5</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-orange-600 uppercase">Const.</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-yellow-600 uppercase">Pre-Con</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-indigo-600 uppercase">Design</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Active</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-red-600 uppercase">Overdue</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-cyan-600 uppercase">\U0001f9ca REF</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-amber-600 uppercase">\U0001f321\ufe0f HVAC</th>
          <th class="px-4 py-2 text-center text-xs font-medium text-green-600 uppercase">\u26a1 ZE</th>
        </tr></thead>
        <tbody id="dirBody" class="bg-white divide-y divide-gray-200"></tbody>
      </table>
    </div>
  </div>

  <!-- Project Table -->
  <div class="bg-white rounded-lg shadow">
    <div class="p-4 border-b"><div class="flex justify-between items-center">
      <h3 class="text-sm font-semibold text-gray-700">\U0001f4cb All Projects <span class="text-xs font-normal text-gray-400">(click row for details)</span></h3>
      <span class="text-xs text-gray-500 font-medium" id="pCount">0</span>
    </div></div>
    <div class="overflow-x-auto" style="max-height:700px">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50 sticky top-0 z-10"><tr>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('s')">Store \u21c5</th>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('n')">Project \u21c5</th>
          <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('tc')">Type \u21c5</th>
          <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('sc')">Phase \u21c5</th>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('mc')">Mech Contractor \u21c5</th>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('mcmN')">MCM \u21c5</th>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('d')">Director \u21c5</th>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('sow')">Scope \u21c5</th>
          <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('st')">State \u21c5</th>
          <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('ds')">Start \u21c5</th>
          <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer" onclick="sortT('de')">End \u21c5</th>
        </tr></thead>
        <tbody id="pBody" class="bg-white divide-y divide-gray-200"></tbody>
      </table>
    </div>
  </div>

</main>

<script>
const D = {data_json};

const SC = {{
  'In Construction':   {{ bg:'#fed7aa', text:'#9a3412' }},
  'Pre-Construction':  {{ bg:'#fef3c7', text:'#92400e' }},
  'Design / Bidding':  {{ bg:'#e0e7ff', text:'#3730a3' }},
  'Active':            {{ bg:'#dbeafe', text:'#1e40af' }},
  'Post-Construction': {{ bg:'#d1fae5', text:'#065f46' }},
  'Complete':          {{ bg:'#f3f4f6', text:'#374151' }},
}};

const TB = {{
  ZE:   '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-700">\u26a1 ZE</span>',
  REF:  '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-100 text-cyan-700">\U0001f9ca REF</span>',
  HVAC: '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">\U0001f321\ufe0f HVAC</span>',
  EMS:  '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700">\U0001f4df EMS</span>',
  COMBO:'<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-700">\U0001f517 COMBO</span>',
  SP:   '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-pink-100 text-pink-700">\U0001f6e0\ufe0f SP</span>',
  BAS:  '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-700">\U0001f3db\ufe0f BAS</span>',
  OTHER:'<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-600">Other</span>',
}};

let F=[...D], sCol='', sAsc=true, dCol='total', dAsc=false, charts={{}}, openRow=null, activeCard=null;

function cardFilter(type) {{
  if(activeCard===type || type==='all') {{ activeCard=null; zeOnly=false; odOnly=false; }}
  else {{ activeCard=type; zeOnly=false; odOnly=false; }}
  const ringColors={{'all':'ring-blue-400','const':'ring-orange-400','pre':'ring-yellow-400','design':'ring-indigo-400','overdue':'ring-red-400','ref':'ring-cyan-400','hvac':'ring-amber-400','ze':'ring-green-400','walkoff':'ring-violet-400'}};
  document.querySelectorAll('.kpi-card').forEach(c=>{{
    const f=c.dataset.filter;
    // Remove all ring colors
    Object.values(ringColors).forEach(rc=>c.classList.remove(rc));
    c.classList.remove('ring-2','ring-offset-1','scale-105','opacity-60');
    if(f===activeCard) {{
      c.classList.add('ring-2','ring-offset-1','scale-105',ringColors[f]);
    }} else if(activeCard) {{
      c.classList.add('opacity-60');
    }}
  }});
  applyFilters();
}}
let zeOnly=false, odOnly=false;

const fmt=d=>{{ if(!d)return'\u2014'; const p=d.split('-'); return `${{p[1]}}/${{p[2]}}/${{p[0].slice(2)}}`; }};
const v=x=>x&&x!=='\u2014'?x:'';

function clearFilters() {{
  ['fStatus','fType','fSrDir','fDir','fRM','fState','fYear','fSearch'].forEach(id=>{{const e=document.getElementById(id);if(e)e.value='';}});
  zeOnly=false; odOnly=false; activeCard=null;
  document.querySelectorAll('.kpi-card').forEach(c=>c.classList.remove('ring-2','ring-offset-1','scale-105','opacity-60'));
  applyFilters();
}}
function setFilter(t) {{
  if(t==='ze') {{ zeOnly=!zeOnly; odOnly=false; }}
  if(t==='overdue') {{ odOnly=!odOnly; zeOnly=false; }}
  applyFilters();
}}

function applyFilters() {{
  const fs=document.getElementById('fStatus').value;
  const ft=document.getElementById('fType').value;
  const fsd=document.getElementById('fSrDir').value;
  const fd=document.getElementById('fDir').value;
  const frm=document.getElementById('fRM').value;
  const fst=document.getElementById('fState').value;
  const fy=document.getElementById('fYear').value;
  const q=document.getElementById('fSearch').value.toLowerCase();
  F=D.filter(p=>{{
    // Card filters
    if(activeCard==='const' && p.sc!=='In Construction') return false;
    if(activeCard==='pre' && p.sc!=='Pre-Construction') return false;
    if(activeCard==='design' && p.sc!=='Design / Bidding') return false;
    if(activeCard==='overdue' && !p.od) return false;
    if(activeCard==='ref' && p.tc!=='REF') return false;
    if(activeCard==='hvac' && p.tc!=='HVAC') return false;
    if(activeCard==='ze' && !p.ze) return false;
    if(activeCard==='walkoff' && !p.wo) return false;
    // Dropdown/toggle filters
    if(zeOnly && !p.ze) return false;
    if(odOnly && !p.od) return false;
    if(fs && p.sc!==fs) return false;
    if(ft && p.tc!==ft) return false;
    if(fsd && p.sd!==fsd) return false;
    if(fd && p.d!==fd) return false;
    if(frm && p.rm!==frm) return false;
    if(fst && p.st!==fst) return false;
    if(fy && p.yr!==fy) return false;
    if(q && !(p.s+' '+p.n+' '+p.sow+' '+p.city+' '+p.d+' '+p.rm+' '+p.mc+' '+p.sn).toLowerCase().includes(q)) return false;
    return true;
  }});
  render();
}}

function render() {{ renderKPIs(); renderCharts(); renderDirTable(); renderTable(); }}

function renderKPIs() {{
  const c={{}};let od=0,ze=0,tc={{}},woDone=0;
  F.forEach(p=>{{ c[p.sc]=(c[p.sc]||0)+1; if(p.od)od++; if(p.ze)ze++; tc[p.tc]=(tc[p.tc]||0)+1; if(p.wo==='Completed'||p.wo==='Approved')woDone++; }});
  document.getElementById('kTotal').textContent=F.length;
  document.getElementById('kConst').textContent=c['In Construction']||0;
  document.getElementById('kPre').textContent=c['Pre-Construction']||0;
  document.getElementById('kDesign').textContent=c['Design / Bidding']||0;
  document.getElementById('kOver').textContent=od;
  document.getElementById('kREF').textContent=tc['REF']||0;
  document.getElementById('kHVAC').textContent=tc['HVAC']||0;
  document.getElementById('kZE').textContent=ze;
  document.getElementById('kWO').textContent=woDone+' / '+(F.filter(p=>p.wo).length);
}}

function renderCharts() {{
  // Phase doughnut
  const sc={{}};F.forEach(p=>sc[p.sc]=(sc[p.sc]||0)+1);
  mkDoughnut('chartPhase',Object.keys(sc),Object.values(sc),['#f97316','#f59e0b','#6366f1','#3b82f6','#10b981','#9ca3af']);
  // Type doughnut
  const tc={{}};F.forEach(p=>tc[p.tc]=(tc[p.tc]||0)+1);
  mkDoughnut('chartType',Object.keys(tc).map(k=>TB[k]?k:'Other'),Object.values(tc),['#06b6d4','#f59e0b','#8b5cf6','#6366f1','#ec4899','#14b8a6','#9ca3af']);
  // Director bar
  const dirs={{}};F.forEach(p=>{{const d=p.d||'Unknown';dirs[d]=(dirs[d]||0)+1;}});
  const de=Object.entries(dirs).sort((a,b)=>b[1]-a[1]).slice(0,15);
  mkBar('chartDir',de.map(e=>e[0]),de.map(e=>e[1]));
}}

function mkDoughnut(id,labels,data,colors) {{
  if(charts[id])charts[id].destroy();
  charts[id]=new Chart(document.getElementById(id),{{
    type:'doughnut',data:{{labels,datasets:[{{data,backgroundColor:colors,borderWidth:2}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{font:{{size:10}}}}}}}}}}
  }});
}}
function mkBar(id,labels,data) {{
  if(charts[id])charts[id].destroy();
  charts[id]=new Chart(document.getElementById(id),{{
    type:'bar',data:{{labels,datasets:[{{data,backgroundColor:'#0071dc',borderRadius:3}}]}},
    options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',
      scales:{{x:{{display:false}},y:{{ticks:{{font:{{size:9}}}}}}}},
      plugins:{{legend:{{display:false}}}}}}
  }});
}}

function renderDirTable() {{
  const dirs={{}};
  F.forEach(p=>{{
    const d=p.d||'Unknown';
    if(!dirs[d]) dirs[d]={{total:0,const:0,pre:0,design:0,active:0,od:0,ref:0,hvac:0,ze:0}};
    dirs[d].total++;
    if(p.sc==='In Construction') dirs[d].const++;
    else if(p.sc==='Pre-Construction') dirs[d].pre++;
    else if(p.sc==='Design / Bidding') dirs[d].design++;
    else dirs[d].active++;
    if(p.od) dirs[d].od++;
    if(p.tc==='REF') dirs[d].ref++;
    if(p.tc==='HVAC') dirs[d].hvac++;
    if(p.ze) dirs[d].ze++;
  }});
  let rows=Object.entries(dirs).map(([n,v])=>({{name:n,...v}}));
  rows.sort((a,b)=>dAsc?(a[dCol]>b[dCol]?1:-1):(b[dCol]>a[dCol]?1:-1));
  document.getElementById('dirBody').innerHTML=rows.map(r=>`
    <tr class="hover:bg-gray-50 cursor-pointer" onclick="document.getElementById('fDir').value='${{r.name}}';applyFilters()">
      <td class="px-4 py-2 text-sm font-medium">${{r.name}}</td>
      <td class="px-4 py-2 text-sm text-center font-bold">${{r.total}}</td>
      <td class="px-4 py-2 text-sm text-center text-orange-600">${{r.const||''}}</td>
      <td class="px-4 py-2 text-sm text-center text-yellow-600">${{r.pre||''}}</td>
      <td class="px-4 py-2 text-sm text-center text-indigo-600">${{r.design||''}}</td>
      <td class="px-4 py-2 text-sm text-center">${{r.active||''}}</td>
      <td class="px-4 py-2 text-sm text-center text-red-600 font-bold">${{r.od||''}}</td>
      <td class="px-4 py-2 text-sm text-center">${{r.ref||''}}</td>
      <td class="px-4 py-2 text-sm text-center">${{r.hvac||''}}</td>
      <td class="px-4 py-2 text-sm text-center text-green-600 font-bold">${{r.ze||''}}</td>
    </tr>`).join('');
}}
function sortDir(col) {{ if(dCol===col) dAsc=!dAsc; else {{dCol=col;dAsc=col==='name';}} renderDirTable(); }}

function renderTable() {{
  document.getElementById('pCount').textContent=`${{F.length}} projects`;
  document.getElementById('pBody').innerHTML=F.map((p,i)=>{{
    const sc=SC[p.sc]||SC['Active'];
    const zeB=p.ze?'<span class="ml-1 px-1 py-0.5 rounded text-[9px] font-bold bg-green-100 text-green-700">\u26a1 ZE</span>':'';
    return `
    <tr class="project-row ${{p.ze?'ze-row':''}}" onclick="toggle(${{i}})">
      <td class="px-3 py-2 text-sm font-mono font-medium text-wm">${{p.s}}</td>
      <td class="px-3 py-2 text-sm">
        <div class="font-medium text-gray-900 truncate max-w-[280px]" title="${{p.n}}">${{p.n}}${{zeB}}</div>
        <div class="text-[10px] text-gray-400">${{p.city}}, ${{p.st}} ${{p.sn?'\u2022 '+p.sn:''}}</div>
      </td>
      <td class="px-3 py-2 text-center">${{TB[p.tc]||''}}</td>
      <td class="px-3 py-2 text-center">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold" style="background:${{sc.bg}};color:${{sc.text}}">${{p.sc}}</span>
      </td>
      <td class="px-3 py-2 text-sm text-gray-700 truncate max-w-[160px]" title="${{p.mc}}">${{v(p.mc)||'\u2014'}}</td>
      <td class="px-3 py-2 text-sm text-gray-700">${{v(p.mcmN)?p.mcmN+(v(p.mcmP)?' <span class="text-[10px] text-blue-500">\U0001f4de</span>':''):'\u2014'}}</td>
      <td class="px-3 py-2 text-sm text-gray-700">${{p.d||'\u2014'}}</td>
      <td class="px-3 py-2 text-xs text-gray-500 truncate max-w-[200px]" title="${{p.sow}}">${{p.sow||'\u2014'}}</td>
      <td class="px-3 py-2 text-sm text-center text-gray-500">${{p.st}}</td>
      <td class="px-3 py-2 text-sm text-center text-gray-500">${{fmt(p.ds)}}</td>
      <td class="px-3 py-2 text-sm text-center ${{p.od?'overdue':''}}">${{fmt(p.de)}}${{p.od?' \u26a0\ufe0f':''}}</td>
    </tr>
    <tr class="scope-row" id="det-${{i}}">
      <td colspan="11" class="px-3 py-0">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 my-2">
          ${{p.sow?'<div class="mb-3 pb-3 border-b border-blue-200"><span class="font-semibold text-gray-600 text-xs">\U0001f4dd Scope:</span><p class="text-sm text-gray-800 mt-1">'+p.sow+'</p></div>':''}}
          <div class="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3 pb-3 border-b border-blue-200">
            <div class="bg-white rounded p-2 border"><div class="text-[10px] text-gray-400 uppercase font-medium">MCM</div><div class="text-sm font-semibold text-gray-800">${{v(p.mcmN)||'\u2014'}}</div>${{v(p.mcmP)?'<div class="text-xs text-blue-600">\U0001f4de '+p.mcmP+'</div>':''}}</div>
            <div class="bg-white rounded p-2 border"><div class="text-[10px] text-gray-400 uppercase font-medium">Project Manager</div><div class="text-sm font-semibold text-gray-800">${{v(p.pmN)||'\u2014'}}</div>${{v(p.pmP)?'<div class="text-xs text-blue-600">\U0001f4de '+p.pmP+'</div>':''}}</div>
            <div class="bg-white rounded p-2 border"><div class="text-[10px] text-gray-400 uppercase font-medium">Mech Contractor</div><div class="text-sm font-semibold text-gray-800">${{v(p.mc)||'\u2014'}}</div></div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div><b class="text-gray-500">Sr. Director:</b> ${{p.sd||'\u2014'}}</div>
            <div><b class="text-gray-500">Director:</b> ${{p.d||'\u2014'}}</div>
            <div><b class="text-gray-500">Regional Mgr:</b> ${{p.rm||'\u2014'}}</div>
            <div><b class="text-gray-500">FSM:</b> ${{p.fsm||'\u2014'}}</div>
            <div><b class="text-gray-500">Market:</b> ${{p.mkt||'\u2014'}}</div>
            <div><b class="text-gray-500">Banner:</b> ${{p.bn||'\u2014'}}</div>
            <div><b class="text-gray-500">SAP #:</b> ${{p.sap||'\u2014'}}</div>
            <div><b class="text-gray-500">Seq / Year:</b> ${{p.seq||'\u2014'}} / ${{p.yr||'\u2014'}}</div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mt-2 pt-2 border-t border-blue-100">
            <div><b class="text-gray-500">MC Director:</b> ${{v(p.mcd)||'\u2014'}}</div>
            <div><b class="text-gray-500">MC Sr. PM:</b> ${{v(p.mspm)||'\u2014'}}</div>
            <div><b class="text-gray-500">CMM:</b> ${{v(p.cmm)||'\u2014'}}</div>
            <div><b class="text-gray-500">PMO PM:</b> ${{v(p.ppm)||'\u2014'}}</div>
            <div><b class="text-gray-500">Mech Phase:</b> ${{p.mph||'\u2014'}}</div>
            <div><b class="text-gray-500">LX Status:</b> ${{p.sc}}</div>
          </div>
          ${{p.bgt&&Number(p.bgt)>0?'<div class="mt-2 pt-2 border-t border-blue-100 text-xs"><b class="text-gray-500">\U0001f4b0 Working Budget:</b> $'+Number(p.bgt).toLocaleString()+'</div>':''}}
          ${{(p.wo||p.pw)?'<div class="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-blue-200">'+(p.wo?'<div class="rounded p-2 border '+(p.wo==="Completed"||p.wo==="Approved"?'bg-green-50 border-green-200':'bg-yellow-50 border-yellow-200')+'"><div class="text-[10px] text-gray-400 uppercase font-medium">\U0001f4cb FS Walk-Off Report</div><div class="text-sm font-semibold '+(p.wo==="Completed"||p.wo==="Approved"?'text-green-700':'text-yellow-700')+'">'+p.wo+'</div>'+(p.wol?'<a href="'+p.wol+'" target="_blank" class="text-[10px] text-blue-500 hover:underline">Open in Wrike \u2197</a>':'')+'</div>':'')+(p.pw?'<div class="rounded p-2 border '+(p.pw==="Completed"?'bg-green-50 border-green-200':'bg-yellow-50 border-yellow-200')+'"><div class="text-[10px] text-gray-400 uppercase font-medium">\U0001f9ca Rack Verification Pre-Project</div><div class="text-sm font-semibold '+(p.pw==="Completed"?'text-green-700':'text-yellow-700')+'">'+p.pw+'</div>'+(p.pwl?'<a href="'+p.pwl+'" target="_blank" class="text-[10px] text-blue-500 hover:underline">Open in Wrike \u2197</a>':'')+'</div>':'')+'</div>':''}}
        </div>
      </td>
    </tr>`;
  }}).join('');
}}

function toggle(i) {{
  const r=document.getElementById(`det-${{i}}`);
  if(openRow!==null&&openRow!==i) document.getElementById(`det-${{openRow}}`).classList.remove('open');
  r.classList.toggle('open');
  openRow=r.classList.contains('open')?i:null;
}}

function sortT(col) {{
  if(sCol===col) sAsc=!sAsc; else {{sCol=col;sAsc=true;}}
  F.sort((a,b)=>{{
    const va=(a[col]||'').toString().toLowerCase(), vb=(b[col]||'').toString().toLowerCase();
    return sAsc?va.localeCompare(vb):vb.localeCompare(va);
  }});
  renderTable();
}}

applyFilters();
</script>
</body>
</html>''';

    with open('projects_preview.html', 'w') as f:
        f.write(html)
    size = os.path.getsize('projects_preview.html') / 1024
    print(f'  HTML: projects_preview.html ({size:.0f} KB)')


def main():
    local = '--local' in sys.argv
    bq_only = '--bq-only' in sys.argv

    # 1. Pull LX projects (primary source)
    if local:
        print('Loading cached LX data...')
        try:
            lx_rows = json.load(open('lx_projects.json'))
            print(f'  LX: {len(lx_rows)} cached projects')
        except FileNotFoundError:
            print('  No cached lx_projects.json — pulling from BQ...')
            lx_rows = pull_lx_projects()
    else:
        print('Pulling LX projects from BQ...')
        lx_rows = pull_lx_projects()

    # 2. Pull Wrike (secondary — for ZE flags + POC contacts)
    wrike_projects = None
    if not bq_only:
        if local:
            try:
                wrike_projects = json.load(open('wrike_projects.json'))
                print(f'  Wrike: {len(wrike_projects)} cached projects')
            except:
                print('  No cached Wrike data')
        else:
            print('Pulling Wrike POC data...')
            try:
                wrike_projects = pull_wrike()
            except Exception as e:
                print(f'  Wrike pull failed: {e}')

    # 2b. Pull walk-off / pre-project forms from Wrike
    walkoff_data = None
    if not bq_only:
        if local:
            try:
                walkoff_data = json.load(open('walkoff_data.json'))
                print(f'  Walk-offs: {len(walkoff_data.get("walkoffs",{}))} cached')
            except:
                print('  No cached walk-off data')
        else:
            print('Pulling FS walk-off forms...')
            try:
                walkoff_data = pull_walkoff_forms()
            except Exception as e:
                print(f'  Walk-off pull failed: {e}')

    # 3. Enrich + build
    print('Enriching projects...')
    projects = enrich(lx_rows, wrike_projects, walkoff_data)

    print('Building HTML...')
    build_html(projects)
    print(f'\u2705 Done! {len(projects)} projects')


if __name__ == '__main__':
    main()
