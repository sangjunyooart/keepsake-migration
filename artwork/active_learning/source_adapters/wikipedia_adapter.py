import logging
from typing import List

import requests

from active_learning.source_adapters.base import Gap, SearchResult, SourceAdapter

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
_TIMEOUT = 10


class WikipediaAdapter(SourceAdapter):
    name = "wikipedia"
    requires_api_key = False

    def search(self, query: str, gap: Gap) -> List[SearchResult]:
        try:
            resp = requests.get(
                _SEARCH_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 5,
                    "format": "json",
                    "utf8": 1,
                },
                headers={"User-Agent": "keepsake-migration/1.0 (research; contact@example.com)"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json().get("query", {}).get("search", [])
            results = []
            for item in items:
                snippet = item.get("snippet", "")
                snippet = snippet.replace('<span class="searchmatch">', "").replace("</span>", "")
                results.append(SearchResult(
                    url=f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                    title=item.get("title", ""),
                    content=snippet,
                    source=self.name,
                    gap_period=gap.period,
                    gap_location=gap.location,
                ))
            return results
        except Exception as e:
            logger.warning(f"Wikipedia search failed for '{query}': {e}")
            return []

    def fetch_content(self, result: SearchResult) -> str:
        try:
            title = result.title
            resp = requests.get(
                _SEARCH_URL,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "format": "json",
                    "utf8": 1,
                },
                headers={"User-Agent": "keepsake-migration/1.0 (research; contact@example.com)"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                return extract[:2000]
        except Exception as e:
            logger.warning(f"Wikipedia fetch failed for '{result.title}': {e}")
        return result.content
