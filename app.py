"""Flask API server for the Google Maps Leads Scraper."""

import uuid
import threading
import json
import time
import queue
import os
import random
from urllib.parse import urlparse

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

from config import (
    DEFAULT_MAX_RESULTS,
    MAX_RESULTS_CAP,
    DEFAULT_SHEET_URL,
    SENDER_EMAIL,
    SENDER_NAME,
    SMTP_USERNAME,
    SMTP_PASSWORD
)

# Bootstrap credentials.json from environment variable (for cloud deployment)
_creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
if _creds_env and not os.path.exists(os.path.join(os.path.dirname(__file__), "credentials.json")):
    import base64
    _creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    with open(_creds_path, "w") as _f:
        _f.write(base64.b64decode(_creds_env).decode("utf-8"))

from scraper.orchestrator import scrape_all_sources
from scraper.website_scraper import extract_contact_info
from sheets.google_sheets import (
    write_to_sheets,
    get_service_account_email,
    clear_sheet,
    read_leads_from_sheet,
    update_lead_email_status,
    get_existing_lead_data,
    is_duplicate_lead,
)
from email_templates import generate_email_content
from email_sender import send_outreach_email, test_smtp_connection

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# In-memory task stores
tasks = {}
outreach_tasks = {}


def run_scrape_task(task_id, query, max_results, sheet_url=None, filter_type="both", sources=None):
    """Background thread that runs the full scraping pipeline."""
    task = tasks[task_id]
    log_queue = task["log_queue"]

    def emit(msg, level="info"):
        log_queue.put(json.dumps({"message": msg, "level": level, "time": time.time()}))

    try:
        emit(f"Starting scrape: \"{query}\" (max {max_results} results) | Sources: {', '.join(sources or ['all'])}")
        task["status"] = "scraping_sources"

        businesses = []
        for event in scrape_all_sources(query, max_results, sources=sources):
            if event["type"] == "log":
                emit(event["message"], event.get("level", "info"))
            elif event["type"] == "result":
                businesses.append(event["data"])
                task["counts"]["total"] = len(businesses)
            elif event["type"] == "summary":
                sc = event.get("counts", {})
                task["counts"]["from_maps"]       = sc.get("from_maps", 0)
                task["counts"]["from_google"]     = sc.get("from_google", 0)
                task["counts"]["from_duckduckgo"] = sc.get("from_duckduckgo", 0)
                task["counts"]["enriched"]        = sc.get("enriched", 0)

        emit(f"All sources complete. Unique leads found: {len(businesses)}.", "success")

        all_with_website = [b for b in businesses if b.get("website")]
        all_without_website = [b for b in businesses if not b.get("website")]

        if filter_type == "with_website":
            with_website = all_with_website
            without_website = []
        elif filter_type == "without_website":
            with_website = []
            without_website = all_without_website
        else:
            with_website = all_with_website
            without_website = all_without_website

        task["counts"]["with_website"] = len(with_website)
        task["counts"]["without_website"] = len(without_website)

        emit(f"Split: {len(all_with_website)} with website, {len(all_without_website)} without website")
        if filter_type != "both":
            emit(f"Filter applied: {filter_type.replace('_', ' ')}")

        task["status"] = "scraping_websites"
        for i, biz in enumerate(with_website):
            domain = urlparse(biz['website']).netloc or biz['website']
            emit(f"Scanning website ({i+1}/{len(with_website)}): {domain}")
            try:
                contact_info = extract_contact_info(biz["website"])
                biz["emails"] = contact_info.get("emails", [])
                if not biz.get("phone"):
                    biz["phone"] = contact_info.get("phone", "Not Found")
            except Exception as e:
                emit(f"Error scanning {biz['website']}: {str(e)}", "error")
                biz["emails"] = []

        emit("Website scanning complete.", "success")

        task["status"] = "writing_sheets"
        emit("Writing results to Google Sheets...")

        credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        if not os.path.exists(credentials_path):
            emit("ERROR: credentials.json not found. Cannot write to Google Sheets.", "error")
            task["status"] = "completed"
            task["sheet_url"] = None
        else:
            # ── Duplicate detection ──────────────────────────────────────────
            emit("Checking existing sheet data for duplicates...")
            try:
                existing_ids, existing_records = get_existing_lead_data(sheet_url, credentials_path)
                if existing_ids or existing_records:
                    orig_total = len(with_website) + len(without_website)
                    with_website   = [b for b in with_website   if not is_duplicate_lead(b, existing_ids, existing_records)]
                    without_website = [b for b in without_website if not is_duplicate_lead(b, existing_ids, existing_records)]
                    skipped = orig_total - len(with_website) - len(without_website)
                    emit(
                        f"Duplicate check: {skipped} lead(s) skipped (already in sheet), "
                        f"{len(with_website) + len(without_website)} new lead(s) to write.",
                        "info"
                    )
                else:
                    emit("Sheet is empty — no duplicates to skip.", "info")
                use_append = True
            except Exception as dup_err:
                emit(f"Warning: Duplicate check failed ({dup_err}). Writing full results.", "warning")
                use_append = False

            # ── Write to sheet (append new rows only) ────────────────────────
            if with_website or without_website:
                sheet_url = write_to_sheets(
                    query, with_website, without_website,
                    credentials_path, sheet_url=sheet_url,
                    append=use_append
                )
                task["sheet_url"] = sheet_url
                emit("Google Sheet updated successfully.", "success")
            else:
                task["sheet_url"] = sheet_url
                emit("No new leads to write — all scraped results already exist in the sheet.", "info")
            task["status"] = "completed"

        emit("All done!", "success")

    except Exception as e:
        emit(f"Fatal error: {str(e)}", "error")
        task["status"] = "error"
        task["error"] = str(e)


