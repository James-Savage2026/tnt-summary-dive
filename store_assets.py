"""Load and merge store asset data for the store detail view.

Combines rack, HVAC, case, and terminal data into a single
compact dict keyed by store number.
"""
import json
from pathlib import Path

BQ = Path.home() / 'bigquery_results'


def _load(filename):
    path = BQ / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_store_assets():
    """Return {store_nbr: {refrig: {...}, hvac: {...}}} for all stores."""
    rack = _load('rack-store-summary.json')
    hvac = _load('hvac-store-summary.json')
    cases = _load('case-store-summary.json')
    terminals = _load('hvac-terminal-summary.json')

    all_stores = set(rack) | set(hvac) | set(cases) | set(terminals)
    out = {}
    for s in all_stores:
        entry = {}
        # Refrigeration
        r = rack.get(s)
        c = cases.get(s)
        if r or c:
            ref = {}
            if r:
                ref['rc'] = r['rc']        # rack count
                ref['rs'] = r['rs']        # rack scorecard score
                ref['cl'] = r['cl']        # compressor lockouts
                ref['la'] = r['la']        # lockout alarms
                ref['fa'] = r['fa']        # float alarms
                ref['tf'] = r['tf']        # tests failed
                ref['tp'] = r['tp']        # tests passed
            if c:
                ref['cc'] = c['cc']        # case count
                ref['lt'] = c['lt']        # LT cases
                ref['mt'] = c['mt']        # MT cases
                ref['ctp'] = c['tp']       # case terminal %
                ref['cow'] = c['ow']       # case open WOs
                ref['cat'] = c['at']       # case avg temp
            entry['r'] = ref

        # HVAC
        h = hvac.get(s)
        t = terminals.get(s)
        if h or t:
            hv = {}
            if h:
                hv['u'] = h['u']           # total units
                hv['ah'] = h['ah']         # AHU count
                hv['rt'] = h['rt']         # RTU count
                hv['tnt'] = h['tnt']       # HVAC TnT
                hv['dp'] = h['dp']         # avg dewpoint
                hv['al'] = h['al']         # alerts
                hv['hdp'] = h['hdp']       # high dewpoint alerts
                hv['cdp'] = h['cdp']       # critical dewpoint
                hv['wo'] = h['wo']         # WOs last 30
            if t:
                hv['terms'] = t            # terminal units by type
            entry['h'] = hv

        if entry:
            out[s] = entry
    return out


def store_assets_json():
    """Return minified JSON string for embedding."""
    return json.dumps(load_store_assets(), separators=(',', ':'))
