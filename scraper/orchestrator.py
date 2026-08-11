"""
Orchestrator: runs Google Maps, Google Search, and DuckDuckGo in parallel,
deduplicates results via a SHA-256 lead_id, then runs a cross-source
enrichment pass to fill missing fields from complementary sources.
"""

import hashlib
import re
import queue
import threading
import difflib
from typing import Generator, Dict, Any, List, Optional

from config import ENRICHMENT_NAME_SIMILARITY
from scraper.maps_scraper import scrape_google_maps, _create_driver
from scraper.google_search_scraper import scrape_google_search
from scraper.duckduckgo_scraper import scrape_duckduckgo


# ── Unique ID helpers ────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip, remove non-alphanumeric."""
    return re.sub(r'[^a-z0-9]', '', text.lower().strip())


def make_lead_id(name: str, phone: str, address: str) -> str:
    """
    Compute a deterministic 16-char SHA-256 hex ID from the normalised
    combination of name + phone digits + address.
    This is the single source of truth for uniqueness.
    """
    phone_digits = re.sub(r'\D', '', phone)
    raw = f"{_normalise(name)}|{phone_digits}|{_normalise(address)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Merge helpers ────────────────────────────────────────────────────────────

# Source priority for each field (first = highest priority)
_FIELD_SOURCE_PRIORITY = {
    "name":    ["google_maps", "google_search", "duckduckgo"],
    "phone":   ["google_maps", "duckduckgo",    "google_search"],
    "address": ["google_maps", "google_search", "duckduckgo"],
    "website": ["google_maps", "google_search", "duckduckgo"],
    "rating":  ["google_maps"],
    "reviews": ["google_maps"],
}

# Fields eligible for cross-source enrichment
_ENRICHABLE_FIELDS = ("phone", "address", "website")


def _source_rank(source_tag: str, field: str) -> int:
    """Lower number = higher priority for this field."""
    priority = _FIELD_SOURCE_PRIORITY.get(field, [])
    try:
        return priority.index(source_tag)
    except ValueError:
        return len(priority)  # unknown source goes last


def _merge_into(existing: Dict, incoming: Dict) -> bool:
    """
    Merge non-empty fields from `incoming` into `existing`, respecting
    source priority. Returns True if any field was updated.
    """
    updated = False
    incoming_source = incoming.get("source", "")

    for field in ("name", "phone", "address", "website", "rating", "reviews",
                  "category", "maps_url"):
        new_val = incoming.get(field, "").strip()
        if not new_val:
            continue

        existing_val = existing.get(field, "").strip()
        if not existing_val:
            # Empty slot — always fill
            existing[field] = new_val
            updated = True
        else:
            # Both have a value — defer to priority
            existing_source = existing.get("source", "")
            if _source_rank(incoming_source, field) < _source_rank(existing_source, field):
                existing[field] = new_val
                updated = True

    # Append incoming source tag if not already listed
    existing_sources = [s.strip() for s in existing.get("source", "").split(",") if s.strip()]
    if incoming_source and incoming_source not in existing_sources:
        existing["source"] = ", ".join(existing_sources + [incoming_source])
        updated = True

    return updated


# ── Name similarity ──────────────────────────────────────────────────────────

def _name_similarity(a: str, b: str) -> float:
    """Return SequenceMatcher similarity ratio between two normalised names."""
    return difflib.SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


# ── Cross-source enrichment ──────────────────────────────────────────────────

