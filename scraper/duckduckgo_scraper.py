"""DuckDuckGo scraper: extracts business leads from DuckDuckGo search results."""

import re
import time
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import DUCKDUCKGO_MAX_PAGES, MIN_DELAY


# ── International phone regex ────────────────────────────────────────────────
# Matches: +44 20 7946 0958 | +91 98765 43210 | 030 12345678 | (212) 555-1234
PHONE_RE = re.compile(
    r'(?:\+\d{1,3}[\s.\-]?)?'         # optional country code e.g. +44
    r'(?:\(?\d{1,4}\)?[\s.\-]?)?'     # optional area code / trunk prefix
    r'\d{2,5}'                         # first block
    r'[\s.\-]?\d{2,5}'                 # second block
    r'(?:[\s.\-]?\d{2,5})?'           # optional third block
)

# ── International address regex ──────────────────────────────────────────────
ADDR_RE = re.compile(
    r'\d[\d\s\-]*\s+[\w\s\-\.]{3,}(?:,\s*[\w\s\-\.]+){1,4}(?:\s+[\d]{3,10})?',
    re.IGNORECASE | re.UNICODE,
)


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


def scrape_duckduckgo(driver, query, max_results):
    """
    Generator that yields events from DuckDuckGo web search.

    Events:
      {"type": "log",    "message": "...", "level": "info|success|error"}
      {"type": "result", "data": {...},    "source": "duckduckgo"}

    Parameters
    ----------
    driver      : Selenium WebDriver (already created by caller)
    query       : free-form search string, e.g. "Restaurants in London"
    max_results : int  – maximum number of results to yield
    """
    search_query = f"{query} address phone contact"
    collected = 0
    seen_urls: set[str] = set()

    yield {"type": "log", "message": f"DuckDuckGo: searching — \"{query}\"", "level": "info"}

    for page in range(DUCKDUCKGO_MAX_PAGES):
        if collected >= max_results:
            break

        # DuckDuckGo uses `s=` offset (25 per page after the first)
        offset = page * 25
        if page == 0:
            url = f"https://duckduckgo.com/?q={quote(search_query)}&ia=web"
        else:
            url = (
                f"https://duckduckgo.com/?q={quote(search_query)}"
                f"&s={offset}&dc={offset + 1}&ia=web&iai=&start={offset}"
            )

        try:
            driver.get(url)
            time.sleep(3)

            # Wait for results to appear
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'article[data-testid="result"], .result')
                    )
                )
            except Exception:
                yield {
                    "type": "log",
                    "message": f"DuckDuckGo page {page + 1}: no results found.",
                    "level": "error",
                }
                break

            results = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="result"]')
            if not results:
                results = driver.find_elements(By.CSS_SELECTOR, '.result')

            if not results:
                yield {
                    "type": "log",
                    "message": f"DuckDuckGo page {page + 1}: empty result page.",
                    "level": "info",
                }
                break

            yield {
                "type": "log",
                "message": f"DuckDuckGo page {page + 1}: found {len(results)} results.",
                "level": "info",
            }

            for result in results:
                if collected >= max_results:
                    break

                try:
                    # Title + URL
                    title_el = result.find_element(
                        By.CSS_SELECTOR, 'h2 a, a[data-testid="result-title-a"]'
                    )
                    title = title_el.text.strip()
                    link = title_el.get_attribute("href") or ""

                    if not title or not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Snippet text
                    snippet = ""
                    try:
                        snippet_el = result.find_element(
                            By.CSS_SELECTOR,
                            'span[data-testid="result-snippet"], .result__snippet',
                        )
                        snippet = snippet_el.text.strip()
                    except Exception:
                        pass

                    phone = _parse_phone(snippet)
                    address = _parse_address(snippet)

                    business = {
                        "name": title,
                        "category": "",
                        "address": address,
                        "phone": phone,
                        "rating": "",
                        "reviews": "",
                        "website": link if "google.com" not in link else "",
                        "maps_url": "",
                        "source": "duckduckgo",
                    }

                    collected += 1
                    yield {"type": "result", "data": business}

                except Exception:
                    continue

            # Small delay between pages
            time.sleep(MIN_DELAY)

        except Exception as e:
            yield {
                "type": "log",
                "message": f"DuckDuckGo page {page + 1} error: {e}",
                "level": "error",
            }
            break

    yield {
        "type": "log",
        "message": f"DuckDuckGo: extracted {collected} leads.",
        "level": "success",
    }
