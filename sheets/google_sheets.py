"""Google Sheets writer using gspread + service account."""

import re
import difflib
import logging
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials

from config import SHEET_NAME_TEMPLATE

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WITH_WEBSITE_HEADERS = ["Lead ID", "Name", "Category", "Address", "Phone", "Email(s)", "Email Status", "Website", "Rating", "Reviews", "Source", "Maps URL"]
WITHOUT_WEBSITE_HEADERS = ["Lead ID", "Name", "Category", "Address", "Phone", "Email(s)", "Email Status", "Rating", "Reviews", "Source", "Maps URL"]

# Desired column widths (pixels) for clean formatting
WITH_WEBSITE_WIDTHS = [130, 200, 150, 250, 150, 220, 110, 250, 70, 80, 160, 300]
WITHOUT_WEBSITE_WIDTHS = [130, 200, 150, 250, 150, 220, 110, 70, 80, 160, 300]

# Similarity threshold for fuzzy duplicate detection (name + address)
DUPLICATE_SIMILARITY_THRESHOLD = 0.85


def _get_client(credentials_path):
    """Authenticate and return a gspread client."""
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_service_account_email(credentials_path):
    """Return the service account email from credentials file."""
    import json
    with open(credentials_path) as f:
        data = json.load(f)
    return data.get("client_email", "")


def _safe_phone(phone):
    """Prefix phone numbers with apostrophe so Sheets treats them as text, not formulas."""
    if not phone:
        return ""
    phone = str(phone).strip()
    if phone.startswith("+") or phone.startswith("="):
        return "'" + phone
    return phone


def _get_or_create_worksheet(spreadsheet, title, cols):
    """Get existing worksheet or create a new one."""
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=cols)


def _extract_sheet_id(sheet_url):
    """Extract spreadsheet ID from a Google Sheets URL."""
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if match:
        return match.group(1)
    return sheet_url.strip()


def _normalise_text(text: str) -> str:
    """Lowercase, strip, remove non-alphanumeric for comparison."""
    return re.sub(r'[^a-z0-9]', '', str(text).lower().strip())


def _name_address_similarity(name_a: str, addr_a: str, name_b: str, addr_b: str) -> float:
    """
    Compute a combined similarity score using name + address.
    Does NOT use phone number — phone may legitimately differ between sources.
    Returns a float between 0.0 and 1.0.
    """
    name_sim = difflib.SequenceMatcher(
        None, _normalise_text(name_a), _normalise_text(name_b)
    ).ratio()
    addr_sim = difflib.SequenceMatcher(
        None, _normalise_text(addr_a), _normalise_text(addr_b)
    ).ratio()
    # Weighted average: name is slightly more reliable than address
    return (name_sim * 0.6) + (addr_sim * 0.4)


def get_existing_lead_data(sheet_url, credentials_path):
    """
    Read both worksheets and return:
      - existing_ids: set of Lead ID strings already in the sheet
      - existing_records: list of dicts with 'lead_id', 'name', 'address' for fuzzy matching

    Used by the scraper to detect and skip duplicate leads before writing.
    """
    client = _get_client(credentials_path)
    sheet_id = _extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)

    existing_ids = set()
    existing_records = []

    for title in ["With Website", "Without Website"]:
        try:
            ws = spreadsheet.worksheet(title)
            records = ws.get_all_records()
            for row in records:
                lead_id = str(row.get("Lead ID", "")).strip()
                name    = str(row.get("Name", "")).strip()
                address = str(row.get("Address", "")).strip()
                if lead_id:
                    existing_ids.add(lead_id)
                if name:
                    existing_records.append({
                        "lead_id": lead_id,
                        "name": name,
                        "address": address,
                    })
        except Exception as e:
            logger.warning(f"Could not read worksheet '{title}' for duplicate check: {e}")

    return existing_ids, existing_records


def is_duplicate_lead(biz: dict, existing_ids: set, existing_records: list) -> bool:
    """
    Returns True if `biz` is already present in the sheet.

    Detection strategy (fuzzy, Option B):
      1. Exact Lead ID match (fast path).
      2. Fuzzy name+address similarity ≥ DUPLICATE_SIMILARITY_THRESHOLD (no phone).
    """
    lead_id = biz.get("lead_id", "").strip()

    # Fast path: exact ID match
    if lead_id and lead_id in existing_ids:
        return True

    # Fuzzy path: name + address similarity
    biz_name = biz.get("name", "")
    biz_addr = biz.get("address", "")
    if not biz_name:
        return False

    for record in existing_records:
        sim = _name_address_similarity(biz_name, biz_addr, record["name"], record["address"])
        if sim >= DUPLICATE_SIMILARITY_THRESHOLD:
            return True

    return False


