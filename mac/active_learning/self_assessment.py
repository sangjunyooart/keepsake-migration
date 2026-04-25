"""
Corpus coverage analysis using TF-IDF keyword matching.
No LLM calls — zero token cost.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    period: str
    location: str
    country: str
    current_coverage: float   # 0.0 – 1.0
    priority: float           # higher = more urgent
    suggested_topics: List[str] = field(default_factory=list)
    lens_type: str = ""


class SelfAssessment:
    """
    Identify corpus gaps for a lens relative to Masa's timeline entries.
    Uses TF-IDF keyword overlap as a proxy for coverage.
    """

    def __init__(self, lens_name: str, processed_dir: Path):
        self.lens_name = lens_name
        self.corpus_dir = processed_dir / lens_name
        self._corpus_text: str = ""

    def identify_gaps(self, timeline: list) -> List[Gap]:
        """
        Given masa_timeline entries, return Gap list sorted by priority desc.
        """
        if not timeline:
            return []
        self._corpus_text = self._load_corpus()
        gaps = []
        for entry in timeline:
            coverage = self._estimate_coverage(entry)
            priority = 1.0 - coverage  # low coverage = high priority
            gap = Gap(
                period=entry.get("period", ""),
                location=entry.get("location", ""),
                country=entry.get("country", entry.get("location", "").split(",")[-1].strip()),
                current_coverage=coverage,
                priority=priority,
                suggested_topics=self._suggest_topics(entry),
                lens_type=self.lens_name,
            )
            gaps.append(gap)
        return sorted(gaps, key=lambda g: g.priority, reverse=True)

    # ------------------------------------------------------------------

    def _load_corpus(self) -> str:
        if not self.corpus_dir.exists():
            return ""
        texts = []
        for f in self.corpus_dir.glob("*.txt"):
            texts.append(f.read_text(encoding="utf-8", errors="ignore"))
        return " ".join(texts).lower()

    def _estimate_coverage(self, entry: dict) -> float:
        """
        TF-IDF keyword match: how often do period/location keywords appear
        in the corpus, normalised by corpus length.
        """
        if not self._corpus_text:
            return 0.0
        keywords = self._keywords_for(entry)
        if not keywords:
            return 0.0
        corpus_words = len(self._corpus_text.split())
        if corpus_words == 0:
            return 0.0
        hit_count = sum(self._corpus_text.count(kw.lower()) for kw in keywords)
        normalised = min(1.0, hit_count / max(1, len(keywords)) / 10)
        return normalised

    def _keywords_for(self, entry: dict) -> list[str]:
        keywords = []
        period = entry.get("period", "")
        if "-" in period:
            start, end = period.split("-", 1)
            keywords.extend(y for y in range(int(start[:4]), min(int(start[:4]) + 5, 2030), 2)
                            if start[:4].isdigit())
        location = entry.get("location", "")
        if location:
            keywords.extend(location.split(","))
        context = entry.get("context", "")
        if context:
            keywords.extend(context.split()[:5])
        return [str(k).strip().lower() for k in keywords if str(k).strip()]

    def _suggest_topics(self, entry: dict) -> list[str]:
        location = entry.get("location", "")
        period = entry.get("period", "")
        context = entry.get("context", "")
        return [
            f"{location} {period}",
            f"{context} {location}",
            f"{period} {location} history",
        ]
