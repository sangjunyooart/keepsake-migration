"""
Wikipedia search adapter — free API, no auth required.
Rate-limited to 1 req/s with exponential backoff on 429.
"""
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
TIMEOUT = 15
_HEADERS = {
    "User-Agent": (
        "Keepsake-Migration/1.0 "
        "(AI art installation research; "
        "https://github.com/sangjunyooart/keepsake-migration)"
    )
}
_MIN_INTERVAL = 1.0   # seconds between requests
_LAST_REQ: list[float] = [0.0]


def _get(params: dict, retries: int = 3) -> Optional[requests.Response]:
    """Rate-limited GET with exponential backoff on 429."""
    for attempt in range(retries):
        elapsed = time.time() - _LAST_REQ[0]
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        try:
            resp = requests.get(
                SEARCH_URL, params=params, headers=_HEADERS, timeout=TIMEOUT
            )
            _LAST_REQ[0] = time.time()

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5 * (2 ** attempt)))
                logger.warning("Wikipedia 429 — waiting %ds (attempt %d/%d)",
                               retry_after, attempt + 1, retries)
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp

        except requests.HTTPError:
            raise
        except requests.RequestException as exc:
            logger.warning("Wikipedia request error (attempt %d): %s", attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    return None


@dataclass
class SearchResult:
    title: str
    snippet: str
    page_id: int
    source: str = "wikipedia"


class WikipediaAdapter:
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
            "utf8": 1,
        }
        try:
            resp = _get(params)
            if resp is None:
                return []
            data = resp.json()
            return [
                SearchResult(
                    title=item["title"],
                    snippet=item.get("snippet", ""),
                    page_id=item["pageid"],
                )
                for item in data.get("query", {}).get("search", [])
            ]
        except Exception as exc:
            logger.warning("Wikipedia search failed for '%s': %s", query, exc)
            return []

    def fetch_content(self, result: SearchResult, max_chars: int = 4000) -> Optional[str]:
        params = {
            "action": "query",
            "pageids": result.page_id,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "format": "json",
        }
        try:
            resp = _get(params)
            if resp is None:
                return None
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                return extract[:max_chars] if extract else None
        except Exception as exc:
            logger.warning("Wikipedia fetch failed for page %d: %s", result.page_id, exc)
            return None
