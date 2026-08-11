"""Google Maps scraper using Selenium (headless Chrome)."""

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
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US,en")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """
    })
    return driver


def scrape_google_maps(query, max_results):
    """
    Generator that yields events:
      {"type": "log", "message": "...", "level": "info|success|error"}
      {"type": "result", "data": {...}}

    Parameters
    ----------
    query       : free-form search query, e.g. "Restaurants in London"
    max_results : int
    """
    url = f"https://www.google.com/maps/search/{quote(query)}"

    yield {"type": "log", "message": f"Google Maps: searching — \"{query}\"", "level": "info"}

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
                    # Tag the source so the orchestrator can track origin
                    business["source"] = "google_maps"
                    yield {"type": "result", "data": business}

                    if results_collected % 5 == 0:
                        yield {"type": "log", "message": f"Extracted {results_collected}/{len(listing_urls)} businesses...", "level": "info"}

                _random_delay(0.5, 1.5)

            except Exception as e:
                yield {"type": "log", "message": f"Error on listing {i+1}: {str(e)}", "level": "error"}

        maps_count = results_collected
        yield {"type": "log", "message": f"Google Maps: extracted {maps_count} businesses.", "level": "success"}

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