def _format_worksheet(spreadsheet, worksheet, num_cols, col_widths):
    """Apply formatting: bold header, freeze row 1, set column widths, alternating colors."""
    sheet_id = worksheet.id
    requests = []

    # Remove existing banding first to avoid duplicate error
    try:
        sheet_meta = spreadsheet.fetch_sheet_metadata()
        for sheet in sheet_meta.get("sheets", []):
            if sheet["properties"]["sheetId"] == sheet_id:
                for banding in sheet.get("bandedRanges", []):
                    requests.append({"deleteBanding": {"bandedRangeId": banding["bandedRangeId"]}})
                break
    except Exception:
        pass

    # Bold + background color for header row
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.15, "green": 0.15, "blue": 0.15},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 10,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "padding": {"top": 6, "bottom": 6, "left": 8, "right": 8},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
        }
    })

    # Freeze header row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    })

    # Set column widths
    for i, width in enumerate(col_widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })

    # Set row height for header
    requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 1,
            },
            "properties": {"pixelSize": 36},
            "fields": "pixelSize",
        }
    })

    # Wrap text for all data cells
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "wrapStrategy": "WRAP",
                    "verticalAlignment": "TOP",
                    "padding": {"top": 4, "bottom": 4, "left": 6, "right": 6},
                }
            },
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment,padding)",
        }
    })

    # Add border under header
    requests.append({
        "updateBorders": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "bottom": {
                "style": "SOLID",
                "width": 2,
                "color": {"red": 0.3, "green": 0.3, "blue": 0.3},
            },
        }
    })

    # Alternating row colors
    requests.append({
        "addBanding": {
            "bandedRange": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols,
                },
                "rowProperties": {
                    "firstBandColor": {"red": 1, "green": 1, "blue": 1},
                    "secondBandColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                },
            }
        }
    })

    spreadsheet.batch_update({"requests": requests})


def _build_with_website_row(biz):
    """Build a row list for the 'With Website' sheet from a business dict."""
    emails = biz.get("emails", [])
    if isinstance(emails, list):
        clean_emails = [
            e for e in emails
            if e and "@" in e and e.strip().lower() not in ("not found", "")
        ]
        email_str = ", ".join(clean_emails) if clean_emails else "Not Found"
    else:
        email_str = str(emails) if emails and "@" in str(emails) else "Not Found"

    email_status = "Not Sent" if email_str != "Not Found" else "NULL"
    phone = _safe_phone(biz.get("phone", ""))

    return [
        biz.get("lead_id", "").strip(),
        biz.get("name", "").strip(),
        biz.get("category", "").strip(),
        biz.get("address", "").strip(),
        phone,
        email_str,
        email_status,
        biz.get("website", "").strip(),
        biz.get("rating", "").strip(),
        biz.get("reviews", "").strip(),
        biz.get("source", "").strip(),
        biz.get("maps_url", "").strip(),
    ]


def _build_without_website_row(biz):
    """Build a row list for the 'Without Website' sheet from a business dict."""
    emails = biz.get("emails", [])
    if isinstance(emails, list):
        clean_emails = [
            e for e in emails
            if e and "@" in e and e.strip().lower() not in ("not found", "")
        ]
        email_str = ", ".join(clean_emails) if clean_emails else "Not Found"
    else:
        email_str = str(emails) if emails and "@" in str(emails) else "Not Found"

    email_status = "Not Sent" if email_str != "Not Found" else "NULL"
    phone = _safe_phone(biz.get("phone", ""))

    return [
        biz.get("lead_id", "").strip(),
        biz.get("name", "").strip(),
        biz.get("category", "").strip(),
        biz.get("address", "").strip(),
        phone,
        email_str,
        email_status,
        biz.get("rating", "").strip(),
        biz.get("reviews", "").strip(),
        biz.get("source", "").strip(),
        biz.get("maps_url", "").strip(),
    ]


def clear_sheet(sheet_url, credentials_path):
    """Clear all DATA from both worksheets, then restore correct header row."""
    client = _get_client(credentials_path)
    sheet_id = _extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)

    ws_config = [
        ("With Website",    len(WITH_WEBSITE_HEADERS),    WITH_WEBSITE_HEADERS,    WITH_WEBSITE_WIDTHS),
        ("Without Website", len(WITHOUT_WEBSITE_HEADERS), WITHOUT_WEBSITE_HEADERS, WITHOUT_WEBSITE_WIDTHS),
    ]

    for title, num_cols, headers, widths in ws_config:
        try:
            ws = spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=num_cols)

        ws.clear()
        ws.update("A1", [headers], value_input_option="USER_ENTERED")
        _format_worksheet(spreadsheet, ws, num_cols, widths)

    return True