def _enrich_from_other_sources(
    leads: List[Dict],
    raw_by_source: Dict[str, List[Dict]],
) -> int:
    """
    Second pass: for each lead that is still missing phone / address / website,
    scan the raw results from every OTHER source for a name-similar match and
    fill in the missing field.

    Returns the number of leads that were enriched.
    """
    enriched_count = 0

    for lead in leads:
        lead_source = lead.get("source", "")
        missing = [f for f in _ENRICHABLE_FIELDS if not lead.get(f, "").strip()]
        if not missing:
            continue  # lead is already complete

        for src_name, src_results in raw_by_source.items():
            if src_name in lead_source:
                continue  # already used this source for this lead

            for candidate in src_results:
                sim = _name_similarity(lead.get("name", ""), candidate.get("name", ""))
                if sim < ENRICHMENT_NAME_SIMILARITY:
                    continue

                # Name match — fill whichever fields are still missing
                filled_any = False
                for field in missing:
                    val = candidate.get(field, "").strip()
                    if val and not lead.get(field, "").strip():
                        lead[field] = val
                        filled_any = True

                if filled_any:
                    # Update source attribution
                    existing_sources = [s.strip() for s in lead.get("source", "").split(",") if s.strip()]
                    if src_name not in existing_sources:
                        lead["source"] = ", ".join(existing_sources + [src_name])

                    lead["enriched"] = True
                    enriched_count += 1

                    # Refresh lead_id now that phone/address may have changed
                    lead["lead_id"] = make_lead_id(
                        lead.get("name", ""),
                        lead.get("phone", ""),
                        lead.get("address", ""),
                    )
                    break  # one candidate per source is enough

            # Recalculate missing after each source
            missing = [f for f in _ENRICHABLE_FIELDS if not lead.get(f, "").strip()]
            if not missing:
                break  # fully enriched

    return enriched_count


# ── Worker threads ───────────────────────────────────────────────────────────

def _run_maps_scraper(query: str, max_results: int, out_queue: queue.Queue):
    """Maps scraper manages its own browser internally."""
    try:
        for event in scrape_google_maps(query, max_results):
            out_queue.put(event)
    except Exception as e:
        out_queue.put({
            "type": "log",
            "message": f"Google Maps scraper error: {e}",
            "level": "error",
        })
    finally:
        out_queue.put({"type": "_done", "source": "google_maps"})


def _run_web_scrapers(
    query: str,
    max_results: int,
    out_queue: queue.Queue,
    run_google: bool,
    run_ddg: bool,
):
    """Google Search + DuckDuckGo share one browser to save memory."""
    web_driver = None
    try:
        web_driver = _create_driver()

        if run_google:
            try:
                for event in scrape_google_search(web_driver, query, max_results):
                    out_queue.put(event)
            except Exception as e:
                out_queue.put({"type": "log", "message": f"Google Search error: {e}", "level": "error"})
            finally:
                out_queue.put({"type": "_done", "source": "google_search"})

        if run_ddg:
            try:
                for event in scrape_duckduckgo(web_driver, query, max_results):
                    out_queue.put(event)
            except Exception as e:
                out_queue.put({"type": "log", "message": f"DuckDuckGo error: {e}", "level": "error"})
            finally:
                out_queue.put({"type": "_done", "source": "duckduckgo"})

    except Exception as e:
        out_queue.put({"type": "log", "message": f"Web scraper thread error: {e}", "level": "error"})
        if run_google:
            out_queue.put({"type": "_done", "source": "google_search"})
        if run_ddg:
            out_queue.put({"type": "_done", "source": "duckduckgo"})
    finally:
        if web_driver:
            web_driver.quit()


# ── Main orchestrator ────────────────────────────────────────────────────────

