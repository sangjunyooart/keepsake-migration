import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import OpenCLAWClient

logger = logging.getLogger(__name__)


class OpenCLAWDecisions:
    """LLM-driven decisions: query generation and relevance evaluation."""

    def __init__(self, client: "OpenCLAWClient"):
        self.client = client

    def generate_search_queries(
        self, period: str, location: str, lens_topic: str, max_queries: int = 3
    ) -> List[str]:
        if not self.client.available:
            return self._fallback_queries(period, location, lens_topic)
        prompt = (
            f"Generate {max_queries} precise search queries to find historical records about "
            f"the period '{period}' in '{location}' related to '{lens_topic}'. "
            f"Return only the queries, one per line, no numbering, no punctuation."
        )
        result = self.client.generate(prompt, max_tokens=120)
        if not result:
            return self._fallback_queries(period, location, lens_topic)
        queries = [q.strip() for q in result.strip().split("\n") if q.strip()]
        return queries[:max_queries] or self._fallback_queries(period, location, lens_topic)

    def evaluate_relevance(self, texts: List[str], gap_context: str) -> List[float]:
        if not self.client.available or not texts:
            return [0.5] * len(texts)
        excerpt_block = "\n---\n".join(
            f"Text {i+1}: {t[:300]}" for i, t in enumerate(texts)
        )
        prompt = (
            f"Rate the relevance of each text to this research gap: '{gap_context}'\n"
            f"Rate each from 0.0 (irrelevant) to 1.0 (highly relevant). "
            f"Return only numbers, one per line, nothing else.\n\n{excerpt_block}"
        )
        result = self.client.generate(prompt, max_tokens=60)
        try:
            scores = []
            for line in result.strip().split("\n"):
                line = line.strip()
                if line:
                    scores.append(float(line.split()[-1]))
            if len(scores) == len(texts):
                return [max(0.0, min(1.0, s)) for s in scores]
        except Exception:
            pass
        return [0.5] * len(texts)

    def _fallback_queries(self, period: str, location: str, topic: str) -> List[str]:
        return [
            f"{location} {period} {topic}",
            f"historical records {location} {period}",
        ]
