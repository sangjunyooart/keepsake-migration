import logging
from typing import List, TYPE_CHECKING

from active_learning.source_adapters.base import Gap

if TYPE_CHECKING:
    from openclaw.client import OpenCLAWClient
    from active_learning.token_budget import TokenBudgetEnforcer

logger = logging.getLogger(__name__)

_QUERY_GEN_COST = 30


class QueryGenerator:
    """
    LLM-driven search query generation for identified gaps.
    Budget-aware: returns empty list if daily budget would be exceeded.
    """

    def __init__(self, openclaw_client: "OpenCLAWClient", budget_enforcer: "TokenBudgetEnforcer"):
        self.client = openclaw_client
        self.budget = budget_enforcer

    def generate_queries(self, gap: Gap, max_queries: int = 3) -> List[str]:
        if not self.budget.request(_QUERY_GEN_COST):
            logger.info(f"Token budget exhausted — skipping query generation for {gap.period}/{gap.location}")
            return []

        if not self.client.available:
            return self._heuristic_queries(gap, max_queries)

        topics = ", ".join(gap.suggested_topics[:3]) if gap.suggested_topics else "historical records"
        prompt = (
            f"Generate {max_queries} precise search queries to find historical records "
            f"about the period '{gap.period}' in '{gap.location}' related to '{topics}'. "
            f"Return only the queries, one per line, no numbering."
        )
        result = self.client.generate(prompt, max_tokens=120)
        if not result:
            return self._heuristic_queries(gap, max_queries)

        queries = [q.strip() for q in result.strip().split("\n") if q.strip()]
        queries = queries[:max_queries]
        return queries if queries else self._heuristic_queries(gap, max_queries)

    def _heuristic_queries(self, gap: Gap, max_queries: int) -> List[str]:
        topic = gap.suggested_topics[0] if gap.suggested_topics else "history"
        base = [
            f"{gap.location} {gap.period} {topic}",
            f"historical records {gap.location} {gap.period}",
            f"{gap.location} {topic} archive",
        ]
        return base[:max_queries]
