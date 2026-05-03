"""
AgentCoordinator — drop-in replacement for HistoricalCollector.

Runs LensAgent for a given lens, then pipes the generated queries
into the existing SearchOrchestrator + FeedCollector pipeline.

Usage in continual_loop.py:
    coordinator = AgentCoordinator(mac_root, system_config, lens_configs)
    texts_added = coordinator.run_lens(lens_name)
"""
import logging
import sys
from pathlib import Path

import yaml

from .lens_agent import LensAgent
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_MAC_ROOT.parent))


class AgentCoordinator:
    def __init__(self, mac_root: Path, system_config: dict, lens_configs: dict):
        self.mac_root = mac_root
        self.system_config = system_config
        self.lens_configs = lens_configs

        agent_cfg = system_config.get("agent_curation", {})
        model = agent_cfg.get("model", "qwen2.5:14b-instruct-q4_K_M")
        base_url = agent_cfg.get("ollama_base_url", "http://localhost:11434")

        self.client = OllamaClient(base_url=base_url, model=model)
        self._max_results_per_query = agent_cfg.get("max_results_per_query", 3)

    def is_available(self) -> bool:
        return self.client.is_available()

    def run_lens(self, lens_name: str) -> int:
        """
        Run agent curation for one lens.
        Returns number of new texts added to corpus.
        """
        if not self.client.is_available():
            logger.warning(
                "[coordinator] Ollama not reachable at %s — skipping agent for %s",
                self.client.base_url, lens_name,
            )
            return 0

        lc = self.lens_configs["lenses"].get(lens_name, {})
        agent = LensAgent(
            lens_name=lens_name,
            lens_config=lc,
            mac_root=self.mac_root,
            client=self.client,
        )

        result = agent.run()

        if result.status != "complete" or not result.queries:
            logger.info(
                "[coordinator:%s] agent status=%s, no queries to execute",
                lens_name, result.status,
            )
            return 0

        return self._execute_queries(lens_name, result.queries)

    # ── query execution ───────────────────────────────────────────────────────

    def _execute_queries(self, lens_name: str, queries: list[str]) -> int:
        """Run agent-generated queries through Wikipedia search → corpus."""
        from mac.active_learning.source_adapters.wikipedia_adapter import WikipediaAdapter
        from mac.data_pipeline.collect import FeedCollector

        adapter = WikipediaAdapter()
        collector = FeedCollector(lens_name, self.mac_root / "corpus" / "raw")

        added = 0
        for query in queries:
            try:
                results = adapter.search(query, max_results=self._max_results_per_query)
                for result in results:
                    text = adapter.fetch_content(result)
                    if not text:
                        continue
                    source = f"wikipedia:{result.title}"
                    if collector.add_text(text, source=source):
                        added += 1
            except Exception as exc:
                logger.warning(
                    "[coordinator:%s] query failed '%s': %s", lens_name, query, exc
                )
                continue

        logger.info(
            "[coordinator:%s] %d queries → +%d new texts",
            lens_name, len(queries), added,
        )
        return added

    # ── state helpers (for dashboard) ─────────────────────────────────────────

    def load_all_states(self) -> dict:
        """Read agent_{lens}.json for all lenses. Used by dashboard."""
        import json
        states = {}
        for lens_name in self.lens_configs.get("lenses", {}):
            state_path = self.mac_root / "runtime_state" / f"agent_{lens_name}.json"
            if state_path.exists():
                try:
                    states[lens_name] = json.loads(state_path.read_text())
                except Exception:
                    states[lens_name] = {"status": "error", "lens_name": lens_name}
            else:
                states[lens_name] = {"status": "idle", "lens_name": lens_name}
        return states
