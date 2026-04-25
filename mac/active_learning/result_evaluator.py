"""
Evaluate search results: keyword relevance + ethics filter.
No LLM calls.
"""
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from shared.ethics_filter import EthicsFilter


class ResultEvaluator:
    def __init__(self, lens_name: str):
        self.lens_name = lens_name
        self.ethics = EthicsFilter()

    def evaluate(self, results: list[dict], gap_keywords: list[str]) -> list[dict]:
        """
        Filter results: must pass ethics check and have keyword relevance > 0.
        Returns results sorted by relevance descending.
        """
        scored = []
        for r in results:
            text = r.get("text", "")
            if not self.ethics.is_safe(text):
                logger.debug("Ethics filter dropped result from %s", r.get("source"))
                continue
            score = self._relevance(text, gap_keywords)
            if score > 0:
                scored.append({**r, "_relevance": score})
        return sorted(scored, key=lambda x: x["_relevance"], reverse=True)

    # ------------------------------------------------------------------

    def _relevance(self, text: str, keywords: list[str]) -> float:
        if not keywords or not text:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        return hits / len(keywords)
