"""
Runs queries across all configured source adapters for a given gap.
"""
import logging
from typing import List

from mac.active_learning.self_assessment import Gap
from mac.active_learning.query_generator import QueryGenerator
from mac.active_learning.source_adapters.wikipedia_adapter import WikipediaAdapter, SearchResult as WikiResult
from mac.active_learning.source_adapters.noaa_adapter import NOAAAdapter

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    def __init__(self):
        self.query_gen = QueryGenerator()
        self.wikipedia = WikipediaAdapter()
        self.noaa = NOAAAdapter()

    def search_gap(self, gap: Gap) -> list[dict]:
        """
        Run search for a gap. Returns list of raw result dicts with text content.
        """
        queries = self.query_gen.generate(gap)
        results = []
        for query in queries[:3]:  # limit queries per gap to avoid rate limits
            wiki_results = self.wikipedia.search(query, max_results=3)
            for r in wiki_results:
                content = self.wikipedia.fetch_content(r)
                if content:
                    results.append({
                        "source": "wikipedia",
                        "query": query,
                        "title": r.title,
                        "text": content,
                    })
            noaa_results = self.noaa.search(query, location=gap.location, period=gap.period)
            for r in noaa_results:
                if r.snippet:
                    results.append({
                        "source": "noaa",
                        "query": query,
                        "title": r.title,
                        "text": r.snippet,
                    })
        logger.info("Search for gap '%s/%s' returned %d results", gap.lens_type, gap.period, len(results))
        return results
