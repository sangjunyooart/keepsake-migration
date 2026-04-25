import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .decisions import OpenCLAWDecisions
    from active_learning.token_budget import TokenBudgetEnforcer

logger = logging.getLogger(__name__)

_QUERY_GEN_COST = 30   # estimated tokens per query-generation call
_EVAL_COST_PER_ITEM = 10  # estimated tokens per evaluated result


class BudgetAwareDecisions:
    """
    Wraps OpenCLAWDecisions with budget enforcement.
    Falls back to heuristic methods when budget is exhausted.
    """

    def __init__(self, decisions: "OpenCLAWDecisions", budget: "TokenBudgetEnforcer"):
        self.decisions = decisions
        self.budget = budget

    def generate_search_queries(
        self, period: str, location: str, lens_topic: str, max_queries: int = 3
    ) -> List[str]:
        if not self.budget.request(_QUERY_GEN_COST):
            logger.info("Token budget exhausted — using fallback queries")
            return self.decisions._fallback_queries(period, location, lens_topic)
        return self.decisions.generate_search_queries(period, location, lens_topic, max_queries)

    def evaluate_relevance(self, texts: List[str], gap_context: str) -> List[float]:
        cost = max(1, len(texts) * _EVAL_COST_PER_ITEM)
        if not self.budget.request(cost):
            logger.info("Token budget exhausted — using default relevance scores")
            return [0.5] * len(texts)
        return self.decisions.evaluate_relevance(texts, gap_context)
