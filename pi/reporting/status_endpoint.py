"""
Flask /status endpoint — port 5000.
Polled by Mac dashboard every 30s to aggregate all Pi states.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify
import psutil

logger = logging.getLogger(__name__)

PI_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PI_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.protocol import PI_STATUS_PORT

_runtime = None   # set by main inference process via set_runtime()
_lens_name = "unknown"


def set_runtime(runtime, lens_name: str):
    global _runtime, _lens_name
    _runtime = runtime
    _lens_name = lens_name


def create_app(lens_name: str) -> Flask:
    global _lens_name
    _lens_name = lens_name
    app = Flask(__name__)

    @app.route("/status")
    def status():
        return jsonify(_build_status())

    @app.route("/health")
    def health():
        return jsonify({"ok": True})

    return app


def _build_status() -> dict:
    sys_info = _get_system_info()
    adapter_info = _runtime.adapter_info() if _runtime else {}
    inference_ready = _runtime.is_ready() if _runtime else False

    return {
        "lens_name": _lens_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inference_ready": inference_ready,
        "system": sys_info,
        "adapter": adapter_info,
    }


def _get_system_info() -> dict:
    info = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "cpu_temp": _get_cpu_temp(),
    }
    return info


def _get_cpu_temp() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        for key in ("cpu_thermal", "coretemp", "cpu-thermal", "soc_thermal"):
            if key in temps and temps[key]:
                return round(temps[key][0].current, 1)
    except (AttributeError, Exception):
        pass
    # Raspberry Pi fallback — read thermal zone directly
    try:
        t = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return round(int(t) / 1000, 1)
    except Exception:
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pi.reporting.status_endpoint <lens_name>")
        sys.exit(1)
    logging.basicConfig(level=logging.INFO)
    app = create_app(sys.argv[1])
    app.run(host="0.0.0.0", port=PI_STATUS_PORT, debug=False)