def run_outreach_task(task_id, sheet_url, custom_template=None):
    """Background thread that executes cold outreach campaign."""
    task = outreach_tasks[task_id]
    log_queue = task["log_queue"]

    def emit(msg, level="info", payload=None):
        data = {"message": msg, "level": level, "time": time.time()}
        if payload:
            data.update(payload)
        log_queue.put(json.dumps(data))

    try:
        credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        if not os.path.exists(credentials_path):
            emit("ERROR: credentials.json not found.", "error")
            task["status"] = "error"
            return

        emit("Verifying SMTP server connection...")
        conn_test = test_smtp_connection()
        if not conn_test["success"]:
            emit(f"SMTP Connection Error: {conn_test['error']}", "error")
            task["status"] = "error"
            return
        emit("SMTP Server connection verified successfully.", "success")

        emit("Fetching leads queue from Google Sheet...")
        leads = read_leads_from_sheet(sheet_url, credentials_path)

        # Filter queue: valid email + status != 'Sent'
        target_leads = []
        for lead in leads:
            raw_email = lead.get("emails", "").strip()
            status = lead.get("email_status", "").strip()

            if raw_email and "@" in raw_email and raw_email.lower() != "not found" and status != "Sent":
                # If multiple emails, take first clean email
                first_email = [e.strip() for e in raw_email.split(",") if "@" in e][0]
                lead["target_email"] = first_email
                target_leads.append(lead)

        task["total_queue"] = len(target_leads)
        emit(f"Found {len(target_leads)} eligible lead(s) ready for outreach campaign.")

        if not target_leads:
            emit("No pending leads found to email. Campaign finished.", "success")
            task["status"] = "completed"
            return

        sent_count = 0
        failed_count = 0

        for idx, lead in enumerate(target_leads, start=1):
            if task.get("stopped"):
                emit("Outreach campaign cancelled by user.", "warning")
                task["status"] = "cancelled"
                return

            recipient = lead["target_email"]
            name = lead.get("name")
            location = lead.get("address")
            category = lead.get("category")

            emit(f"[{idx}/{len(target_leads)}] Preparing cold email for {name} ({recipient})...")

            # Generate content
            content = generate_email_content(name, location, category)

            # Send email
            res = send_outreach_email(
                recipient_email=recipient,
                subject=content["subject"],
                html_body=content["html_body"],
                text_body=content["text_body"]
            )

            if res["success"]:
                sent_count += 1
                task["sent_count"] = sent_count
                emit(f"[{idx}/{len(target_leads)}] Delivered email to {recipient}", "success")
                
                # Update status in Google Sheets
                try:
                    update_lead_email_status(
                        sheet_url=sheet_url,
                        credentials_path=credentials_path,
                        worksheet_title=lead["worksheet_title"],
                        row_index=lead["row_index"],
                        new_status="Sent"
                    )
                    emit(f"Updated row #{lead['row_index']} status in '{lead['worksheet_title']}' -> Sent", "info")
                except Exception as ex:
                    emit(f"Warning: Could not update sheet status for {name}: {ex}", "warning")
            else:
                failed_count += 1
                task["failed_count"] = failed_count
                emit(f"[{idx}/{len(target_leads)}] Failed to send to {recipient}: {res['error']}", "error")

            # Apply anti-spam throttling delay if not last item
            if idx < len(target_leads) and not task.get("stopped"):
                delay = random.uniform(5.0, 12.0)
                emit(f"Throttling delay: waiting {delay:.1f}s before next email...", "info")
                time.sleep(delay)

        emit(f"Outreach campaign complete! Sent: {sent_count}, Failed: {failed_count}", "success")
        task["status"] = "completed"

    except Exception as e:
        emit(f"Fatal outreach error: {str(e)}", "error")
        task["status"] = "error"


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    """Start a new scraping task."""
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        niche = data.get("niche", "").strip()
        state = data.get("state", "").strip()
        if niche and state:
            query = f"{niche} in {state}"
        elif niche:
            query = niche
    max_results = min(int(data.get("max_results", DEFAULT_MAX_RESULTS)), MAX_RESULTS_CAP)
    sheet_url = data.get("sheet_url", "").strip() or DEFAULT_SHEET_URL
    filter_type = data.get("filter", "both")
    sources = data.get("sources", ["google_maps", "google_search", "duckduckgo"])
    if not isinstance(sources, list) or not sources:
        sources = ["google_maps", "google_search", "duckduckgo"]

    if not query:
        return jsonify({"error": "A 'query' field is required."}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "log_queue": queue.Queue(),
        "counts": {
            "total": 0,
            "with_website": 0,
            "without_website": 0,
            "from_maps": 0,
            "from_google": 0,
            "from_duckduckgo": 0,
            "enriched": 0,
        },
        "sheet_url": None,
        "error": None,
    }

    thread = threading.Thread(
        target=run_scrape_task,
        args=(task_id, query, max_results, sheet_url, filter_type, sources),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id}), 202


