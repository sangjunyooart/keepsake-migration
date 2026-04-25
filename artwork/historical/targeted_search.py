import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from historical.gap_identifier import GapIdentifier
from active_learning.source_adapters.base import SearchResult

if TYPE_CHECKING:
    from active_learning.query_generator import QueryGenerator
    from active_learning.search_orchestrator import SearchOrchestrator
    from active_learning.result_evaluator import ResultEvaluator

logger = logging.getLogger(__name__)


class TargetedSearch:
    """
    Drives the full active-search pipeline toward the highest-priority gap
    in a lens's coverage of Masa's timeline.
    """

    def __init__(
        self,
        gap_identifier: GapIdentifier,
        query_generator: "QueryGenerator",
        orchestrator: "SearchOrchestrator",
        evaluator: "ResultEvaluator",
        corpus_dir: Path,
        lens_name: str,
    ):
        self.gaps = gap_identifier
        self.qgen = query_generator
        self.orchestrator = orchestrator
        self.evaluator = evaluator
        self.corpus_dir = Path(corpus_dir)
        self.lens_name = lens_name

    def run_cycle(self) -> int:
        """Execute one targeted-search cycle. Returns number of items added."""
        prioritized = self.gaps.identify_prioritized_gaps()
        if not prioritized:
            logger.debug(f"{self.lens_name}: no gaps to fill")
            return 0

        top_gap = prioritized[0]
        logger.info(
            f"{self.lens_name}: targeting gap {top_gap.period}/{top_gap.location} "
            f"(coverage={top_gap.current_coverage:.2f}, priority={top_gap.priority:.2f})"
        )

        queries = self.qgen.generate_queries(top_gap)
        if not queries:
            return 0

        results = self.orchestrator.search(queries, top_gap)
        if not results:
            return 0

        evaluations = self.evaluator.evaluate_batch(results, top_gap)
        kept = [e.result for e in evaluations if e.decision == "keep"]

        if kept:
            self._save_results(kept)
            logger.info(f"{self.lens_name}: active search added {len(kept)} items")

        return len(kept)

    def _save_results(self, results: List[SearchResult]):
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_file = self.corpus_dir / f"active_{ts}.jsonl"
        with open(out_file, "a", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps({
                    "text": r.content,
                    "title": r.title,
                    "url": r.url,
                    "source": r.source,
                    "period": r.gap_period,
                    "location": r.gap_location,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False) + "\n")
