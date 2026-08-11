"""Website scraper: extracts emails and phone numbers from business websites."""

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT, CONTACT_PATHS, EMAIL_NOISE_DOMAINS

# Regex patterns
EMAIL_REGEX = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
# International phone: optional country code (+XX), then 7-15 digit number in any grouping
PHONE_REGEX = re.compile(
    r'(?:\+\d{1,3}[\s.\-]?)?'      # optional country code, e.g. +44
    r'(?:\(?\d{1,4}\)?[\s.\-]?)?'   # optional area/trunk prefix
    r'\d{2,5}'                         # first digit block
    r'[\s.\-]?\d{2,5}'                # second digit block
    r'(?:[\s.\-]?\d{2,5})?'           # optional third block
)


def _fetch_page(url):
    """Fetch a page and return its text content, or None on failure."""
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


def _is_valid_email(email):
    """Filter out noise emails."""
    email_lower = email.lower()
    for noise in EMAIL_NOISE_DOMAINS:
        if noise in email_lower:
            return False
    # Filter image/file extensions mistakenly matched
    if email_lower.endswith((".png", ".jpg", ".gif", ".svg", ".webp", ".css", ".js")):
        return False
    return True


def _is_valid_phone(phone_str):
    """Validate phone number: must have 7-15 digits (ITU-T E.164 international standard)."""
    digits = re.sub(r'\D', '', phone_str)
    return 7 <= len(digits) <= 15


def extract_contact_info(website_url):
    """
    Scan a business website for emails and phone numbers.
    Returns: {"emails": [...], "phone": "..." or "Not Found"}
    """
    emails_found = set()
    phones_found = []

    # Normalize base URL
    if not website_url.startswith("http"):
        website_url = "https://" + website_url
    base_url = website_url.rstrip("/")

    for path in CONTACT_PATHS:
        url = urljoin(base_url + "/", path.lstrip("/"))
        html = _fetch_page(url)
        if not html:
            continue

        # Remove script and style tags for cleaner extraction
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ")

        # Extract emails
        raw_emails = EMAIL_REGEX.findall(text)
        # Also check href="mailto:..." links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("mailto:"):
                raw_emails.append(href.replace("mailto:", "").split("?")[0])

        for email in raw_emails:
            if _is_valid_email(email):
                emails_found.add(email.lower())

        # Extract phones
        raw_phones = PHONE_REGEX.findall(text)
        # Also check href="tel:..." links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("tel:"):
                phone_val = href.replace("tel:", "").strip()
                if _is_valid_phone(phone_val):
                    phones_found.append(phone_val)

        # findall with groups returns tuples; search full matches instead
        for match in PHONE_REGEX.finditer(text):
            phone_str = match.group(0)
            if _is_valid_phone(phone_str):
                phones_found.append(phone_str.strip())

    # Deduplicate emails
    emails_list = sorted(emails_found)

    # Pick first valid phone
    phone = phones_found[0] if phones_found else "Not Found"

    return {
        "emails": emails_list if emails_list else ["Not Found"],
        "phone": phone,
    }