@app.route("/api/progress/<task_id>")
def progress_stream(task_id):
    """SSE endpoint streaming log lines for a task."""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    def generate():
        task = tasks[task_id]
        log_queue = task["log_queue"]
        while True:
            try:
                msg = log_queue.get(timeout=1)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
                if task["status"] in ("completed", "error"):
                    final = json.dumps({
                        "done": True,
                        "status": task["status"],
                        "sheet_url": task["sheet_url"],
                        "counts": task["counts"],
                    })
                    yield f"data: {final}\n\n"
                    break

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/api/outreach-preview", methods=["GET"])
def outreach_preview():
    """Get lead campaign queue stats and HTML/Text email template preview."""
    sheet_url = request.args.get("sheet_url", "").strip() or DEFAULT_SHEET_URL
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")

    queue_count = 0
    total_leads = 0
    sent_count = 0

    if sheet_url and os.path.exists(credentials_path):
        try:
            leads = read_leads_from_sheet(sheet_url, credentials_path)
            total_leads = len(leads)
            for l in leads:
                status = l.get("email_status", "")
                emails = l.get("emails", "")
                if status == "Sent":
                    sent_count += 1
                elif emails and "@" in emails and emails.lower() != "not found":
                    queue_count += 1
        except Exception as e:
            app.logger.error(f"Error reading preview leads: {e}")

    sample_content = generate_email_content("Acme Software Inc", "Tokyo, Japan", "IT Consulting")

    return jsonify({
        "total_leads": total_leads,
        "queue_count": queue_count,
        "sent_count": sent_count,
        "sender_email": SENDER_EMAIL,
        "sender_name": SENDER_NAME,
        "sample_preview": sample_content
    })


@app.route("/api/send-outreach", methods=["POST"])
def start_outreach():
    """Launch SSE automated email outreach campaign task."""
    data = request.get_json() or {}
    sheet_url = (data.get("sheet_url") or "").strip() or DEFAULT_SHEET_URL

    if not sheet_url:
        return jsonify({"error": "Google Sheet URL is required."}), 400

    task_id = str(uuid.uuid4())
    outreach_tasks[task_id] = {
        "status": "pending",
        "log_queue": queue.Queue(),
        "total_queue": 0,
        "sent_count": 0,
        "failed_count": 0,
        "stopped": False
    }

    thread = threading.Thread(
        target=run_outreach_task,
        args=(task_id, sheet_url),
        daemon=True
    )
    thread.start()

    return jsonify({"task_id": task_id}), 202


