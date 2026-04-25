"""
Orchestrates active learning when Masa's timeline is populated.
Cycles: timeline entries → gap analysis → search → evaluate → add to corpus.
"""
import logging
import yaml
from pathlib import Path

from mac.active_learning.self_assessment import SelfAssessment
from mac.active_learning.search_orchestrator import SearchOrchestrator
from mac.active_learning.result_evaluator import ResultEvaluator
from mac.data_pipeline.collect import FeedCollector

logger = logging.getLogger(__name__)


class HistoricalCollector:
    def __init__(self, lens_name: str, mac_root: Path, max_gaps_per_run: int = 3):
        self.lens_name = lens_name
        self.mac_root = mac_root
        self.max_gaps_per_run = max_gaps_per_run

        self.processed_dir = mac_root / "corpus" / "processed"
        self.raw_dir = mac_root / "corpus" / "raw"
        self.timeline_path = mac_root / "config" / "masa_timeline.yaml"

        self.assessment = SelfAssessment(lens_name, self.processed_dir)
        self.orchestrator = SearchOrchestrator()
        self.evaluator = ResultEvaluator(lens_name)
        self.collector = FeedCollector(lens_name, self.raw_dir)

    def run(self) -> int:
        """
        Run one historical collection cycle.
        Returns number of new texts added to corpus.
        """
        timeline = self._load_timeline()
        if not timeline:
            logger.info("Masa timeline is empty — skipping historical collection for %s", self.lens_name)
            return 0

        gaps = self.assessment.identify_gaps(timeline)
        top_gaps = gaps[: self.max_gaps_per_run]
        added = 0

        for gap in top_gaps:
            results = self.orchestrator.search_gap(gap)
            gap_keywords = gap.suggested_topics + [gap.location, gap.period]
            evaluated = self.evaluator.evaluate(results, gap_keywords)

            for result in evaluated[:5]:  # at most 5 results per gap
                text = result.get("text", "")
                source = f"{result.get('source', 'unknown')}:{result.get('title', '')}"
                if self.collector.add_text(text, source=source):
                    added += 1

        logger.info("Historical collection for %s: +%d new texts", self.lens_name, added)
        return added

    # ------------------------------------------------------------------

    def _load_timeline(self) -> list:
        if not self.timeline_path.exists():
            return []
        data = yaml.safe_load(self.timeline_path.read_text())
        return data.get("masa_timeline", []) or []
