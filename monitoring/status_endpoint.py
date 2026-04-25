import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify
import psutil


def create_app(lens_name: str) -> Flask:
    app = Flask(__name__)

    adapter_dir = Path("adapters") / lens_name
    drift_log = Path("logs") / "drift.jsonl"
    decisions_log = Path("logs") / f"decisions_{lens_name}.jsonl"

    def get_cpu_temp():
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None
            for key in ("cpu_thermal", "coretemp", "cpu-thermal", "soc_thermal"):
                if key in temps and temps[key]:
                    return temps[key][0].current
        except (AttributeError, Exception):
            pass
        return None

    def get_training_stats():
        last_training = None
        total_count = 0
        if decisions_log.exists():
            with open(decisions_log, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("action") == "train":
                        total_count += 1
                        last_training = entry.get("timestamp")
        return {"last_training": last_training, "total_training_count": total_count}

    def get_adapter_stats():
        checkpoints = sorted(adapter_dir.glob("checkpoint_*")) if adapter_dir.exists() else []
        return {
            "latest_checkpoint": str(checkpoints[-1]) if checkpoints else None,
            "total_checkpoints": len(checkpoints),
        }

    def get_latest_drift():
        if not drift_log.exists():
            return None
        last_entry = None
        with open(drift_log, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get("lens") == lens_name:
                        last_entry = entry
        return last_entry

    @app.route("/status")
    def status():
        return jsonify({
            "lens_name": lens_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "cpu_temp": get_cpu_temp(),
            },
            "training": get_training_stats(),
            "adapter": get_adapter_stats(),
            "drift": get_latest_drift(),
        })

    return app


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m monitoring.status_endpoint <lens_name>")
        sys.exit(1)
    lens_name = sys.argv[1]
    app = create_app(lens_name)
    app.run(host="0.0.0.0", port=5000)
