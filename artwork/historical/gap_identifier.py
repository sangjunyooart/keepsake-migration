import logging
from pathlib import Path
from typing import List, Optional

from active_learning.source_adapters.base import Gap
from active_learning.self_assessment import SelfAssessment
from historical.timeline_loader import load_timeline

logger = logging.getLogger(__name__)

_LENS_PERIOD_WEIGHTS = {
    "environmental_time": lambda entry: (
        1.3 if any(kw in entry.get("context", "").lower()
                   for kw in ("extreme", "typhoon", "earthquake", "drought")) else 1.0
    ),
    "infrastructure_time": lambda entry: (
        1.4 if any(kw in entry.get("context", "").lower()
                   for kw in ("visa", "border", "transition", "status")) else 1.0
    ),
    "digital_time": lambda entry: (
        1.3 if entry.get("period", "").startswith(("2000", "2001", "2002", "2003")) else 1.0
    ),
}


class GapIdentifier:
    """
    Cross-references Masa's timeline against a lens's corpus.
    Returns gaps prioritized by coverage shortfall + lens-specific period weights.
    """

    def __init__(
        self,
        lens_name: str,
        lens_config: dict,
        corpus_dir: Path,
        timeline_path: Optional[Path] = None,
    ):
        self.lens_name = lens_name
        timeline = load_timeline(timeline_path)
        self.assessment = SelfAssessment(lens_name, lens_config, corpus_dir, timeline)
        self._weight_fn = _LENS_PERIOD_WEIGHTS.get(lens_name, lambda _: 1.0)

    def identify_prioritized_gaps(self) -> List[Gap]:
        gaps = self.assessment.identify_gaps()
        timeline = self.assessment.timeline
        entry_map = {e.get("period", ""): e for e in timeline}
        for gap in gaps:
            entry = entry_map.get(gap.period, {})
            weight = self._weight_fn(entry)
            gap.priority = min(1.0, gap.priority * weight)
        gaps.sort(key=lambda g: g.priority, reverse=True)
        return gaps
