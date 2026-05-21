"""Google Sheets writer using gspread + service account."""

import re

import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials

from config import SHEET_NAME_TEMPLATE

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WITH_WEBSITE_HEADERS = ["Name", "Category", "Address", "Phone", "Email(s)", "Website", "Rating", "Reviews", "Maps URL"]
WITHOUT_WEBSITE_HEADERS = ["Name", "Category", "Address", "Phone", "Email(s)", "Rating", "Reviews", "Maps URL"]

# Desired column widths (pixels) for clean formatting
WITH_WEBSITE_WIDTHS = [200, 150, 250, 150, 220, 250, 70, 80, 300]
WITHOUT_WEBSITE_WIDTHS = [200, 150, 250, 150, 220, 70, 80, 300]


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


def write_to_sheets(niche, state, with_website, without_website, credentials_path, sheet_url=None):
    """
    Write results to a Google Sheet.
    If sheet_url is provided, open that sheet (user-created, shared with service account).
    Otherwise, try to create a new one.
    Returns the shareable URL.
    """
    client = _get_client(credentials_path)

    if sheet_url:
        sheet_id = _extract_sheet_id(sheet_url)
        spreadsheet = client.open_by_key(sheet_id)
    else:
        sheet_name = SHEET_NAME_TEMPLATE.format(niche=niche, state=state)
        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(sheet_name)
            spreadsheet.share(None, perm_type="anyone", role="reader")

    # --- "With Website" worksheet ---
    ws_with = _get_or_create_worksheet(spreadsheet, "With Website", 10)
    existing_with = ws_with.get_all_values()

    # Write headers if empty or header row is blank
    has_headers_with = existing_with and any(cell.strip() for cell in existing_with[0])
    if not has_headers_with:
        ws_with.update("A1", [WITH_WEBSITE_HEADERS], value_input_option="USER_ENTERED")
        existing_with = [WITH_WEBSITE_HEADERS]

    # Get existing names to skip duplicates
    existing_names_with = {row[0].strip().lower() for row in existing_with[1:] if row and row[0].strip()}

    rows_with = []
    for biz in with_website:
        name = biz.get("name", "").strip()
        if name.lower() in existing_names_with:
            continue
        existing_names_with.add(name.lower())
        emails = biz.get("emails", ["Not Found"])
        email_str = ", ".join(emails) if isinstance(emails, list) else str(emails)
        phone = _safe_phone(biz.get("phone", ""))
        rows_with.append([
            name,
            biz.get("category", ""),
            biz.get("address", ""),
            phone,
            email_str,
            biz.get("website", ""),
            biz.get("rating", ""),
            biz.get("reviews", ""),
            biz.get("maps_url", ""),
        ])

    if rows_with:
        next_row = len(existing_with) + 1
        cell_range = f"A{next_row}"
        ws_with.update(cell_range, rows_with, value_input_option="USER_ENTERED")
        _format_worksheet(spreadsheet, ws_with, len(WITH_WEBSITE_HEADERS), WITH_WEBSITE_WIDTHS)

    # --- "Without Website" worksheet ---
    ws_without = _get_or_create_worksheet(spreadsheet, "Without Website", 8)
    existing_without = ws_without.get_all_values()

    has_headers_without = existing_without and any(cell.strip() for cell in existing_without[0])
    if not has_headers_without:
        ws_without.update("A1", [WITHOUT_WEBSITE_HEADERS], value_input_option="USER_ENTERED")
        existing_without = [WITHOUT_WEBSITE_HEADERS]

    existing_names_without = {row[0].strip().lower() for row in existing_without[1:] if row and row[0].strip()}

    rows_without = []
    for biz in without_website:
        name = biz.get("name", "").strip()
        if name.lower() in existing_names_without:
            continue
        existing_names_without.add(name.lower())
        phone = _safe_phone(biz.get("phone", ""))
        emails = biz.get("emails", [])
        email_str = ", ".join(emails) if isinstance(emails, list) and emails else ""
        rows_without.append([
            name,
            biz.get("category", ""),
            biz.get("address", ""),
            phone,
            email_str,
            biz.get("rating", ""),
            biz.get("reviews", ""),
            biz.get("maps_url", ""),
        ])

    if rows_without:
        next_row = len(existing_without) + 1
        cell_range = f"A{next_row}"
        ws_without.update(cell_range, rows_without, value_input_option="USER_ENTERED")
        _format_worksheet(spreadsheet, ws_without, len(WITHOUT_WEBSITE_HEADERS), WITHOUT_WEBSITE_WIDTHS)

    # Remove the default "Sheet1" if it exists
    try:
        default_sheet = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default_sheet)
    except (gspread.WorksheetNotFound, Exception):
        pass

    return spreadsheet.url
