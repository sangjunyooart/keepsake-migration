"""
Pushes LoRA adapter to a Pi via rsync over SSH, then signals reload.
"""
import logging
import os
import subprocess
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class PiPusher:
    def __init__(self, system_config: dict):
        dist = system_config["distribution"]
        self.ssh_key = os.path.expanduser(dist["pi_ssh_key_path"])

    def push_adapter(self, lens_name: str, adapter_path: Path, pi_hostname: str,
                     ssh_user: str = "pi") -> dict:
        """
        rsync adapter to Pi, then POST /reload signal.
        Returns {"success": bool, "error": str | None}.
        """
        result = self._rsync(lens_name, adapter_path, pi_hostname, ssh_user)
        if not result["success"]:
            return result
        return self._signal_reload(pi_hostname)

    # ------------------------------------------------------------------

    def _rsync(self, lens_name: str, adapter_path: Path, pi_hostname: str,
               ssh_user: str) -> dict:
        remote_path = f"/home/{ssh_user}/keepsake-migration/pi/adapters/{lens_name}/"
        cmd = [
            "rsync", "-avz", "--delete",
            "-e", f"ssh -i {self.ssh_key} -o StrictHostKeyChecking=no -o ConnectTimeout=10",
            f"{adapter_path}/",
            f"{ssh_user}@{pi_hostname}:{remote_path}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error("rsync failed to %s: %s", pi_hostname, result.stderr)
                return {"success": False, "error": result.stderr.strip()}
            logger.info("rsync to %s completed", pi_hostname)
            return {"success": True, "error": None}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "rsync timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _signal_reload(self, pi_hostname: str) -> dict:
        secret = os.environ.get("KEEPSAKE_RELOAD_SECRET", "")
        try:
            resp = requests.post(
                f"http://{pi_hostname}:5001/reload",
                headers={"X-Keepsake-Secret": secret},
                timeout=10,
            )
            ok = resp.status_code == 200
            return {"success": ok, "error": None if ok else f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.warning("Reload signal failed for %s: %s", pi_hostname, e)
            return {"success": False, "error": str(e)}
