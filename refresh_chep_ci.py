"""
Refresh the CHEP 2026 paper review tracking sheet from Indico.
CI/GitHub Actions variant — reads credentials from env vars instead of local files:
  INDICO_CHEP_READ_TOKEN   — bare token string
  GOOGLE_SERVICE_ACCOUNT_KEY — full service-account JSON blob
"""
import json
import os
import re
import requests
from datetime import datetime, timezone

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Auth ---
INDICO_TOKEN = os.environ["INDICO_CHEP_READ_TOKEN"]

sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    sa_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
sheets = build("sheets", "v4", credentials=creds)

BASE = "https://indico.cern.ch"
EVENT_ID = "1471803"
SHEET_ID = "1IN_v1TopLlplSwGgKzGN4ThA6EDPEUsf6ahq4_0_DpY"
HEADERS = {"Authorization": f"Bearer {INDICO_TOKEN}"}

TABLE_NAME = "Submission_Review_Tracking"
TABLE_HEADER_COLOR = {"red": 0.20784314, "green": 0.40784314, "blue": 0.32941177}
TABLE_BAND1_COLOR  = {"red": 1.0, "green": 1.0, "blue": 1.0}
TABLE_BAND2_COLOR  = {"red": 0.9647059, "green": 0.972549, "blue": 0.9764706}

RIGHTS_PAT = re.compile(r"right|license|licence|form", re.IGNORECASE)


def likely_missing_rights(files):
    if not files:
        return "Yes"
    if any(RIGHTS_PAT.search(f["filename"]) for f in files):
        return "No"
    pdfs = [f for f in files if f["filename"].lower().endswith(".pdf")]
    return "No" if len(pdfs) >= 2 else "Yes"


def last_comment_dt(revisions):
    dts = [
        datetime.fromisoformat(c["created_dt"])
        for rev in revisions
        for c in rev["comments"]
    ]
    return max(dts).strftime("%Y-%m-%d %H:%M UTC") if dts else ""


def fmt_dt(iso):
    if not iso:
        return ""
    return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M UTC")


# --- Fetch Indico data ---
print("Fetching contribution track data...")
track_data = requests.get(
    f"{BASE}/export/event/{EVENT_ID}.json?detail=contributions",
    headers=HEADERS,
).json()
track_map = {
    c["friendly_id"]: c.get("track", "")
    for c in track_data["results"][0]["contributions"]
}
print(f"  {len(track_map)} contributions with track info")

print("Fetching Indico paper data...")
data = requests.get(
    f"{BASE}/event/{EVENT_ID}/manage/papers/assignment-list/export-json",
    headers=HEADERS,
).json()
papers = sorted(data["papers"], key=lambda p: p["contribution"]["friendly_id"])
print(f"  {len(papers)} papers")

# --- Build rows ---
HEADER = ["#", "Title", "Track", "Revision", "Last Submitted", "State",
          "Missing Rights Form?", "Last Comment", "Judge(s)", "Reviewer(s)"]

IGNORED_IDS = {671, 690}

rows = []
for paper in papers:
    contrib = paper["contribution"]
    if contrib["friendly_id"] in IGNORED_IDS:
        continue
    if not paper["revisions"]:
        continue
    last_rev = max(paper["revisions"], key=lambda r: r["number"])
    paper_url = f"{BASE}/event/{EVENT_ID}/papers/{contrib['id']}/"
    title = contrib["title"].replace('"', "'")
    rows.append([
        contrib["friendly_id"],
        f'=HYPERLINK("{paper_url}","{title}")',
        track_map.get(contrib["friendly_id"], ""),
        last_rev["number"],
        fmt_dt(last_rev.get("submitted_dt")),
        last_rev["state"],
        likely_missing_rights(last_rev["files"]),
        last_comment_dt(paper["revisions"]),
        last_rev["judge"]["full_name"] if last_rev["judge"] else "",
        "; ".join(r["user"]["full_name"] for r in last_rev["reviews"]),
    ])

all_rows = [HEADER] + rows
n_rows = len(all_rows)
n_cols = len(HEADER)

# --- Get sheet metadata, snapshot column widths, delete existing table FIRST ---
# (deleteTable also clears cell data, so it must happen before the write)
print("Preparing sheet...")
meta = sheets.spreadsheets().get(
    spreadsheetId=SHEET_ID,
    includeGridData=True,
    ranges=["Sheet1!1:1"],
).execute()
sheet0 = meta["sheets"][0]
sheet_id = sheet0["properties"]["sheetId"]

# Snapshot current column widths (cols 0..n_cols-1) so we can restore them
col_widths = {
    i: c["pixelSize"]
    for i, c in enumerate(sheet0.get("data", [{}])[0].get("columnMetadata", []))
    if i < n_cols and "pixelSize" in c
}

existing_tables = [t for t in sheet0.get("tables", []) if t["name"] == TABLE_NAME]
if existing_tables:
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": [{"deleteTable": {"tableId": t["tableId"]}}
                           for t in existing_tables]},
    ).execute()

# --- Write data ---
print("Writing to sheet...")
sheets.spreadsheets().values().clear(
    spreadsheetId=SHEET_ID, range="Sheet1"
).execute()
sheets.spreadsheets().values().update(
    spreadsheetId=SHEET_ID,
    range="Sheet1!A1",
    valueInputOption="USER_ENTERED",
    body={"values": all_rows},
).execute()

