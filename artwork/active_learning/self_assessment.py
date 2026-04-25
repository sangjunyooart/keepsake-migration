import json
import logging
from pathlib import Path
from typing import List, Optional

from active_learning.source_adapters.base import Gap

logger = logging.getLogger(__name__)

_LENS_TOPIC_KEYWORDS = {
    "human_time": ["daily life", "routine", "generation", "diary", "memoir", "community"],
    "infrastructure_time": ["visa", "border", "immigration", "bureaucracy", "permit", "status"],
    "environmental_time": ["weather", "climate", "ecology", "seasonal", "temperature", "environment"],
    "digital_time": ["internet", "media", "platform", "digital", "network", "technology"],
    "liminal_time": ["migration", "transit", "border", "diaspora", "displacement", "waiting"],
    "more_than_human_time": ["ecology", "species", "geological", "deep time", "nonhuman", "multispecies"],
}


class SelfAssessment:
    """
    Evaluates a lens's corpus against the spatiotemporal claims it should embody.
    Runs entirely without LLM calls — pure TF-IDF keyword analysis.
    """

    def __init__(
        self,
        lens_name: str,
        lens_config: dict,
        corpus_dir: Path,
        timeline: Optional[List[dict]] = None,
    ):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.corpus_dir = Path(corpus_dir)
        self.timeline = timeline or []
        self._corpus_texts: Optional[List[str]] = None

    def _load_corpus(self) -> List[str]:
        if self._corpus_texts is not None:
            return self._corpus_texts
        texts = []
        if self.corpus_dir.exists():
            for f in self.corpus_dir.glob("*.jsonl"):
                with open(f) as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                obj = json.loads(line)
                                texts.append(obj.get("text", ""))
                            except Exception:
                                pass
        self._corpus_texts = texts
        return texts

    def measure_period_coverage(self, period: str, location: str) -> float:
        """
        Returns 0.0–1.0 coverage for a period × location combination.
        Uses TF-IDF keyword match count — no LLM, zero token cost.
        """
        texts = self._load_corpus()
        if not texts:
            return 0.0
        period_parts = period.replace("-", " ").split()
        location_parts = [w.lower() for w in location.replace(",", " ").split()]
        keywords = period_parts + location_parts
        hits = 0
        for text in texts:
            tl = text.lower()
            if any(kw.lower() in tl for kw in keywords):
                hits += 1
        return min(1.0, hits / max(1, len(texts)))

    def identify_gaps(self) -> List[Gap]:
        """
        Returns prioritized list of gaps in the lens's coverage.
        Sorted by priority descending (highest gap first).
        """
        if not self.timeline:
            logger.debug(f"{self.lens_name}: no timeline loaded, returning empty gaps")
            return []

        lens_topics = _LENS_TOPIC_KEYWORDS.get(self.lens_name, ["history", "society"])
        gaps = []

        for entry in self.timeline:
            period = entry.get("period", "")
            location = entry.get("location", "")
            if not period or not location:
                continue
            coverage = self.measure_period_coverage(period, location)
            if coverage < 0.8:
                priority = 1.0 - coverage
                gaps.append(Gap(
                    period=period,
                    location=location,
                    current_coverage=coverage,
                    priority=priority,
                    suggested_topics=lens_topics,
                ))

        gaps.sort(key=lambda g: g.priority, reverse=True)
        logger.debug(f"{self.lens_name}: identified {len(gaps)} corpus gaps")
        return gaps

    def report_state(self) -> dict:
        texts = self._load_corpus()
        gaps = self.identify_gaps()
        return {
            "lens_name": self.lens_name,
            "corpus_size": len(texts),
            "gaps_count": len(gaps),
            "top_gap": {
                "period": gaps[0].period,
                "location": gaps[0].location,
                "coverage": gaps[0].current_coverage,
                "priority": gaps[0].priority,
            } if gaps else None,
        }
