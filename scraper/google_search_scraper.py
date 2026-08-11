"""Google Web Search scraper: extracts business leads from Google search results."""

import re
import time
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import GOOGLE_SEARCH_MAX_PAGES, MIN_DELAY


# ── International phone regex ────────────────────────────────────────────────
# Matches: +44 20 7946 0958 | +91 98765 43210 | 030 12345678 | (212) 555-1234
PHONE_RE = re.compile(
    r'(?:\+\d{1,3}[\s.\-]?)?'         # optional country code e.g. +44
    r'(?:\(?\d{1,4}\)?[\s.\-]?)?'     # optional area code / trunk prefix
    r'\d{2,5}'                         # first block of digits
    r'[\s.\-]?\d{2,5}'                 # second block
    r'(?:[\s.\-]?\d{2,5})?'           # optional third block
)

# ── International address regex ──────────────────────────────────────────────
# Matches: "123 Main St, London" | "45 Rue de Rivoli, Paris 75001" | "新宿区1-2-3" etc.
# Strategy: look for digit(s) followed by text with at least one comma — covers most world formats.
ADDR_RE = re.compile(
    r'\d[\d\s\-]*\s+[\w\s\-\.]{3,}(?:,\s*[\w\s\-\.]+){1,4}(?:\s+[\d]{3,10})?',
    re.IGNORECASE | re.UNICODE,
)

# Domains to exclude from results (search engines, social media, directories)
EXCLUDED_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "linkedin.com", "yelp.com", "tripadvisor.com",
    "wikipedia.org", "reddit.com", "yellowpages.com", "bbb.org",
    "mapquest.com", "apple.com", "amazon.com",
}


def _parse_phone(text):
    """Return the first plausible international phone number found in text."""
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r'\D', '', m.group(0))
        if 7 <= len(digits) <= 15:   # ITU-T E.164: max 15 digits, min ~7
            return m.group(0).strip()
    return ""


def _parse_address(text):
    """Return the first address-like string found in text, or empty string."""
    m = ADDR_RE.search(text)
    return m.group(0).strip() if m else ""


def _is_excluded(url):
    """Return True if the URL belongs to an excluded domain."""
    for domain in EXCLUDED_DOMAINS:
        if domain in url:
            return True
    return False


def scrape_google_search(driver, query, max_results):
    """
    Generator that yields events from Google Web Search.

    Events:
      {"type": "log",    "message": "...", "level": "info|success|error"}
      {"type": "result", "data": {...},    "source": "google_search"}

    Parameters
    ----------
    driver      : Selenium WebDriver (already created by caller)
    query       : free-form search string, e.g. "Restaurants in London"
    max_results : int  – maximum number of results to yield
    """
    # Append contact-info hints to help surface business pages
    search_query = f"{query} contact phone address"
    collected = 0
    seen_urls: set[str] = set()

    yield {"type": "log", "message": f"Google Search: searching — \"{query}\"", "level": "info"}

    for page in range(GOOGLE_SEARCH_MAX_PAGES):
        if collected >= max_results:
            break

        start = page * 10
        url = (
            f"https://www.google.com/search?q={quote(search_query)}"
            f"&start={start}&hl=en&num=10"
        )

        try:
            driver.get(url)
            time.sleep(2.5)

            # Check and dismiss Google consent modal if present
            try:
                consent_selectors = [
                    'button#L2AGLb',
                    'form[action*="consent"] button',
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="Agree"]',
                ]
                for sel in consent_selectors:
                    buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                    if buttons and buttons[0].is_displayed():
                        buttons[0].click()
                        time.sleep(1.5)
                        break
            except Exception:
                pass

            # Wait for organic results with broader selector
            try:
                WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '#rso, div#search, div.g, div.tF2Cxc, div.MjjYud')
                    )
                )
            except Exception:
                # Check if CAPTCHA or blocking occurred
                page_title = driver.title.lower()
                if "sorry" in page_title or "captcha" in page_title or "unusual traffic" in driver.page_source.lower():
                    yield {
                        "type": "log",
                        "message": f"Google Search page {page + 1}: Google CAPTCHA / rate-limit detected.",
                        "level": "error",
                    }
                else:
                    yield {
                        "type": "log",
                        "message": f"Google Search page {page + 1}: no search results container found.",
                        "level": "error",
                    }
                break

            # Collect organic result blocks using updated selectors
            result_blocks = driver.find_elements(
                By.CSS_SELECTOR, '#rso > div, div.g, div.tF2Cxc, div.MjjYud, div[data-hveid]'
            )
            if not result_blocks:
                result_blocks = driver.find_elements(By.CSS_SELECTOR, 'div#search div.g')

            if not result_blocks:
                yield {
                    "type": "log",
                    "message": f"Google Search page {page + 1}: 0 result items matched.",
                    "level": "info",
                }
                break

            yield {
                "type": "log",
                "message": f"Google Search page {page + 1}: found {len(result_blocks)} result blocks.",
                "level": "info",
            }

            for block in result_blocks:
                if collected >= max_results:
                    break

                try:
                    # Title from h3
                    try:
                        title_el = block.find_element(By.CSS_SELECTOR, 'h3')
                        title = title_el.text.strip()
                    except Exception:
                        continue

                    if not title:
                        continue

                    # URL from the anchor wrapping the h3
                    link = ""
                    try:
                        anchor = block.find_element(By.CSS_SELECTOR, 'a[href]')
                        link = anchor.get_attribute("href") or ""
                        # Strip Google redirect wrapper if present
                        if link.startswith("/url?"):
                            m = re.search(r'[?&]q=([^&]+)', link)
                            if m:
                                from urllib.parse import unquote
                                link = unquote(m.group(1))
                    except Exception:
                        pass

                    if not link or link in seen_urls or _is_excluded(link):
                        continue
                    seen_urls.add(link)

                    # Snippet text
                    snippet = ""
                    for snippet_sel in [
                        'div.VwiC3b', 'span.aCOpRe', 'div.s', '.st',
                        'div[data-sncf]', 'div.IsZvec',
                    ]:
                        try:
                            snippet_el = block.find_element(By.CSS_SELECTOR, snippet_sel)
                            snippet = snippet_el.text.strip()
                            if snippet:
                                break
                        except Exception:
                            continue

                    phone = _parse_phone(snippet)
                    address = _parse_address(snippet)

                    business = {
                        "name": title,
                        "category": "",
                        "address": address,
                        "phone": phone,
                        "rating": "",
                        "reviews": "",
                        "website": link,
                        "maps_url": "",
                        "source": "google_search",
                    }

                    collected += 1
                    yield {"type": "result", "data": business}

                except Exception:
                    continue

            # Respect rate limits
            time.sleep(MIN_DELAY + 1)

        except Exception as e:
            yield {
                "type": "log",
                "message": f"Google Search page {page + 1} error: {e}",
                "level": "error",
            }
            break

    yield {
        "type": "log",
        "message": f"Google Search: extracted {collected} leads.",
        "level": "success",
    }
