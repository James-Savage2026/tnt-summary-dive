# Email Digest Templates

Reusable email templates for the HVAC TnT Dashboard.
Generate with fresh data and push to Outlook as formatted HTML drafts.

---

## 1. Terminal Cases Tab Announcement

**File:** `terminal-tab-announcement.html`  
**Subject:** `🌡️ Dashboard Update: Terminal Cases Tab`  
**Audience:** Laura Moore  
**Purpose:** Announce new Terminal Cases tab, show how to use it  

### Data Points (from `TERMINAL_DATA` in index.html, filtered to Laura Moore's org)
- Total cases, stores
- Low Temp / Med Temp breakdown
- 3+ consecutive day count
- Screenshot placeholders for KPI cards + table view

### Sections
1. Laura's terminal case stats (4 stat boxes)
2. "5 Things You Can Do" — filter, click charts, Crystal links, WO dropdowns, email button
3. Quick win tip (sort by consec days)
4. Sneak peek: Wrike integration

---

## 2. Win-the-Winter Daily Digest

**File:** `wtw-daily-digest.html`  
**Subject:** `❄️ Win-the-Winter Daily Digest — Laura Moore's Org`  
**Audience:** Laura Moore  
**Purpose:** Daily WTW status with director + phase breakdown  

### Data Points (from `WTW_DATA` in index.html, filtered to Laura Moore's org)

#### Header Stats
- Laura's total store count (from `store_data.json`, `fm_sr_director_name == 'LAURA MOORE'`)
- Total WTW WOs (count of WTW_DATA where srd == Laura Moore)
- Completed count + percentage
- In Progress count
- Open count
- Avg PM Score (average of `pm` field)
- Pass Rate (% where `allP == 'PASS'`)

#### Ready to Complete (green callout box)
- **Definition:** In Progress + `allP == 'PASS'` (all PM components passing)
- Show total ready count
- Show count with 6+ labor hours (`totH >= 6`)
- Break down by director (ready count + 6+ hrs count)
- Break down by phase

#### Phase Tables (3 tables: PH1, PH2, PH3)
For each phase, show per-director:
- WOs (total in that phase)
- Done (completed count)
- % Done (completed / total)
- IP (in progress count)
- Avg PM (average of `pm` field)
- Pass Rate (% where `allP == 'PASS'`)
- Total row at bottom
- Directors sorted by % Done descending
- Color-coded badges:
  - Green: >= 40% done or >= 35% pass rate
  - Amber: 15-39% done or 20-34% pass rate
  - Red: < 15% done or < 20% pass rate

#### Footer
- Dashboard link
- Refresh schedule (6 AM CT)
- Contact info

---

## How to Generate & Send

### Quick send (uses existing HTML template with current data):
```bash
cd ~/Documents/Projects/hvac-tnt-dashboard
python3 send_digest.py --wtw        # WTW daily digest
python3 send_digest.py --terminal   # Terminal tab announcement
```

### Manual process:
1. Run `python3 refresh.py` to get latest data
2. Run the data extraction Python to update the HTML template
3. Push to Outlook via AppleScript:
```python
import subprocess
html = open('wtw-daily-digest.html', 'r').read()
html_escaped = html.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '')
script = f'''tell application "Microsoft Outlook"
    activate
    set newMsg to make new outgoing message with properties {{subject:"❄️ Win-the-Winter Daily Digest — Laura Moore's Org", content:"{html_escaped}"}}
    open newMsg
end tell'''
subprocess.run(['osascript', '-e', script])
```

---

## Key Field Reference (WTW_DATA)

| Field | Description |
|-------|-------------|
| `t` | Tracking number |
| `s` | Store number |
| `st` | Status (COMPLETED, IN PROGRESS, OPEN) |
| `est` | Extended status (INCOMPLETE, DISPATCH CONFIRMED, etc.) |
| `ph` | Phase (PH1, PH2, PH3) |
| `srd` | Sr. Director |
| `fm` | Director |
| `rm` | Regional Manager |
| `fsm` | FSM |
| `pm` | PM Score (float) |
| `allP` | Overall pass/fail (PASS/FAIL) |
| `tnt` | TnT score |
| `rack` | Rack score |
| `dew` | Dewpoint value |
| `totH` | Total labor hours |
| `vis` | Visit count |
| `comp` | Component count |
| `banner` | Store banner |

## Key Field Reference (TERMINAL_DATA)

| Field | Description |
|-------|-------------|
| `sn` | Store number |
| `cn` | Case name |
| `cc` | Case class (LT/MT) |
| `sp` | Setpoint temp |
| `mt` | Mean temp |
| `pt` | % time in terminal |
| `cd` | Consecutive days terminal |
| `ow` | Open work order count (Crystal) |
| `wos` | Matched open WOs [{t, a}] |
| `wos30` | Matched 30-day WOs [{t, a}] |
| `sid` | Crystal sensor ID |
| `srd` | Sr. Director |
| `dir` | Director |
| `rm` | Regional Manager |
| `fsm` | FSM |
| `mgr` | Store Manager |