def scrape_all_sources(
    query: str,
    max_results: int,
    sources: Optional[List[str]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Run all requested scrapers in parallel, deduplicate by lead_id,
    then run cross-source enrichment to fill missing fields.

    Yields events:
      {"type": "log",     "message": "...", "level": "info|success|error"}
      {"type": "result",  "data": {...}}
      {"type": "summary", "counts": {...}}

    Parameters
    ----------
    query       : free-form search string, e.g. "Restaurants in London"
    max_results : target number of unique leads
    sources     : list of source tags to enable. Defaults to all three.
                  Valid: "google_maps", "google_search", "duckduckgo"
    """
    if sources is None:
        sources = ["google_maps", "google_search", "duckduckgo"]

    run_maps   = "google_maps"   in sources
    run_google = "google_search" in sources
    run_ddg    = "duckduckgo"    in sources

    yield {
        "type": "log",
        "message": f"Starting parallel scrape for \"{query}\" across: {', '.join(sources)}",
        "level": "info",
    }

    shared_queue: queue.Queue = queue.Queue()
    threads = []

    # ── Launch Maps thread ───────────────────────────────────────────────────
    if run_maps:
        t = threading.Thread(
            target=_run_maps_scraper,
            args=(query, max_results, shared_queue),
            daemon=True,
        )
        t.start()
        threads.append(t)

    # ── Launch web scrapers thread (Google Search + DDG share one browser) ───
    if run_google or run_ddg:
        t = threading.Thread(
            target=_run_web_scrapers,
            args=(query, max_results, shared_queue, run_google, run_ddg),
            daemon=True,
        )
        t.start()
        threads.append(t)

    # ── Collect & deduplicate ────────────────────────────────────────────────
    seen_ids: Dict[str, Dict] = {}          # lead_id → business dict
    raw_by_source: Dict[str, List] = {s: [] for s in sources}
    done_sources: set = set()
    expected_done = len(sources)  # one _done sentinel per source

    while len(done_sources) < expected_done:
        try:
            event = shared_queue.get(timeout=90)
        except queue.Empty:
            yield {"type": "log", "message": "Timeout waiting for scraper results.", "level": "error"}
            break

        if event["type"] == "_done":
            done_sources.add(event["source"])
            yield {
                "type": "log",
                "message": f"✓ {event['source'].replace('_', ' ').title()} finished.",
                "level": "info",
            }
            continue

        if event["type"] == "log":
            yield event
            continue

        if event["type"] == "result":
            biz = event["data"]
            src = biz.get("source", "unknown")

            # Store raw result for enrichment pass
            if src in raw_by_source:
                raw_by_source[src].append(dict(biz))  # copy for enrichment lookup

            # Compute deterministic unique ID
            lead_id = make_lead_id(
                biz.get("name", ""),
                biz.get("phone", ""),
                biz.get("address", ""),
            )
            biz["lead_id"] = lead_id
            biz.setdefault("enriched", False)

            if lead_id in seen_ids:
                # Same lead from another source — merge, don't duplicate
                _merge_into(seen_ids[lead_id], biz)
                yield {
                    "type": "log",
                    "message": f"Merged duplicate: \"{biz.get('name', '')}\" (from {src})",
                    "level": "info",
                }
            else:
                seen_ids[lead_id] = biz
                yield {"type": "result", "data": biz}

    # ── Cross-source enrichment pass ─────────────────────────────────────────
    all_leads = list(seen_ids.values())
    incomplete = [
        lead for lead in all_leads
        if any(not lead.get(f, "").strip() for f in _ENRICHABLE_FIELDS)
    ]

    if incomplete:
        yield {
            "type": "log",
            "message": f"Enrichment pass: {len(incomplete)} leads have missing fields. Checking other sources...",
            "level": "info",
        }
        enriched_count = _enrich_from_other_sources(incomplete, raw_by_source)
        yield {
            "type": "log",
            "message": f"Enrichment complete: filled missing data for {enriched_count} leads.",
            "level": "success",
        }
    else:
        yield {"type": "log", "message": "All leads are complete — no enrichment needed.", "level": "info"}

    # ── Summary ──────────────────────────────────────────────────────────────
    total = len(seen_ids)
    maps_count   = sum(1 for l in all_leads if "google_maps"   in l.get("source", ""))
    google_count = sum(1 for l in all_leads if "google_search" in l.get("source", ""))
    ddg_count    = sum(1 for l in all_leads if "duckduckgo"    in l.get("source", ""))
    enriched_total = sum(1 for l in all_leads if l.get("enriched"))

    yield {
        "type": "log",
        "message": (
            f"Scrape complete. Total unique leads: {total} "
            f"(Maps: {maps_count}, Google: {google_count}, DuckDuckGo: {ddg_count}, "
            f"Enriched: {enriched_total})"
        ),
        "level": "success",
    }

    yield {
        "type": "summary",
        "counts": {
            "from_maps": maps_count,
            "from_google": google_count,
            "from_duckduckgo": ddg_count,
            "enriched": enriched_total,
        },
    }
