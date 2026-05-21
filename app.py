"""Flask API server for the Google Maps Leads Scraper."""

import uuid
import threading
import json
import time
import queue
import os
from urllib.parse import urlparse

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

from config import DEFAULT_MAX_RESULTS, MAX_RESULTS_CAP, DEFAULT_SHEET_URL
from scraper.maps_scraper import scrape_google_maps
from scraper.website_scraper import extract_contact_info
from sheets.google_sheets import write_to_sheets, get_service_account_email

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# In-memory task store
tasks = {}


def run_scrape_task(task_id, niche, state, max_results, sheet_url=None, filter_type="both"):
    """Background thread that runs the full scraping pipeline."""
    task = tasks[task_id]
    log_queue = task["log_queue"]

    def emit(msg, level="info"):
        log_queue.put(json.dumps({"message": msg, "level": level, "time": time.time()}))

    try:
        emit(f"Starting scrape: '{niche}' in '{state}' (max {max_results} results)")
        task["status"] = "scraping_maps"

        # Step 1: Scrape Google Maps
        businesses = []
        for event in scrape_google_maps(niche, state, max_results):
            if event["type"] == "log":
                emit(event["message"], event.get("level", "info"))
            elif event["type"] == "result":
                businesses.append(event["data"])
                task["counts"]["total"] = len(businesses)

        emit(f"Google Maps scraping complete. Found {len(businesses)} businesses.", "success")

        # Step 2: Split into with/without website
        all_with_website = [b for b in businesses if b.get("website")]
        all_without_website = [b for b in businesses if not b.get("website")]

        # Apply filter
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

        # Step 3: Extract emails and phones from business websites
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

        # Step 4: Write to Google Sheets
        task["status"] = "writing_sheets"
        emit("Writing results to Google Sheets...")

        credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        if not os.path.exists(credentials_path):
            emit("ERROR: credentials.json not found. Cannot write to Google Sheets.", "error")
            task["status"] = "completed"
            task["sheet_url"] = None
        else:
            sheet_url = write_to_sheets(niche, state, with_website, without_website, credentials_path, sheet_url=sheet_url)
            task["sheet_url"] = sheet_url
            emit("Google Sheet updated successfully.", "success")
            task["status"] = "completed"

        emit("All done!", "success")

    except Exception as e:
        emit(f"Fatal error: {str(e)}", "error")
        task["status"] = "error"
        task["error"] = str(e)


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    """Start a new scraping task."""
    data = request.get_json()
    niche = data.get("niche", "").strip()
    state = data.get("state", "").strip()
    max_results = min(int(data.get("max_results", DEFAULT_MAX_RESULTS)), MAX_RESULTS_CAP)
    sheet_url = data.get("sheet_url", "").strip() or DEFAULT_SHEET_URL
    filter_type = data.get("filter", "both")

    if not niche or not state:
        return jsonify({"error": "Both 'niche' and 'state' are required."}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "log_queue": queue.Queue(),
        "counts": {"total": 0, "with_website": 0, "without_website": 0},
        "sheet_url": None,
        "error": None,
    }

    thread = threading.Thread(target=run_scrape_task, args=(task_id, niche, state, max_results, sheet_url, filter_type), daemon=True)
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
                # Send keepalive
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
                if task["status"] in ("completed", "error"):
                    # Send final status
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


@app.route("/api/status/<task_id>")
def task_status(task_id):
    """Get current task status."""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    task = tasks[task_id]
    return jsonify({
        "status": task["status"],
        "counts": task["counts"],
        "sheet_url": task["sheet_url"],
        "error": task["error"],
    })


@app.route("/api/service-account-email")
def service_account_email():
    """Return the service account email for sharing sheets."""
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if os.path.exists(credentials_path):
        email = get_service_account_email(credentials_path)
        return jsonify({"email": email})
    return jsonify({"email": None, "error": "credentials.json not found"}), 404


# Serve React frontend in production
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
