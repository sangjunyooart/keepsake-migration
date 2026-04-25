import logging
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from active_learning.source_adapters.base import Gap, SearchResult

if TYPE_CHECKING:
    from data_pipeline.ethics_filter import EthicsFilter
    from openclaw.client import OpenCLAWClient
    from active_learning.token_budget import TokenBudgetEnforcer

logger = logging.getLogger(__name__)

_EVAL_COST_PER_ITEM = 10
_BATCH_SIZE = 5
_RELEVANCE_THRESHOLD = 0.4
_QUALITY_THRESHOLD = 0.3


@dataclass
class Evaluation:
    result: SearchResult
    relevance: float
    quality: float
    ethics_safe: bool
    decision: str   # 'keep' or 'reject'


class ResultEvaluator:
    """
    Judges search results: ethics safety (free), then LLM relevance (batched, budget-aware).
    """

    def __init__(
        self,
        ethics_filter: "EthicsFilter",
        openclaw_client: "OpenCLAWClient",
        budget_enforcer: "TokenBudgetEnforcer",
    ):
        self.ethics = ethics_filter
        self.client = openclaw_client
        self.budget = budget_enforcer

    def evaluate_batch(self, results: List[SearchResult], gap: Gap) -> List[Evaluation]:
        evaluations = []
        safe_results = []
        for r in results:
            if not self.ethics.is_safe(r.content) or not self.ethics.is_safe(r.title):
                evaluations.append(Evaluation(
                    result=r, relevance=0.0, quality=0.0,
                    ethics_safe=False, decision="reject"
                ))
            else:
                safe_results.append(r)

        if not safe_results:
            return evaluations

        gap_context = f"{gap.period} {gap.location} — {', '.join(gap.suggested_topics[:2])}"
        relevance_scores = self._score_relevance_batched(safe_results, gap_context)
        quality_scores = [self._score_quality(r) for r in safe_results]

        for r, rel, qual in zip(safe_results, relevance_scores, quality_scores):
            keep = rel >= _RELEVANCE_THRESHOLD and qual >= _QUALITY_THRESHOLD
            evaluations.append(Evaluation(
                result=r,
                relevance=rel,
                quality=qual,
                ethics_safe=True,
                decision="keep" if keep else "reject",
            ))

        return evaluations

    def _score_relevance_batched(self, results: List[SearchResult], gap_context: str) -> List[float]:
        scores = []
        for i in range(0, len(results), _BATCH_SIZE):
            batch = results[i: i + _BATCH_SIZE]
            cost = len(batch) * _EVAL_COST_PER_ITEM
            if not self.budget.request(cost):
                scores.extend([0.5] * len(batch))
                continue
            if self.client.available:
                batch_scores = self._llm_relevance(batch, gap_context)
            else:
                batch_scores = self._keyword_relevance(batch, gap_context)
            scores.extend(batch_scores)
        return scores

    def _llm_relevance(self, batch: List[SearchResult], gap_context: str) -> List[float]:
        excerpt_block = "\n---\n".join(
            f"Text {i+1}: {r.content[:300]}" for i, r in enumerate(batch)
        )
        prompt = (
            f"Rate the relevance of each text to: '{gap_context}'\n"
            f"Rate 0.0 (irrelevant) to 1.0 (highly relevant). One number per line only.\n\n"
            f"{excerpt_block}"
        )
        result = self.client.generate(prompt, max_tokens=60)
        try:
            raw = [line.strip() for line in result.strip().split("\n") if line.strip()]
            scores = [float(x.split()[-1]) for x in raw]
            if len(scores) == len(batch):
                return [max(0.0, min(1.0, s)) for s in scores]
        except Exception:
            pass
        return [0.5] * len(batch)

    def _keyword_relevance(self, batch: List[SearchResult], gap_context: str) -> List[float]:
        keywords = gap_context.lower().split()
        scores = []
        for r in batch:
            text = (r.title + " " + r.content).lower()
            hits = sum(1 for kw in keywords if kw in text)
            scores.append(min(1.0, hits / max(1, len(keywords))))
        return scores

    def _score_quality(self, result: SearchResult) -> float:
        content_len = len(result.content.strip())
        if content_len < 50:
            return 0.1
        if content_len < 150:
            return 0.5
        return 0.8
