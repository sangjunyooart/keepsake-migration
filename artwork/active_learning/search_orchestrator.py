import hashlib
import logging
from typing import List, TYPE_CHECKING

from active_learning.source_adapters.base import Gap, SearchResult, SourceAdapter

if TYPE_CHECKING:
    from data_pipeline.ethics_filter import EthicsFilter

logger = logging.getLogger(__name__)

_MAX_RESULTS = 20


class SearchOrchestrator:
    """
    Dispatches search queries across all registered source adapters.
    Deduplicates by content hash and filters through ethics filter.
    """

    def __init__(self, adapters: List[SourceAdapter], ethics_filter: "EthicsFilter"):
        self.adapters = adapters
        self.ethics = ethics_filter

    def search(self, queries: List[str], gap: Gap) -> List[SearchResult]:
        raw: List[SearchResult] = []
        for query in queries:
            for adapter in self.adapters:
                try:
                    found = adapter.search(query, gap)
                    raw.extend(found)
                except Exception as e:
                    logger.warning(f"Adapter {adapter.name} failed for query '{query}': {e}")

        seen: set = set()
        unique: List[SearchResult] = []
        for result in raw:
            key = hashlib.md5((result.url + result.content[:80]).encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            if self.ethics.is_safe(result.content) and self.ethics.is_safe(result.title):
                unique.append(result)

        logger.debug(
            f"Search: {len(raw)} raw → {len(unique)} unique/safe results "
            f"for {gap.period}/{gap.location}"
        )
        return unique[:_MAX_RESULTS]
