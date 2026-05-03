"""
Wikipedia search adapter — free API, no auth required.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
TIMEOUT = 10
_HEADERS = {
    "User-Agent": "Keepsake-Migration/1.0 (AI art installation research; https://github.com/sangjunyooart/keepsake-migration)"
}


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
            resp = requests.get(SEARCH_URL, params=params, headers=_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                results.append(SearchResult(
                    title=item["title"],
                    snippet=item.get("snippet", ""),
                    page_id=item["pageid"],
                ))
            return results
        except Exception as e:
            logger.warning("Wikipedia search failed for '%s': %s", query, e)
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
            resp = requests.get(SEARCH_URL, params=params, headers=_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                return extract[:max_chars] if extract else None
        except Exception as e:
            logger.warning("Wikipedia fetch failed for page %d: %s", result.page_id, e)
            return None
