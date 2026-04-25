import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def measure_novelty(new_chunks: List[str], recent_corpus: List[str], max_compare: int = 100) -> float:
    if not recent_corpus:
        return 1.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        compare_corpus = recent_corpus[-max_compare:]
        all_texts = new_chunks + compare_corpus
        vectorizer = TfidfVectorizer(max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        new_vecs = tfidf_matrix[: len(new_chunks)]
        corpus_vecs = tfidf_matrix[len(new_chunks):]

        similarities = cosine_similarity(new_vecs, corpus_vecs)
        max_sims = similarities.max(axis=1)
        novelty = 1.0 - float(np.mean(max_sims))
        return float(np.clip(novelty, 0.0, 1.0))
    except Exception as e:
        logger.warning(f"novelty measurement failed, returning 0.5: {e}")
        return 0.5


class MetaLearningController:
    def __init__(self, lens_name: str, lens_config: dict, log_dir: Path):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._decisions_log = self.log_dir / f"decisions_{lens_name}.jsonl"
        self._last_training_time: Optional[datetime] = self._load_last_training_time()
        self._runtime_state_file = Path("runtime_state") / f"{lens_name}.json"

    def _load_last_training_time(self) -> Optional[datetime]:
        if not self._decisions_log.exists():
            return None
        last_entry = None
        with open(self._decisions_log, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_entry = json.loads(line)
        if last_entry and last_entry.get("action") == "train":
            ts = last_entry.get("timestamp")
            if ts:
                return datetime.fromisoformat(ts)
        return None

    def _is_training_enabled(self) -> bool:
        """Reads runtime_state to check control-panel toggle. Defaults to True."""
        try:
            if self._runtime_state_file.exists():
                with open(self._runtime_state_file) as f:
                    state = json.load(f)
                return bool(state.get("training_enabled", True))
        except Exception as e:
            logger.warning(f"Could not read runtime state for {self.lens_name}: {e}")
        return True

    def should_train(self, corpus_size: int, novelty_score: float) -> Dict:
        now = datetime.now(timezone.utc)
        decision = {
            "lens_name": self.lens_name,
            "timestamp": now.isoformat(),
            "corpus_size": corpus_size,
            "novelty_score": novelty_score,
        }

        # Control-panel override takes priority
        if not self._is_training_enabled():
            decision.update({
                "action": "skip",
                "reason": "training disabled via control panel",
            })
            self._log_decision(decision)
            return decision

        learning_cfg = self.lens_config.get("learning", {})
        check_interval = learning_cfg.get("check_interval_seconds", 3600)
        min_chunks = learning_cfg.get("min_corpus_chunks", 50)
        novelty_threshold = learning_cfg.get("novelty_threshold", 0.4)

        if self._last_training_time is not None:
            elapsed = (now - self._last_training_time).total_seconds()
            if elapsed < check_interval:
                decision.update({
                    "action": "skip",
                    "reason": f"too soon since last training ({elapsed:.0f}s < {check_interval}s)",
                })
                self._log_decision(decision)
                return decision

        if corpus_size < min_chunks:
            decision.update({
                "action": "skip",
                "reason": f"insufficient corpus ({corpus_size} < {min_chunks} chunks)",
            })
            self._log_decision(decision)
            return decision

        if novelty_score < novelty_threshold:
            decision.update({
                "action": "skip",
                "reason": f"low novelty ({novelty_score:.3f} < {novelty_threshold})",
            })
            self._log_decision(decision)
            return decision

        intensity = self._compute_intensity(novelty_score)
        decision.update({
            "action": "train",
            "reason": f"novelty {novelty_score:.3f} >= threshold {novelty_threshold}",
            "intensity": intensity,
        })
        self._log_decision(decision)
        return decision

    def _compute_intensity(self, novelty_score: float) -> Dict:
        learning_cfg = self.lens_config.get("learning", {})
        max_epochs = learning_cfg.get("max_epochs_per_session", 1)
        if novelty_score > 0.8:
            return {"epochs": max_epochs, "lr_multiplier": 1.0}
        elif novelty_score > 0.5:
            return {"epochs": max_epochs, "lr_multiplier": 0.7}
        else:
            return {"epochs": 1, "lr_multiplier": 0.5}

    def mark_training_completed(self, result: Dict):
        now = datetime.now(timezone.utc)
        self._last_training_time = now
        entry = {
            "lens_name": self.lens_name,
            "timestamp": now.isoformat(),
            "action": "train",
            "result": result,
        }
        self._log_decision(entry)

    def _log_decision(self, entry: Dict):
        with open(self._decisions_log, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