def write_to_sheets(query, with_website, without_website, credentials_path, sheet_url=None, append=False):
    """
    Write results to a Google Sheet.

    Parameters
    ----------
    append : bool
        If True, append new rows below existing data without clearing the sheet.
        Headers are written only if the sheet is empty.
        If False (default), clear the worksheet and rewrite from scratch.
    """
    client = _get_client(credentials_path)

    if sheet_url:
        sheet_id = _extract_sheet_id(sheet_url)
        spreadsheet = client.open_by_key(sheet_id)
    else:
        safe_query = query.strip()[:50]
        sheet_name = SHEET_NAME_TEMPLATE.format(query=safe_query)
        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(sheet_name)
            spreadsheet.share(None, perm_type="anyone", role="reader")

    # --- "With Website" worksheet ---
    ws_with = _get_or_create_worksheet(spreadsheet, "With Website", len(WITH_WEBSITE_HEADERS))
    rows_with = [_build_with_website_row(biz) for biz in with_website]

    if append:
        # Check if sheet has headers; if empty, write headers first
        existing_values = ws_with.get_all_values()
        if not existing_values:
            ws_with.update("A1", [WITH_WEBSITE_HEADERS], value_input_option="USER_ENTERED")
            _format_worksheet(spreadsheet, ws_with, len(WITH_WEBSITE_HEADERS), WITH_WEBSITE_WIDTHS)
        if rows_with:
            ws_with.append_rows(rows_with, value_input_option="USER_ENTERED")
    else:
        ws_with.clear()
        all_with = [WITH_WEBSITE_HEADERS] + rows_with
        ws_with.update("A1", all_with, value_input_option="USER_ENTERED")
        if rows_with:
            _format_worksheet(spreadsheet, ws_with, len(WITH_WEBSITE_HEADERS), WITH_WEBSITE_WIDTHS)

    # --- "Without Website" worksheet ---
    ws_without = _get_or_create_worksheet(spreadsheet, "Without Website", len(WITHOUT_WEBSITE_HEADERS))
    rows_without = [_build_without_website_row(biz) for biz in without_website]

    if append:
        existing_values_wo = ws_without.get_all_values()
        if not existing_values_wo:
            ws_without.update("A1", [WITHOUT_WEBSITE_HEADERS], value_input_option="USER_ENTERED")
            _format_worksheet(spreadsheet, ws_without, len(WITHOUT_WEBSITE_HEADERS), WITHOUT_WEBSITE_WIDTHS)
        if rows_without:
            ws_without.append_rows(rows_without, value_input_option="USER_ENTERED")
    else:
        ws_without.clear()
        all_without = [WITHOUT_WEBSITE_HEADERS] + rows_without
        ws_without.update("A1", all_without, value_input_option="USER_ENTERED")
        if rows_without:
            _format_worksheet(spreadsheet, ws_without, len(WITHOUT_WEBSITE_HEADERS), WITHOUT_WEBSITE_WIDTHS)

    try:
        default_sheet = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default_sheet)
    except (gspread.WorksheetNotFound, Exception):
        pass

    return spreadsheet.url


def read_leads_from_sheet(sheet_url, credentials_path):
    """
    Reads all leads from both worksheets ('With Website' and 'Without Website').
    Returns a list of dictionaries with 1-indexed row position for email outreach processing.
    Only returns leads with a valid email address and status 'Not Sent'.
    """
    client = _get_client(credentials_path)
    sheet_id = _extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)
    leads = []

    for title in ["With Website", "Without Website"]:
        try:
            ws = spreadsheet.worksheet(title)
            records = ws.get_all_records()
            for idx, row in enumerate(records, start=2):  # Header is row 1
                emails = str(row.get("Email(s)", "")).strip()
                email_status = str(row.get("Email Status", "")).strip()

                leads.append({
                    "row_index": idx,
                    "worksheet_title": title,
                    "lead_id": str(row.get("Lead ID", "")),
                    "name": str(row.get("Name", "")),
                    "category": str(row.get("Category", "")),
                    "address": str(row.get("Address", "")),
                    "phone": str(row.get("Phone", "")),
                    "emails": emails,
                    "email_status": email_status or ("Not Sent" if emails and "@" in emails and emails.lower() != "not found" else "NULL"),
                    "website": str(row.get("Website", "")) if "Website" in row else "",
                    "rating": str(row.get("Rating", "")),
                    "reviews": str(row.get("Reviews", "")),
                    "source": str(row.get("Source", "")),
                    "maps_url": str(row.get("Maps URL", ""))
                })
        except Exception as e:
            logger.warning(f"Could not read worksheet '{title}': {e}")

    return leads


def update_lead_email_status(sheet_url, credentials_path, worksheet_title, row_index, new_status):
    """
    Updates the 'Email Status' cell for a specific lead in Google Sheets.
    """
    client = _get_client(credentials_path)
    sheet_id = _extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)
    ws = spreadsheet.worksheet(worksheet_title)

    headers = ws.row_values(1)
    if "Email Status" in headers:
        col_idx = headers.index("Email Status") + 1
        ws.update_cell(row_index, col_idx, new_status)
        return True
    return False
