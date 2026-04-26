#!/usr/bin/env python3
"""
Detect and configure Time Machine backup disk.

Handles the common failure case where the backup disk is unreachable because
it has a link-local (169.254.x.x) IP — typical for Thunderbolt bridge
connections and direct Ethernet when DHCP is absent.

Usage:
    python3 detect_timemachine_disk.py [--host 169.254.72.157] [--share TimeMachine]
    python3 detect_timemachine_disk.py --scan       # scan via mDNS + link-local ARP
    python3 detect_timemachine_disk.py --configure  # mount + register with tmutil
"""

import argparse
import ipaddress
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


LINK_LOCAL_NETWORK = ipaddress.IPv4Network("169.254.0.0/16")
DEFAULT_MOUNT_BASE = Path("/Volumes")
SMB_PORT = 445
AFP_PORT = 548
CONNECT_TIMEOUT = 3  # seconds


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def is_link_local(addr: str) -> bool:
    try:
        return ipaddress.IPv4Address(addr) in LINK_LOCAL_NETWORK
    except ValueError:
        return False


def port_open(host: str, port: int, timeout: float = CONNECT_TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def probe_host(host: str) -> dict:
    """Return what file-sharing protocols are reachable on host."""
    return {
        "host": host,
        "smb": port_open(host, SMB_PORT),
        "afp": port_open(host, AFP_PORT),
        "reachable": port_open(host, SMB_PORT) or port_open(host, AFP_PORT),
    }


# ---------------------------------------------------------------------------
# mDNS / Bonjour discovery
# ---------------------------------------------------------------------------

def discover_via_dns_sd() -> list[dict]:
    """
    Use dns-sd to browse _smb._tcp and _afpovertcp._tcp.
    Returns list of {host, ip, protocol} dicts.
    Times out after 5 s.
    """
    results = []
    for svc_type in ("_smb._tcp", "_afpovertcp._tcp"):
        try:
            out = subprocess.run(
                ["dns-sd", "-B", svc_type, "local."],
                capture_output=True, text=True, timeout=5,
            ).stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

        for line in out.splitlines():
            # Typical line: "Timestamp  Flags  If  Domain  Type  Name"
            match = re.search(r"local\.\s+(\S+)$", line)
            if match:
                results.append({"name": match.group(1), "protocol": svc_type})
    return results


def resolve_mdns_name(name: str, svc_type: str) -> str | None:
    """Resolve a Bonjour service to an IP address."""
    try:
        out = subprocess.run(
            ["dns-sd", "-L", name, svc_type, "local."],
            capture_output=True, text=True, timeout=5,
        ).stdout
        match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", out)
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ---------------------------------------------------------------------------
# ARP-based link-local scan
# ---------------------------------------------------------------------------

def arp_table_link_local() -> list[str]:
    """Return link-local IPs currently in the ARP cache."""
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return []

    addrs = []
    for line in out.splitlines():
        match = re.search(r"\((\d{1,3}(?:\.\d{1,3}){3})\)", line)
        if match and is_link_local(match.group(1)):
            addrs.append(match.group(1))
    return addrs


def ping_sweep_link_local(subnet_prefix: str = "169.254.72") -> list[str]:
    """
    Ping-sweep a /24 within the link-local range.
    Only useful if we already know the rough subnet from a previously seen IP.
    """
    reachable = []
    for last_octet in range(1, 255):
        addr = f"{subnet_prefix}.{last_octet}"
        ret = subprocess.run(
            ["ping", "-c", "1", "-W", "1", "-q", addr],
            capture_output=True,
        ).returncode
        if ret == 0:
            reachable.append(addr)
    return reachable


# ---------------------------------------------------------------------------
# Mount helpers
# ---------------------------------------------------------------------------

def list_current_tm_destinations() -> list[dict]:
    """Parse `tmutil destinationinfo` output."""
    try:
        out = subprocess.run(
            ["tmutil", "destinationinfo"],
            capture_output=True, text=True,
        ).stdout
    except FileNotFoundError:
        return []

    destinations = []
    current: dict = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("===="):
            if current:
                destinations.append(current)
            current = {}
        elif ":" in line:
            key, _, val = line.partition(":")
            current[key.strip()] = val.strip()
    if current:
        destinations.append(current)
    return destinations


def mount_smb(host: str, share: str, username: str = "guest",
              password: str = "", mount_point: Path | None = None) -> Path | None:
    """
    Mount an SMB share. Returns mount point on success, None on failure.
    For link-local hosts (169.254.x.x) we skip Bonjour and use the raw IP.
    """
    if mount_point is None:
        safe_share = re.sub(r"[^a-zA-Z0-9_-]", "_", share)
        mount_point = DEFAULT_MOUNT_BASE / f"TM-{safe_share}"

    mount_point.mkdir(parents=True, exist_ok=True)

    if password:
        url = f"smb://{username}:{password}@{host}/{share}"
    else:
        url = f"smb://{username}@{host}/{share}"

    result = subprocess.run(
        ["mount", "-t", "smbfs", url, str(mount_point)],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        print(f"  Mounted SMB share at {mount_point}")
        return mount_point

    # Try open-source mount_smbfs path (available on macOS)
    result2 = subprocess.run(
        ["mount_smbfs", url, str(mount_point)],
        capture_output=True, text=True,
    )
    if result2.returncode == 0:
        print(f"  Mounted via mount_smbfs at {mount_point}")
        return mount_point

    print(f"  SMB mount failed: {result.stderr.strip() or result2.stderr.strip()}")
    return None


def configure_tmutil(volume_path: Path) -> bool:
    """Register volume with Time Machine via tmutil."""
    result = subprocess.run(
        ["tmutil", "setdestination", "-p", str(volume_path)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  Time Machine destination set to {volume_path}")
        return True
    print(f"  tmutil setdestination failed: {result.stderr.strip()}")
    print("  Tip: run with sudo if permission denied")
    return False


# ---------------------------------------------------------------------------
# Diagnostic report
# ---------------------------------------------------------------------------

def run_diagnostic(host: str) -> None:
    print(f"\n=== Time Machine Disk Diagnostic for {host} ===\n")

    if is_link_local(host):
        print(f"  NOTE: {host} is a link-local address (169.254.x.x)")
        print("  This is expected for Thunderbolt bridge or direct Ethernet")
        print("  connections when no DHCP server is present.\n")

    info = probe_host(host)
    print(f"  SMB (port 445) : {'open' if info['smb'] else 'closed'}")
    print(f"  AFP (port 548) : {'open' if info['afp'] else 'closed'}")

    if not info["reachable"]:
        print("\n  Host is NOT reachable. Possible causes:")
        print("  1. Cable not connected / Thunderbolt cable not seated")
        print("  2. Firewall on the backup device blocking SMB/AFP")
        print("  3. Wrong IP — run with --scan to rediscover")
        print("  4. For Thunderbolt: System Preferences > Network > Thunderbolt Bridge")
        print("     must be active on BOTH machines")
        sys.exit(1)

    print("\n  Current Time Machine destinations:")
    dests = list_current_tm_destinations()
    if dests:
        for d in dests:
            print(f"    - {d.get('Name', '?')}  ({d.get('URL', d.get('Mount Point', '?'))})")
    else:
        print("    (none configured)")


def run_scan(known_ip: str | None = None) -> None:
    print("\n=== Scanning for Time Machine Shares ===\n")

    print("  Checking ARP cache for link-local hosts...")
    arp_hosts = arp_table_link_local()
    if arp_hosts:
        print(f"  Found link-local hosts in ARP: {arp_hosts}")
    else:
        print("  No link-local hosts in ARP cache")

    print("\n  Probing hosts for SMB/AFP...")
    candidates = list({*arp_hosts, *([] if not known_ip else [known_ip])})
    for h in candidates:
        info = probe_host(h)
        status = []
        if info["smb"]:
            status.append("SMB")
        if info["afp"]:
            status.append("AFP")
        label = ", ".join(status) if status else "no response"
        print(f"    {h:20s}  {label}")

    print("\n  Attempting Bonjour/mDNS discovery...")
    services = discover_via_dns_sd()
    if services:
        for svc in services:
            ip = resolve_mdns_name(svc["name"], svc["protocol"])
            print(f"    {svc['name']:30s}  {svc['protocol']:20s}  ip={ip or '?'}")
    else:
        print("    No services found via mDNS (normal for link-local direct connections)")


def run_configure(host: str, share: str, username: str,
                  password: str, mount_point: str | None) -> None:
    print(f"\n=== Configuring Time Machine: {host}/{share} ===\n")

    if not probe_host(host)["smb"]:
        print(f"  ERROR: {host} SMB port closed. Run --diagnostic first.")
        sys.exit(1)

    mp = Path(mount_point) if mount_point else None
    mounted = mount_smb(host, share, username, password, mp)
    if not mounted:
        sys.exit(1)

    ok = configure_tmutil(mounted)
    if not ok:
        sys.exit(1)

    print(f"\n  Done. Time Machine is now configured to back up to {mounted}")
    print("  To start a backup immediately:  tmutil startbackup")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and configure a Time Machine backup disk, "
                    "including link-local (169.254.x.x) network addresses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="169.254.72.157",
                        help="IP or hostname of the backup disk (default: 169.254.72.157)")
    parser.add_argument("--share", default="TimeMachine",
                        help="SMB share name on the backup device (default: TimeMachine)")
    parser.add_argument("--username", default="guest",
                        help="SMB username (default: guest)")
    parser.add_argument("--password", default="",
                        help="SMB password (default: empty / guest)")
    parser.add_argument("--mount-point",
                        help="Where to mount the share (default: /Volumes/TM-<share>)")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--diagnostic", action="store_true",
                      help="Check reachability and show current TM config")
    mode.add_argument("--scan", action="store_true",
                      help="Scan link-local network and mDNS for backup shares")
    mode.add_argument("--configure", action="store_true",
                      help="Mount the share and register with Time Machine")

    args = parser.parse_args()

    if args.scan:
        run_scan(known_ip=args.host)
    elif args.configure:
        run_configure(args.host, args.share, args.username,
                      args.password, args.mount_point)
    else:
        # Default: diagnostic
        run_diagnostic(args.host)


if __name__ == "__main__":
    main()
