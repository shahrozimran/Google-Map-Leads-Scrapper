# Google Maps Leads Generator & Cold Outreach Platform

A full-stack Python (Flask) + React web platform that scrapes high-value business leads across **Google Maps, Google Search, and DuckDuckGo**, enriches contact info (emails & phone numbers) from business websites, syncs structured data to **Google Sheets**, and launches **automated, deliverability-optimized cold email outreach campaigns** branded for **Stremly Studio** (`stremly.site`).

---

## 🌟 Key Features

### 🔍 1. Multi-Source Scraping & Entity Enrichment
- **Triple-Engine Scraping:** Extracts leads from **Google Maps** (Playwright), **Google Search**, and **DuckDuckGo**.
- **Cross-Source Entity Matching:** Intelligently merges and deduplicates leads from multiple sources using string similarity algorithms (`ENRICHMENT_NAME_SIMILARITY = 0.85`).
- **Website Contact Extractor:** Automatically scans business websites across key routes (`/`, `/contact`, `/about`, `/contact-us`, `/about-us`) for direct email addresses and phone numbers.
- **Noise Filtering:** Ignores non-business emails (`sentry.io`, `wpcf7`, `wordpress.org`, `gravatar.com`, `schema.org`).

### 📊 2. Live Google Sheets Synchronization
- **Dual Worksheet Organization:** Automatically splits results into **"With Website"** and **"Without Website"** worksheets.
- **Automated Professional Formatting:** Applies frozen headers, dark theme header styling, custom column widths, text wrapping, and alternating row banding.
- **3-State Lead Status Tracking:** Includes a dedicated **`Email Status`** column:
  - `Not Sent`: Valid lead email present, campaign pending.
  - `Sent`: Outreach email successfully delivered to recipient.
  - `NULL`: No email found for this lead.

### ✉️ 3. Free Automated Cold Email Outreach (Stremly Branded)
- **Built-in Gmail SMTP Engine:** Sends personalized outreach via Gmail TLS SMTP (`smtp.gmail.com:587`).
- **High-Converting Stremly Pitch Template:** Generates responsive HTML and plain-text emails (`multipart/alternative`) showcasing **Stremly Studio** (`stremly.site`) software & AI automation solutions.
- **Dynamic Variable Mapping:** Automatically injects `{business_name}` from the `Name` column, `{location}` from `Address`, and `{category}` from `Category`.
- **Primary Inbox & Anti-Spam Safeguards:**
  - **Randomized Throttling:** 5–12 second delay between emails to protect sender domain reputation and prevent spam flags.
  - **Zero Emojis & Clean Copy:** Bypasses promotional algorithms.
  - **Custom Branded Sender:** Sends as `Stremly <email@stremly.site>` with `Reply-To: email@stremly.site` backed by Cloudflare Email Routing.

### 🚀 4. Modern React Control Console & Modal
- **Live Terminal Stream:** Real-time color-coded console tracking scraping and email delivery progress via Server-Sent Events (SSE).
- **Outreach Campaign Modal:** View queue count, preview live HTML email templates, launch/stop campaigns, and test credentials.
- **Instant Test Email Tool:** Send live test emails to any address before launching full campaigns.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11+, Flask, Playwright (Chromium), `gspread`, `smtplib`, `dotenv`
- **Frontend:** React 18, Vite, TailwindCSS, Lucide Icons, EventSource (SSE)
- **Services:** Google Cloud Sheets & Drive APIs, Gmail SMTP, Cloudflare Email Routing

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud Service Account JSON Key (`credentials.json`)
- Gmail Account with 2-Step Verification & 16-Character App Password

---

### 2. Environment Setup (`.env`)

Create a `.env` file in the project root directory:

```env
DEFAULT_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit

# Outbound Sender Branding
SENDER_EMAIL=email@stremly.site
SENDER_NAME=Stremly

# Gmail Authentication
SMTP_USERNAME=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

---

### 3. Google Cloud Setup

1. Open [Google Cloud Console](https://console.cloud.google.com).
2. Enable **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** and download its JSON key file.
4. Save the key file as **`credentials.json`** in the project root directory.

---

### 4. Installation & Running

#### Backend (Flask Server)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser dependencies
playwright install chromium

# Start Flask server
python app.py
```
*Flask server will start on `http://localhost:5000`.*

#### Frontend (React App)
```bash
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```
*Frontend dev server will run on `http://localhost:5173`.*

#### Production Build
```bash
cd frontend
npm run build
```
*Flask automatically serves the production bundle from `frontend/dist` when accessed at `http://localhost:5000`.*

---

## 📖 Usage Guide

1. Open `http://localhost:5173` (or `http://localhost:5000`).
2. Enter your search **Query** (e.g., `"Plumbers in California"` or `"Car Dealers in Tokyo"`).
3. Select your desired data sources (**Google Maps**, **Google Search**, **DuckDuckGo**).
4. Set the **Max Results** cap and click **Start Scraping**.
5. When complete, click **Open Google Sheet** to inspect your leads.
6. Click **"✉️ Send Outreach Emails"** in the top header to open the Outreach Modal:
   - Review leads ready in the queue (`Not Sent`).
   - Switch to **"Send Test Email"** to test delivery to your inbox.
   - Click **"🚀 Launch Campaign"** to start automated cold outreach with live trace logging!

---

## 📁 Project Structure

```
Google Map Leads Generater/
├── app.py                      # Flask API server & SSE endpoints
├── config.py                   # Configuration parameters & environment loaders
├── email_templates.py          # Stremly HTML & Plain Text email generator
├── email_sender.py             # smtplib Gmail TLS outreach sender
├── requirements.txt            # Python dependencies
├── credentials.json            # Google Service Account JSON key (user provided)
├── .env                        # Environment configuration
├── scraper/
│   ├── orchestrator.py         # Parallel multi-source manager & entity deduplicator
│   ├── maps_scraper.py         # Playwright Google Maps scraper
│   ├── google_search_scraper.py# Google Search scraper
│   ├── duckduckgo_scraper.py   # DuckDuckGo scraper
│   └── website_scraper.py      # Website email & phone extractor
├── sheets/
│   └── google_sheets.py        # gspread integration & status tracking
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        └── components/
            ├── SearchForm.jsx
            ├── ProgressLog.jsx
            ├── StatsBanner.jsx
            ├── ResultLink.jsx
            └── EmailOutreachModal.jsx   # Outreach control modal & live console
```

---

## 🌐 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape` | Start scraping task `{ query, max_results, filter, sources }` |
| `GET` | `/api/progress/<task_id>` | SSE stream for real-time scraping progress logs |
| `GET` | `/api/status/<task_id>` | Get scraping task status & metrics |
| `POST` | `/api/clear-sheet` | Clear data rows and reset headers in Google Sheet |
| `GET` | `/api/service-account-email` | Fetch service account email for sharing sheets |
| `GET` | `/api/outreach-preview` | Get lead queue counts & HTML email preview |
| `POST` | `/api/send-outreach` | Launch background automated outreach campaign |
| `GET` | `/api/outreach-progress/<task_id>` | SSE stream for live outreach campaign log trace |
| `POST` | `/api/stop-outreach/<task_id>` | Cancel an in-progress email campaign |
| `POST` | `/api/test-email` | Send a test outreach email to a specific address |

---

## 🛡️ License & Branding

Branded for **Stremly Studio** (`https://stremly.site`) — Creative Software & AI Studio.