@app.route("/api/send-outreach-from-sheet", methods=["POST"])
def start_outreach_from_sheet():
    """
    Launch an outreach campaign directly from the existing Google Sheet.
    Reads all 'Not Sent' leads from the sheet and sends emails sequentially.
    Functionally identical to /api/send-outreach — exists as a clear semantic
    endpoint for the frontend 'Send to Sheet Emails' tab.
    """
    data = request.get_json() or {}
    sheet_url = (data.get("sheet_url") or "").strip() or DEFAULT_SHEET_URL

    if not sheet_url:
        return jsonify({"error": "Google Sheet URL is required."}), 400

    task_id = str(uuid.uuid4())
    outreach_tasks[task_id] = {
        "status": "pending",
        "log_queue": queue.Queue(),
        "total_queue": 0,
        "sent_count": 0,
        "failed_count": 0,
        "stopped": False
    }

    thread = threading.Thread(
        target=run_outreach_task,
        args=(task_id, sheet_url),
        daemon=True
    )
    thread.start()

    return jsonify({"task_id": task_id}), 202


@app.route("/api/outreach-progress/<task_id>")
def outreach_progress_stream(task_id):
    """SSE endpoint for live outreach progress log streaming."""
    if task_id not in outreach_tasks:
        return jsonify({"error": "Task not found"}), 404

    def generate():
        task = outreach_tasks[task_id]
        log_queue = task["log_queue"]
        while True:
            try:
                msg = log_queue.get(timeout=1)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
                if task["status"] in ("completed", "error", "cancelled"):
                    final = json.dumps({
                        "done": True,
                        "status": task["status"],
                        "sent_count": task["sent_count"],
                        "failed_count": task["failed_count"],
                    })
                    yield f"data: {final}\n\n"
                    break

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/api/stop-outreach/<task_id>", methods=["POST"])
def stop_outreach(task_id):
    """Stop/cancel an in-progress outreach campaign."""
    if task_id in outreach_tasks:
        outreach_tasks[task_id]["stopped"] = True
        return jsonify({"success": True, "message": "Outreach cancellation requested."})
    return jsonify({"error": "Task not found"}), 404


@app.route("/api/test-email", methods=["POST"])
def test_email():
    """Send a test email to a specified test address."""
    data = request.get_json() or {}
    test_address = (data.get("test_email") or "").strip()
    if not test_address or "@" not in test_address:
        return jsonify({"error": "Valid test_email is required."}), 400

    content = generate_email_content("Test Partner", "Sample Location", "Test Industry")
    res = send_outreach_email(
        recipient_email=test_address,
        subject=f"[TEST] {content['subject']}",
        html_body=content["html_body"],
        text_body=content["text_body"]
    )
    if res["success"]:
        return jsonify({"success": True, "message": f"Test email sent to {test_address}"})
    return jsonify({"error": res["error"]}), 500


@app.route("/api/status/<task_id>")
def task_status(task_id):
    """Get current scrape task status."""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    task = tasks[task_id]
    return jsonify({
        "status": task["status"],
        "counts": task["counts"],
        "sheet_url": task["sheet_url"],
        "error": task["error"],
    })


@app.route("/api/clear-sheet", methods=["POST"])
def clear_sheet_endpoint():
    """Clear all data from both worksheets in the given sheet URL."""
    data = request.get_json()
    sheet_url = (data.get("sheet_url") or "").strip() or DEFAULT_SHEET_URL
    if not sheet_url:
        return jsonify({"error": "No sheet_url provided."}), 400

    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if not os.path.exists(credentials_path):
        return jsonify({"error": "credentials.json not found."}), 500

    try:
        clear_sheet(sheet_url, credentials_path)
        return jsonify({"success": True, "message": "Sheet cleared successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/service-account-email")
def service_account_email():
    """Return the service account email for sharing sheets."""
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if os.path.exists(credentials_path):
        email = get_service_account_email(credentials_path)
        return jsonify({"email": email})
    return jsonify({"email": None, "error": "credentials.json not found"}), 404


@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
