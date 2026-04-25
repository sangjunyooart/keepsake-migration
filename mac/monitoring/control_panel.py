"""
Control panel: toggle training per lens, manual push trigger, emergency stop.
Writes to mac/runtime_state/{lens}.json — the only place monitoring writes into artwork state.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ALL_LENSES = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]


class ControlPanel:
    def __init__(self, mac_root: Path):
        self.runtime_state_dir = mac_root / "runtime_state"
        self.runtime_state_dir.mkdir(parents=True, exist_ok=True)

    def get_state(self, lens_name: str) -> dict:
        state_file = self.runtime_state_dir / f"{lens_name}.json"
        if not state_file.exists():
            return self._default_state(lens_name)
        return json.loads(state_file.read_text())

    def set_training_enabled(self, lens_name: str, enabled: bool) -> dict:
        state = self.get_state(lens_name)
        state["training_enabled"] = enabled
        self._save(lens_name, state)
        logger.info("Set training_enabled=%s for %s", enabled, lens_name)
        return state

    def emergency_stop_all(self) -> dict:
        """Disable training for all lenses immediately."""
        for lens in ALL_LENSES:
            self.set_training_enabled(lens, False)
        logger.warning("EMERGENCY STOP: training disabled for all lenses")
        return {"stopped": ALL_LENSES}

    def resume_all(self) -> dict:
        for lens in ALL_LENSES:
            self.set_training_enabled(lens, True)
        logger.info("Resumed training for all lenses")
        return {"resumed": ALL_LENSES}

    def all_states(self) -> dict:
        return {lens: self.get_state(lens) for lens in ALL_LENSES}

    # ------------------------------------------------------------------

    def _default_state(self, lens_name: str) -> dict:
        return {"lens": lens_name, "training_enabled": True}

    def _save(self, lens_name: str, state: dict):
        (self.runtime_state_dir / f"{lens_name}.json").write_text(
            json.dumps(state, indent=2)
        )