run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
sheets.spreadsheets().values().update(
    spreadsheetId=SHEET_ID,
    range="Sheet1!K1",
    valueInputOption="USER_ENTERED",
    body={"values": [[f"Last refreshed: {run_ts}"]]},
).execute()

# --- Rebuild table ---
print("Rebuilding table...")
requests_batch = []

def cs(color):
    return {"rgbColor": color}

requests_batch.append({"addTable": {"table": {
    "name": TABLE_NAME,
    "range": {
        "sheetId": sheet_id,
        "startRowIndex": 0,
        "endRowIndex": n_rows,
        "startColumnIndex": 0,
        "endColumnIndex": n_cols,
    },
    "rowsProperties": {
        "headerColorStyle":     cs(TABLE_HEADER_COLOR),
        "firstBandColorStyle":  cs(TABLE_BAND1_COLOR),
        "secondBandColorStyle": cs(TABLE_BAND2_COLOR),
    },
    "columnProperties": [
        {"columnName": "#",                   "columnType": "DOUBLE"},
        {"columnIndex": 1, "columnName": "Title"},
        {"columnIndex": 2, "columnName": "Track"},
        {"columnIndex": 3, "columnName": "Revision",             "columnType": "DOUBLE"},
        {"columnIndex": 4, "columnName": "Last Submitted"},
        {"columnIndex": 5, "columnName": "State"},
        {"columnIndex": 6, "columnName": "Missing Rights Form?"},
        {"columnIndex": 7, "columnName": "Last Comment"},
        {"columnIndex": 8, "columnName": "Judge(s)"},
        {"columnIndex": 9, "columnName": "Reviewer(s)"},
    ],
}}})

# Freeze header row
requests_batch.append({"updateSheetProperties": {
    "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
    "fields": "gridProperties.frozenRowCount",
}})

# Columns with explicit fixed widths (not subject to snapshot restore / auto-resize)
FIXED_COL_WIDTHS = {2: 194}  # Track: 2x auto-resize

# Restore column widths; auto-resize any column not previously customised
if col_widths:
    for i in range(n_cols):
        if i in FIXED_COL_WIDTHS:
            continue
        if i in col_widths:
            requests_batch.append({"updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": col_widths[i]},
                "fields": "pixelSize",
            }})
        else:
            requests_batch.append({"autoResizeDimensions": {
                "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS",
                               "startIndex": i, "endIndex": i + 1},
            }})
else:
    requests_batch.append({"autoResizeDimensions": {
        "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS",
                       "startIndex": 0, "endIndex": n_cols},
    }})

# Apply fixed column widths (overrides snapshot/auto-resize above)
for col_i, px in FIXED_COL_WIDTHS.items():
    requests_batch.append({"updateDimensionProperties": {
        "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                  "startIndex": col_i, "endIndex": col_i + 1},
        "properties": {"pixelSize": px},
        "fields": "pixelSize",
    }})

# Set column K width to fit the timestamp
requests_batch.append({"updateDimensionProperties": {
    "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
              "startIndex": 10, "endIndex": 11},
    "properties": {"pixelSize": 210},
    "fields": "pixelSize",
}})

# Restore WRAP on all data cells
requests_batch.append({"repeatCell": {
    "range": {"sheetId": sheet_id,
              "startRowIndex": 0, "endRowIndex": n_rows,
              "startColumnIndex": 0, "endColumnIndex": n_cols},
    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
    "fields": "userEnteredFormat.wrapStrategy",
}})

# Conditional formatting: colored backgrounds for State and Missing Rights Form?
GREEN  = {"red": 0.714, "green": 0.843, "blue": 0.659}
AMBER  = {"red": 1.0,   "green": 0.898, "blue": 0.6}
RED    = {"red": 0.918, "green": 0.6,   "blue": 0.6}
BLUE   = {"red": 0.624, "green": 0.773, "blue": 0.910}
ORANGE = {"red": 1.0,   "green": 0.737, "blue": 0.396}

def cf_rule(col_index, text, bg):
    return {"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sheet_id,
                    "startRowIndex": 1, "endRowIndex": n_rows,
                    "startColumnIndex": col_index, "endColumnIndex": col_index + 1}],
        "booleanRule": {
            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": text}]},
            "format": {"backgroundColor": bg},
        },
    }, "index": 0}}

for text, bg in [("accepted", GREEN), ("submitted", BLUE),
                 ("to_be_corrected", ORANGE), ("rejected", RED)]:
    requests_batch.append(cf_rule(5, text, bg))

for text, bg in [("No", GREEN), ("Yes", RED)]:
    requests_batch.append(cf_rule(6, text, bg))

sheets.spreadsheets().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={"requests": requests_batch},
).execute()

# Apply showCustomUi separately (not accepted inside addTable)
def dv_range(col):
    return {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": n_rows,
            "startColumnIndex": col, "endColumnIndex": col + 1}

sheets.spreadsheets().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={"requests": [
        {"setDataValidation": {"range": dv_range(5), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [
                {"userEnteredValue": "submitted"},
                {"userEnteredValue": "to_be_corrected"},
                {"userEnteredValue": "accepted"},
                {"userEnteredValue": "rejected"},
            ]},
            "showCustomUi": True, "strict": False,
        }}},
        {"setDataValidation": {"range": dv_range(6), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [
                {"userEnteredValue": "No"},
                {"userEnteredValue": "Yes"},
            ]},
            "showCustomUi": True, "strict": False,
        }}},
    ]}
).execute()

print(f"Done — {len(rows)} papers, table '{TABLE_NAME}' rebuilt.")
print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
