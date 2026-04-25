"""
Check that each Pi is reachable and responding.
Run from keepsake-migration/: python -m mac.scripts.verify_pi_inference
"""
import sys
import yaml
from pathlib import Path

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from mac.distribution.pi_health_check import PiHealthChecker


def main():
    pi_targets = yaml.safe_load((MAC_ROOT / "config" / "pi_targets.yaml").read_text())["pis"]
    checker = PiHealthChecker(pi_targets)
    results = checker.check_all()
    print(f"\n{'Host':<20} {'Lens':<25} {'Status'}")
    print("-" * 65)
    for hostname, r in sorted(results.items()):
        status = "✓ online" if r["reachable"] else f"✗ {r.get('error', 'offline')}"
        print(f"{hostname:<20} {r['lens']:<25} {status}")
    print()


if __name__ == "__main__":
    main()
