import logging
import sys
import time
from pathlib import Path

import yaml


def _setup_logging(lens_name: str, log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"runner_{lens_name}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


class LensRunner:
    def __init__(self, config_path: str, lens_name: str):
        with open(config_path, "r") as f:
            full_config = yaml.safe_load(f)

        self.lens_name = lens_name
        self.lens_config = full_config["lenses"][lens_name]
        self.lens_config["name"] = lens_name
        self.global_config = full_config.get("global", {})

        log_dir = Path(self.global_config.get("log_dir", "logs"))
        adapter_dir = Path(self.global_config.get("adapter_dir", "adapters"))
        corpus_base = Path(self.global_config.get("corpus_base_dir", "corpus"))

        _setup_logging(lens_name, log_dir)
        self.logger = logging.getLogger(f"runner.{lens_name}")

        from data_pipeline.ethics_filter import EthicsFilter
        from data_pipeline.collect import DataCollector
        from data_pipeline.preprocess import Preprocessor
        from training.base_trainer import LensLoRATrainer
        from training.meta_controller import MetaLearningController

        self.ethics_filter = EthicsFilter()
        self.collector = DataCollector(self.lens_config, corpus_base)
        self.preprocessor = Preprocessor(self.ethics_filter)
        self.trainer = LensLoRATrainer(lens_name, self.lens_config, adapter_dir)
        self.meta_controller = MetaLearningController(lens_name, self.lens_config, log_dir)

        self.corpus_processed_dir = Path(self.lens_config.get("corpus_path", f"corpus/processed/{lens_name}"))
        self.corpus_processed_dir.mkdir(parents=True, exist_ok=True)

    def _count_corpus_chunks(self) -> int:
        count = 0
        for jsonl_file in self.corpus_processed_dir.glob("*.jsonl"):
            with open(jsonl_file, "r") as f:
                count += sum(1 for line in f if line.strip())
        return count

    def _estimate_recent_novelty(self) -> float:
        return 0.5

    def cycle_once(self):
        self.logger.info(f"=== Starting cycle for {self.lens_name} ===")

        # Step 1: Collect new data
        try:
            new_items = self.collector.collect_all_sources()
            self.logger.info(f"Collected {len(new_items)} new items")
            if new_items:
                self.collector.save_batch(new_items)
        except Exception as e:
            self.logger.error(f"Collection step failed: {e}", exc_info=True)

        # Step 2: Preprocess unprocessed raw batches
        try:
            raw_dir = Path("corpus") / "raw" / self.lens_name
            if raw_dir.exists():
                for raw_file in sorted(raw_dir.glob("batch_*.jsonl")):
                    stats = self.preprocessor.process_raw_batch(raw_file, self.corpus_processed_dir)
                    self.logger.info(f"Preprocessed {raw_file.name}: {stats}")
        except Exception as e:
            self.logger.error(f"Preprocessing step failed: {e}", exc_info=True)

        # Step 3: Ask meta-controller whether to train
        try:
            corpus_size = self._count_corpus_chunks()
            novelty_score = self._estimate_recent_novelty()
            decision = self.meta_controller.should_train(corpus_size, novelty_score)
            self.logger.info(f"Meta-controller decision: {decision['action']} — {decision.get('reason', '')}")
        except Exception as e:
            self.logger.error(f"Meta-controller step failed: {e}", exc_info=True)
            decision = {"action": "skip", "reason": "meta-controller error"}

        # Step 4: Train if decided
        if decision.get("action") == "train":
            try:
                result = self.trainer.train_session(self.corpus_processed_dir)
                self.meta_controller.mark_training_completed(result)
                self.logger.info(f"Training result: {result['status']}")
            except Exception as e:
                self.logger.error(f"Training step failed: {e}", exc_info=True)

        self.logger.info(f"=== Cycle complete for {self.lens_name} ===")

    def run_forever(self):
        check_interval = self.lens_config.get("learning", {}).get("check_interval_seconds", 3600)
        sleep_seconds = min(check_interval, 600)
        self.logger.info(f"Starting lens runner for '{self.lens_name}', sleep={sleep_seconds}s between cycles")
        try:
            while True:
                try:
                    self.cycle_once()
                except Exception as e:
                    self.logger.error(f"Unhandled exception in cycle: {e}", exc_info=True)
                self.logger.info(f"Sleeping {sleep_seconds}s until next cycle")
                time.sleep(sleep_seconds)
        except KeyboardInterrupt:
            self.logger.info("Lens runner stopped by KeyboardInterrupt")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m orchestration.lens_runner <lens_name>")
        sys.exit(1)
    lens_name = sys.argv[1]
    runner = LensRunner("config/lens_configs.yaml", lens_name)
    runner.run_forever()
