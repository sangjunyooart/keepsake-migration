"""
Main Mac orchestrator. Cycles through 6 lenses continuously.
Each lens: collect → preprocess → (historical) → maybe train → maybe push.
"""
import logging
import signal
import sys
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from mac.training.lora_trainer import LensLoRATrainer
from mac.training.adapter_manager import AdapterManager
from mac.training.meta_controller import MetaController
from mac.data_pipeline.collect import FeedCollector
from mac.data_pipeline.preprocess import Preprocessor
from mac.data_pipeline.historical_collector import HistoricalCollector
from mac.distribution.pi_pusher import PiPusher
from mac.distribution.version_tracker import VersionTracker

logger = logging.getLogger(__name__)

LENS_NAMES = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]


class ContinualLoop:
    def __init__(self, mac_root: Path):
        self.mac_root = mac_root
        self.running = True
        self._load_config()
        self._setup_signal_handlers()

    def run(self):
        logger.info("Continual loop starting. Lenses: %s", LENS_NAMES)
        while self.running:
            for lens_name in LENS_NAMES:
                if not self.running:
                    break
                self._run_lens_cycle(lens_name)
            if self.running:
                logger.info("Full cycle complete. Sleeping 60s before next round.")
                time.sleep(60)

    # ------------------------------------------------------------------

    def _run_lens_cycle(self, lens_name: str):
        logger.info("=== Lens cycle: %s ===", lens_name)
        lc = self.lens_configs["lenses"][lens_name]
        gc = self.lens_configs["global"]

        # 1. Collect new RSS data
        collector = FeedCollector(lens_name, self.mac_root / "corpus" / "raw")
        collector.collect()

        # 2. Run historical collection (active learning)
        historical = HistoricalCollector(lens_name, self.mac_root)
        historical.run()

        # 3. Preprocess
        preprocessor = Preprocessor(
            lens_name,
            self.mac_root / "corpus" / "raw",
            self.mac_root / "corpus" / "processed",
        )
        preprocessor.run()
        chunk_count = preprocessor.count_chunks()

        # 4. Decide whether to train
        controller = MetaController(lens_name, lc, self.mac_root)
        should_train, reason = controller.should_train(chunk_count)
        controller.record_decision(
            action="train" if should_train else "skip",
            reason=reason,
            metadata={"chunk_count": chunk_count},
        )

        if not should_train:
            logger.info("Skipping training for %s: %s", lens_name, reason)
            return

        # 5. Train
        tag = f"checkpoint_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        trainer = LensLoRATrainer(lens_name, gc, lc, self.mac_root)
        try:
            trainer.load_model()
            adapter_path = trainer.train_session(
                self.mac_root / "corpus" / "processed" / lens_name,
                tag,
            )
        finally:
            trainer.unload_model()

        if not adapter_path:
            logger.error("Training produced no adapter for %s", lens_name)
            return

        # 6. Promote adapter
        self.adapter_manager.promote(lens_name, adapter_path)

        # 7. Push to Pi if configured
        if self.system_config["distribution"]["push_after_each_training"]:
            self._push_to_pi(
                lens_name, adapter_path,
                lc.get("pi_target", ""),
                lc.get("pi_ssh_user", "pi"),
            )

    def _push_to_pi(self, lens_name: str, adapter_path: Path,
                    pi_hostname: str, ssh_user: str):
        if not pi_hostname:
            logger.info("No pi_target for %s — skipping push", lens_name)
            return
        logger.info("Pushing %s adapter to %s@%s", lens_name, ssh_user, pi_hostname)
        result = self.pusher.push_adapter(lens_name, adapter_path, pi_hostname, ssh_user)
        self.version_tracker.record_push(lens_name, pi_hostname, adapter_path, result["success"])
        if result["success"]:
            logger.info("Push to %s succeeded", pi_hostname)
        else:
            logger.warning("Push to %s failed: %s", pi_hostname, result.get("error"))

    def _load_config(self):
        lens_cfg_path = self.mac_root / "config" / "lens_configs.yaml"
        sys_cfg_path = self.mac_root / "config" / "system_config.yaml"
        pi_targets_path = self.mac_root / "config" / "pi_targets.yaml"

        self.lens_configs = yaml.safe_load(lens_cfg_path.read_text())
        self.system_config = yaml.safe_load(sys_cfg_path.read_text())["system"]
        self.pi_targets = yaml.safe_load(pi_targets_path.read_text())["pis"]

        self.adapter_manager = AdapterManager(
            self.mac_root / "adapters",
            keep_history=self.system_config["storage"]["adapter_keep_history_count"],
        )
        self.pusher = PiPusher(self.system_config)
        self.version_tracker = VersionTracker(self.mac_root)

    def _setup_signal_handlers(self):
        def _stop(sig, frame):
            logger.info("Received signal %s — stopping after current cycle", sig)
            self.running = False
        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    loop = ContinualLoop(MAC_ROOT)
    loop.run()


if __name__ == "__main__":
    main()
