"""
Pi main entry point — wires inference + reception + output together.
Run: python -m pi.main <lens_name>
"""
import logging
import sys
import threading
import yaml
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

PI_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PI_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from pi.inference.lens_runtime import LensRuntime
from pi.reception.adapter_receiver import create_app as create_receiver_app, set_runtime as set_receiver_runtime
from pi.reporting.status_endpoint import create_app as create_status_app, set_runtime as set_status_runtime
from pi.output.dispatcher import OutputDispatcher
from shared.protocol import PI_STATUS_PORT, PI_RECEIVER_PORT

logger = logging.getLogger(__name__)


def main(lens_name: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = _load_config(lens_name)
    adapter_base = Path(config["pi"]["adapter_path"])
    inf_cfg = config["inference"]
    log_dir = Path(config["reporting"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    runtime = LensRuntime(lens_name, adapter_base, inf_cfg)
    dispatcher = OutputDispatcher(lens_name, inf_cfg, log_dir)

    # Wire runtime into Flask apps
    set_receiver_runtime(runtime)
    set_status_runtime(runtime, lens_name)

    # Start status endpoint in background thread
    status_app = create_status_app(lens_name)
    threading.Thread(
        target=lambda: status_app.run(host="0.0.0.0", port=PI_STATUS_PORT, debug=False),
        daemon=True,
    ).start()
    logger.info("Status endpoint listening on :%d", PI_STATUS_PORT)

    # Start adapter receiver in background thread
    receiver_app = create_receiver_app()
    threading.Thread(
        target=lambda: receiver_app.run(host="0.0.0.0", port=PI_RECEIVER_PORT, debug=False),
        daemon=True,
    ).start()
    logger.info("Adapter receiver listening on :%d", PI_RECEIVER_PORT)

    # Load model (blocking — takes ~2 min on Pi 5)
    runtime.load()

    logger.info("Pi ready: %s", lens_name)

    # Main loop: run inference on a simple heartbeat prompt
    # In exhibition phase, this is replaced by memory_processor input
    import time
    while True:
        try:
            text = runtime.generate(
                f"Describe the {lens_name.replace('_', ' ')} of a place.",
                max_tokens=inf_cfg.get("max_tokens", 200),
                temperature=inf_cfg.get("temperature", 0.8),
            )
            if text:
                dispatcher.dispatch(text)
        except Exception as e:
            logger.error("Inference error: %s", e)

        # Sleep until next cycle — interval from config or default 60s
        time.sleep(60)


def _load_config(lens_name: str) -> dict:
    cfg_path = PI_ROOT / "config" / "pi_config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"pi_config.yaml not found at {cfg_path}")
    config = yaml.safe_load(cfg_path.read_text())
    # Override lens_name from command line
    config["pi"]["lens_name"] = lens_name
    return config


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pi.main <lens_name>")
        sys.exit(1)
    main(sys.argv[1])
