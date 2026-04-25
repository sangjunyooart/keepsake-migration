"""
Manually push all current adapters to their respective Pis.
Run from keepsake-migration/: python -m mac.scripts.push_to_all_pis
"""
import sys
import yaml
from pathlib import Path

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from mac.distribution.pi_pusher import PiPusher
from mac.distribution.version_tracker import VersionTracker
from mac.training.adapter_manager import AdapterManager


def main():
    sys_cfg = yaml.safe_load((MAC_ROOT / "config" / "system_config.yaml").read_text())["system"]
    pi_targets = yaml.safe_load((MAC_ROOT / "config" / "pi_targets.yaml").read_text())["pis"]

    pusher = PiPusher(sys_cfg)
    tracker = VersionTracker(MAC_ROOT)
    adapter_mgr = AdapterManager(MAC_ROOT / "adapters")

    for target in pi_targets:
        lens = target["lens"]
        hostname = target["hostname"]
        adapter_path = adapter_mgr.current_path(lens)
        if not adapter_path:
            print(f"  {lens}: no adapter yet — skipping")
            continue
        print(f"  Pushing {lens} → {hostname} ...", end=" ", flush=True)
        result = pusher.push_adapter(lens, adapter_path, hostname)
        tracker.record_push(lens, hostname, adapter_path, result["success"])
        print("OK" if result["success"] else f"FAILED: {result.get('error')}")


if __name__ == "__main__":
    main()
