"""Application configuration constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# Scraping delays (seconds)
MIN_DELAY = 1.0
MAX_DELAY = 3.0

# Maximum results cap
MAX_RESULTS_CAP = 500
DEFAULT_MAX_RESULTS = 100

# Google Sheets — loaded from .env (never hardcoded)
SHEET_NAME_TEMPLATE = "{niche} - {state} Leads"
DEFAULT_SHEET_URL = os.getenv("DEFAULT_SHEET_URL", "")

# Website scraper
REQUEST_TIMEOUT = 5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Pages to scan for emails/phones on business websites
CONTACT_PATHS = ["/", "/contact", "/about", "/contact-us", "/about-us"]

# Email noise filter domains
EMAIL_NOISE_DOMAINS = [
    "sentry.io",
    "wpcf7",
    "example.com",
    "example.org",
    "wordpress.org",
    "gravatar.com",
    "schema.org",
]
