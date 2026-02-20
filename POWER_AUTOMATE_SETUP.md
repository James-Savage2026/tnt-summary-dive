# Power Automate: Dashboard Email Tracker

Track sent emails from the HVAC TnT Dashboard — Terminal Cases, WTW, Store Questions.
Automatically log who you emailed, when, and whether they responded.

---

## Step 1: Create the Tracking Sheet

1. Go to **OneDrive** → New → Excel workbook → name it **`Email Tracker.xlsx`**
2. In cell A1, type these headers across the row:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Date Sent | Store | Type | Case/Topic | Recipient | Status | Days Open |

3. Select the header row → **Insert → Table** (Ctrl+T)
4. Click the table → go to **Table Design** tab → rename to **`EmailLog`**
5. Save and close

---

## Step 2: Build Flow #1 — "Log Sent Dashboard Emails"

1. Go to [flow.microsoft.com](https://flow.microsoft.com)
2. Click **+ Create** → **Automated cloud flow**
3. Flow name: `Track Dashboard Emails`
4. Choose trigger: **"When a new email is sent (V3)"** (Office 365 Outlook)
5. Click **Create**

### Add Actions:

#### Action 1: Condition
- Click **+ New step** → **Condition**
- Set to **OR** mode (click "Add" → "Add row" for each):
  - Subject `contains` `Terminal Case Support`
  - Subject `contains` `Win the Winter`
  - Subject `contains` `PM Score`

#### Action 2 (If Yes branch): Compose — Extract Store Number
- **+ New step** → **Compose**
- Rename to `ExtractStore`
- Input (Expression):
```
first(split(last(split(triggerOutputs()?['body/subject'], 'Store ')), ' '))
```

#### Action 3: Compose — Determine Type
- **+ New step** → **Compose**
- Rename to `EmailType`
- Input (Expression):
```
if(contains(triggerOutputs()?['body/subject'], 'Terminal'), 'Terminal Case', if(contains(triggerOutputs()?['body/subject'], 'Winter'), 'Win the Winter', 'Store Question'))
```

#### Action 4: Compose — Extract Case Name (for Terminal)
- **+ New step** → **Compose**
- Rename to `CaseName`
- Input (Expression):
```
if(contains(triggerOutputs()?['body/subject'], '–'), first(split(last(split(triggerOutputs()?['body/subject'], '– ')), ' (')), 'N/A')
```

#### Action 5: Add a row into a table (Excel Online)
- **+ New step** → search **"Add a row into a table"** (Excel Online Business)
- **Location:** OneDrive for Business
- **Document Library:** OneDrive
- **File:** `/Email Tracker.xlsx`
- **Table:** `EmailLog`
- Map columns:
  - **Date Sent:** `utcNow('yyyy-MM-dd HH:mm')`
  - **Store:** Output of `ExtractStore`
  - **Type:** Output of `EmailType`
  - **Case/Topic:** Output of `CaseName`
  - **Recipient:** `triggerOutputs()?['body/toRecipients']`
  - **Status:** `Awaiting Response`
  - **Days Open:** `0`

6. Click **Save**

---

## Step 3: Build Flow #2 — "Track Replies"

1. **+ Create** → **Automated cloud flow**
2. Flow name: `Track Email Replies`
3. Trigger: **"When a new email arrives (V3)"** (Office 365 Outlook)
   - Click **Show advanced options**
   - **Subject Filter:** `Terminal Case Support` (or leave blank for all)
   - **Include Attachments:** No

### Add Actions:

#### Action 1: Condition
- Subject `contains` `RE:` OR Subject `contains` `Re:`

#### Action 2 (If Yes): List rows in table
- Search **"List rows present in a table"** (Excel Online)
- **File:** `/Email Tracker.xlsx`
- **Table:** `EmailLog`

#### Action 3: Apply to each
- Loop through rows, find matching store + type
- **Update a row** → set Status to `Responded`

> **Simpler alternative:** Skip auto-reply tracking. Just manually update
> the Status column in your Excel sheet when you get responses.

---

## Step 4: Dashboard — Check Your Tracker

Open `Email Tracker.xlsx` anytime to see:
- All emails sent from the dashboard
- Who hasn't responded (Status = "Awaiting Response")
- How many days each has been open

### Bonus: Add a Days Open formula in Excel
In the **Days Open** column, use this formula:
```
=IF([@Status]="Awaiting Response", TODAY()-[@[Date Sent]], "")
```

---

## Email Subject Patterns (for reference)

The dashboard generates these subjects:
- **Terminal:** `Store 1234 – B9a (Low Temp) Terminal Case Support`
- **WTW:** `Store 1234 – Win the Winter Follow-up`
- **Store/PM:** `Store 1234 – PM Score Review`

---

## Tips

- Power Automate runs in your browser: [flow.microsoft.com](https://flow.microsoft.com)
- No install needed on Mac
- Flows run automatically in the background
- Check **Flow Runs** to see if it's working (My Flows → click flow → Run History)
- If a flow fails, check the error message in Run History
