"""Google Maps + DuckDuckGo scraper using Selenium (headless Chrome)."""

import random
import time
import re
from urllib.parse import quote, urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import MIN_DELAY, MAX_DELAY


def _random_delay(minimum=None, maximum=None):
    """Sleep for a random duration to mimic human behavior."""
    time.sleep(random.uniform(minimum or MIN_DELAY, maximum or MAX_DELAY))


def _create_driver():
    """Create a headless Chrome WebDriver instance."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def scrape_google_maps(niche, state, max_results):
    """
    Generator that yields events:
      {"type": "log", "message": "...", "level": "info|success|error"}
      {"type": "result", "data": {...}}
    """
    search_query = f"{niche} in {state}"
    url = f"https://www.google.com/maps/search/{quote(search_query)}"

    yield {"type": "log", "message": f"Launching browser, searching: {search_query}", "level": "info"}

    driver = None
    try:
        driver = _create_driver()
        driver.get(url)
        _random_delay()

        yield {"type": "log", "message": "Page loaded. Scrolling results...", "level": "info"}

        # --- Phase 1: Scroll and collect all listing URLs ---
        scroll_attempts = 0
        max_scroll_attempts = 50
        prev_count = 0
        no_change_count = 0

        # Wait for the results feed
        feed_selector = 'div[role="feed"]'
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, feed_selector))
            )
        except Exception:
            feed_selector = 'div[role="main"]'

        while scroll_attempts < max_scroll_attempts:
            try:
                feed = driver.find_element(By.CSS_SELECTOR, feed_selector)
                driver.execute_script("arguments[0].scrollBy(0, 1000)", feed)
            except Exception:
                driver.execute_script("window.scrollBy(0, 1000)")

            time.sleep(1.5)
            scroll_attempts += 1

            # Check for end of results
            try:
                driver.find_element(By.CSS_SELECTOR, 'span.HlvSq')
                yield {"type": "log", "message": "Reached end of results list.", "level": "info"}
                break
            except Exception:
                pass

            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place"]')
            current_count = len(links)

            if current_count >= max_results:
                break

            if current_count == prev_count:
                no_change_count += 1
                if no_change_count >= 5:
                    break
            else:
                no_change_count = 0
            prev_count = current_count

            if scroll_attempts % 5 == 0:
                yield {"type": "log", "message": f"Scrolling... ({current_count} listings visible)", "level": "info"}

        # Collect all listing URLs
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place"]')
        listing_urls = []
        seen = set()
        for link in links[:max_results]:
            href = link.get_attribute("href") or ""
            name = (link.get_attribute("aria-label") or "").strip()
            if href and href not in seen:
                seen.add(href)
                listing_urls.append({"url": href, "name": name})

        yield {"type": "log", "message": f"Collected {len(listing_urls)} unique listing URLs. Extracting details...", "level": "info"}

        # --- Phase 2: Visit each listing URL and extract details ---
        results_collected = 0
        for i, item in enumerate(listing_urls):
            try:
                driver.get(item["url"])
                time.sleep(2)

                business = _extract_from_detail_page(driver, item["name"], item["url"])
                if business:
                    results_collected += 1
                    yield {"type": "result", "data": business}

                    if results_collected % 5 == 0:
                        yield {"type": "log", "message": f"Extracted {results_collected}/{len(listing_urls)} businesses...", "level": "info"}

                _random_delay(0.5, 1.5)

            except Exception as e:
                yield {"type": "log", "message": f"Error on listing {i+1}: {str(e)}", "level": "error"}

        maps_count = results_collected
        yield {"type": "log", "message": f"Google Maps: extracted {maps_count} businesses.", "level": "success"}

        # --- Phase 3: DuckDuckGo fallback if not enough results ---
        if results_collected < max_results:
            remaining = max_results - results_collected
            yield {"type": "log", "message": f"Only {results_collected}/{max_results} found. Searching DuckDuckGo for {remaining} more...", "level": "info"}

            for event in _scrape_duckduckgo(driver, niche, state, remaining, seen):
                if event["type"] == "result":
                    results_collected += 1
                yield event

        yield {"type": "log", "message": f"Extraction complete. Total: {results_collected} businesses.", "level": "success"}

    except Exception as e:
        yield {"type": "log", "message": f"Browser error: {str(e)}", "level": "error"}
    finally:
        if driver:
            driver.quit()


def _extract_from_detail_page(driver, name, maps_url):
    """Extract business details from a Google Maps detail page."""
    business = {
        "name": name,
        "category": "",
        "address": "",
        "phone": "",
        "rating": "",
        "reviews": "",
        "website": "",
        "maps_url": maps_url,
    }

    try:
        # Wait for detail content to load
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h1, [data-item-id]'))
        )

        # Name from h1 (more reliable than aria-label)
        try:
            h1 = driver.find_element(By.CSS_SELECTOR, 'h1')
            if h1.text.strip():
                business["name"] = h1.text.strip()
        except Exception:
            pass

        # Category
        for sel in ['button[jsaction*="category"]', 'span.DkEaL', 'button[jsaction*="pane.rating.category"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                text = el.text.strip()
                if text:
                    business["category"] = text
                    break
            except Exception:
                continue

        # Address
        for sel in ['button[data-item-id="address"]', '[data-item-id="address"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                text = el.get_attribute("aria-label") or el.text or ""
                text = text.replace("Address: ", "").strip()
                if text:
                    business["address"] = text
                    break
            except Exception:
                continue

        # Phone
        for sel in ['button[data-item-id*="phone"]', '[data-item-id*="phone"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                text = el.get_attribute("aria-label") or el.text or ""
                text = text.replace("Phone: ", "").strip()
                if text:
                    business["phone"] = text
                    break
            except Exception:
                continue

        # Website
        for sel in ['a[data-item-id="authority"]', 'a[data-item-id*="authority"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                href = el.get_attribute("href") or ""
                if href and "google.com" not in href:
                    business["website"] = href
                    break
            except Exception:
                continue

        # Rating — try multiple approaches
        try:
            # Look for the rating number in the header area
            rating_spans = driver.find_elements(By.CSS_SELECTOR, 'div.F7nice span')
            for span in rating_spans:
                text = span.get_attribute("aria-hidden")
                if text and re.match(r'^\d+\.?\d*$', text.strip()):
                    business["rating"] = text.strip()
                    break
                text = span.text.strip()
                if re.match(r'^\d+\.?\d*$', text):
                    business["rating"] = text
                    break
        except Exception:
            pass

        if not business["rating"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]')
                text = el.text.strip()
                if re.match(r'^\d+\.?\d*$', text):
                    business["rating"] = text
            except Exception:
                pass

        # Reviews count
        try:
            review_els = driver.find_elements(By.CSS_SELECTOR, 'span[aria-label*="review"]')
            for rel in review_els:
                rtext = rel.get_attribute("aria-label") or ""
                rmatch = re.search(r'([\d,]+)\s*review', rtext)
                if rmatch:
                    business["reviews"] = rmatch.group(1).replace(",", "")
                    break
        except Exception:
            pass

        if not business["reviews"]:
            try:
                # Try to find review count in parentheses like (123)
                spans = driver.find_elements(By.CSS_SELECTOR, 'span')
                for span in spans:
                    text = span.text.strip()
                    rmatch = re.match(r'^\(?([\d,]+)\)?$', text)
                    if rmatch and len(rmatch.group(1).replace(",", "")) >= 1:
                        val = rmatch.group(1).replace(",", "")
                        if val.isdigit() and int(val) < 100000:
                            business["reviews"] = val
                            break
            except Exception:
                pass

    except Exception:
        pass

    return business


def _scrape_duckduckgo(driver, niche, state, max_results, seen_urls):
    """
    Fallback: search DuckDuckGo for businesses and extract basic info.
    Yields same event format as scrape_google_maps.
    """
    query = f"{niche} in {state} address phone"
    ddg_url = f"https://duckduckgo.com/?q={quote(query)}"

    yield {"type": "log", "message": f"DuckDuckGo search: {query}", "level": "info"}

    try:
        driver.get(ddg_url)
        time.sleep(3)

        results = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="result"]')
        if not results:
            results = driver.find_elements(By.CSS_SELECTOR, '.result')

        yield {"type": "log", "message": f"DuckDuckGo: found {len(results)} search results", "level": "info"}

        collected = 0
        for result in results:
            if collected >= max_results:
                break

            try:
                # Extract title
                title_el = result.find_element(By.CSS_SELECTOR, 'h2 a, a[data-testid="result-title-a"]')
                title = title_el.text.strip()
                link = title_el.get_attribute("href") or ""

                if not title or link in seen_urls:
                    continue
                seen_urls.add(link)

                # Extract snippet text
                snippet = ""
                try:
                    snippet_el = result.find_element(By.CSS_SELECTOR, 'span[data-testid="result-snippet"], .result__snippet')
                    snippet = snippet_el.text.strip()
                except Exception:
                    pass

                # Try to extract phone from snippet
                phone = ""
                phone_match = re.search(r'(\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}', snippet)
                if phone_match:
                    phone = phone_match.group(0).strip()

                # Try to extract address-like text from snippet
                address = ""
                addr_match = re.search(r'\d+\s+[\w\s]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl|Pkwy|Hwy)[\w\s,]*(?:\d{5})?', snippet, re.IGNORECASE)
                if addr_match:
                    address = addr_match.group(0).strip()

                business = {
                    "name": title,
                    "category": niche,
                    "address": address,
                    "phone": phone,
                    "rating": "",
                    "reviews": "",
                    "website": link if "google.com" not in link else "",
                    "maps_url": "",
                }

                collected += 1
                yield {"type": "result", "data": business}

            except Exception:
                continue

        yield {"type": "log", "message": f"DuckDuckGo: extracted {collected} additional businesses.", "level": "success"}

    except Exception as e:
        yield {"type": "log", "message": f"DuckDuckGo error: {str(e)}", "level": "error"}
