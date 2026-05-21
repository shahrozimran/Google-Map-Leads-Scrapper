# Google Maps Leads Scraper

A Python (Flask) + React app that scrapes Google Maps for any niche + state, splits results into "with website" / "without website", extracts emails and phone numbers from business websites, and pushes everything to Google Sheets — served through a modern black-and-white React UI.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud service account with Sheets & Drive APIs enabled

### 2. Google Cloud Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project
2. Enable **Google Sheets API** and **Google Drive API**
3. Go to **IAM & Admin → Service Accounts** → create a new service account
4. Download the JSON key file and save it as `credentials.json` in the project root
5. The tool will auto-create sheets; no manual sharing needed

### 3. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Run Flask server
python app.py
```

The API server runs on `http://localhost:5000`.

### 4. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start dev server
npm run dev
```

The React dev server runs on `http://localhost:5173` and proxies `/api` requests to Flask.

### 5. Production Build

```bash
cd frontend
npm run build
```

Then just run `python app.py` — Flask will serve the built frontend from `frontend/dist`.

---

## Usage

1. Open the app in your browser
2. Enter a **Niche** (e.g., "Plumbers") and a **State** (e.g., "California")
3. Adjust the **Max Results** slider (20–500)
4. Click **Start Scraping**
5. Watch the live log stream as it scrapes Google Maps, visits business websites, and extracts contact info
6. When complete, click **Open Google Sheet** to view your leads

---

## Output

The tool creates a Google Sheet with two tabs:

**"With Website"** — businesses that have a website listed:
| Name | Category | Address | Phone | Email(s) | Website | Rating | Reviews | Maps URL |

**"Without Website"** — businesses without a website:
| Name | Category | Address | Phone | Rating | Reviews | Maps URL |

---

## Project Structure

```
Leads Scrapper/
├── app.py                    # Flask API server
├── config.py                 # Configuration constants
├── requirements.txt
├── credentials.json          # ← You provide this (service account key)
├── scraper/
│   ├── maps_scraper.py       # Playwright: Google Maps scraping
│   └── website_scraper.py    # Email + phone extraction from websites
├── sheets/
│   └── google_sheets.py      # gspread: write results to Sheets
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        └── components/
            ├── SearchForm.jsx
            ├── ProgressLog.jsx
            ├── StatsBanner.jsx
            └── ResultLink.jsx
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scrape` | Start a scraping task `{ niche, state, max_results }` |
| GET | `/api/progress/<task_id>` | SSE stream of log events |
| GET | `/api/status/<task_id>` | Current task status + results |

---

## Notes

- Google Maps may rate-limit or block excessive scraping. The tool uses random delays and realistic browser behavior to mitigate this.
- Website scraping has a 5-second timeout per page. Unreachable sites are skipped.
- Emails are deduplicated and noise-filtered (e.g., sentry, wordpress domains excluded).
- Phone numbers are validated as US 10-digit format.
