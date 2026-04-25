import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DriftMeasurer:
    def __init__(self, lens_name: str, adapter_dir: Path, log_path: Path):
        self.lens_name = lens_name
        self.adapter_dir = Path(adapter_dir) / lens_name
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def get_adapter_signature(self, checkpoint_path: Path) -> Dict:
        checkpoint_path = Path(checkpoint_path)
        tensors = {}

        safetensors_path = checkpoint_path / "adapter_model.safetensors"
        bin_path = checkpoint_path / "adapter_model.bin"

        if safetensors_path.exists():
            try:
                from safetensors.torch import load_file
                tensors = load_file(str(safetensors_path))
            except Exception as e:
                logger.error(f"Failed to load safetensors: {e}")
                return {}
        elif bin_path.exists():
            try:
                import torch
                tensors = torch.load(str(bin_path), map_location="cpu")
            except Exception as e:
                logger.error(f"Failed to load bin: {e}")
                return {}
        else:
            logger.warning(f"No adapter weights found in {checkpoint_path}")
            return {}

        sig = {}
        total_norm_sq = 0.0
        for key, tensor in tensors.items():
            if "lora_" not in key:
                continue
            t = tensor.float()
            norm = float(t.norm().item())
            sig[key] = {
                "norm": norm,
                "mean": float(t.mean().item()),
                "std": float(t.std().item()),
                "shape": list(t.shape),
            }
            total_norm_sq += norm ** 2

        sig["_total_norm"] = math.sqrt(total_norm_sq)
        return sig

    def measure_drift_between(self, checkpoint_a: Path, checkpoint_b: Path) -> Dict:
        sig_a = self.get_adapter_signature(checkpoint_a)
        sig_b = self.get_adapter_signature(checkpoint_b)

        total_norm_drift = abs(sig_b.get("_total_norm", 0.0) - sig_a.get("_total_norm", 0.0))

        drift_per_module = {}
        for key in sig_a:
            if key.startswith("_"):
                continue
            if key in sig_b:
                drift_per_module[key] = abs(sig_b[key]["norm"] - sig_a[key]["norm"])

        return {
            "lens": self.lens_name,
            "checkpoint_from": str(checkpoint_a),
            "checkpoint_to": str(checkpoint_b),
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "total_norm_drift": total_norm_drift,
            "drift_per_module": drift_per_module,
        }

    def measure_recent_drift(self, n_recent: int = 2) -> Optional[Dict]:
        checkpoints = sorted(self.adapter_dir.glob("checkpoint_*"))
        if len(checkpoints) < n_recent:
            logger.info(f"Not enough checkpoints for drift measurement (found {len(checkpoints)})")
            return None
        recent = checkpoints[-n_recent:]
        return self.measure_drift_between(recent[0], recent[1])

    def log_drift(self, drift_data: Dict):
        with open(self.log_path, "a") as f:
            f.write(json.dumps(drift_data, ensure_ascii=False) + "\n")
        logger.info(f"Logged drift: total_norm_drift={drift_data.get('total_norm_drift', 0):.4f}")
