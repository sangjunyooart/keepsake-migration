"""
Flask endpoint on port 5001 — receives adapter reload signals from Mac.

Mac sends: POST /reload  with header X-Keepsake-Secret: <shared secret>
Pi reloads the latest adapter from disk (already rsync'd by Mac before signal).
"""
import logging
import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

PI_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PI_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.protocol import RELOAD_HEADER, RELOAD_ENDPOINT, PI_RECEIVER_PORT

_runtime = None   # set by main inference process via set_runtime()


def set_runtime(runtime):
    global _runtime
    _runtime = runtime


def create_app() -> Flask:
    app = Flask(__name__)
    secret = os.environ.get("KEEPSAKE_RELOAD_SECRET", "")

    @app.route(RELOAD_ENDPOINT, methods=["POST"])
    def reload():
        if secret:
            provided = request.headers.get(RELOAD_HEADER, "")
            if provided != secret:
                logger.warning("Reload rejected: bad secret from %s", request.remote_addr)
                return jsonify({"ok": False, "error": "unauthorized"}), 401

        if _runtime is None:
            return jsonify({"ok": False, "error": "runtime not initialised"}), 503

        reloaded = _runtime.reload_adapter()
        if reloaded:
            info = _runtime.adapter_info()
            logger.info("Adapter reloaded: %s", info)
            return jsonify({"ok": True, "reloaded": True, "adapter": info})
        return jsonify({"ok": True, "reloaded": False, "reason": "no new adapter"})

    @app.route("/health")
    def health():
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(host="0.0.0.0", port=PI_RECEIVER_PORT, debug=False)
