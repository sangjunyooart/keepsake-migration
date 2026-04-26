#!/usr/bin/env python3
"""
Thunderbolt Bridge 전용 Time Machine 디스크 탐지 및 설정 도구.

"Backup Disk Not Available 169.254.x.x" 오류 수정.

사용법:
    python3 detect_timemachine_disk.py                    # 현재 상태 진단
    python3 detect_timemachine_disk.py --scan             # 링크-로컬 공유 탐색
    python3 detect_timemachine_disk.py --configure        # 마운트 + tmutil 등록
    python3 detect_timemachine_disk.py --host 169.254.72.157 --configure
"""

import argparse
import ipaddress
import re
import socket
import subprocess
import sys
from pathlib import Path


LINK_LOCAL_NET = ipaddress.IPv4Network("169.254.0.0/16")
SMB_PORT = 445
TIMEOUT = 3


# ── 유틸 ────────────────────────────────────────────────────────────────────

def is_link_local(addr: str) -> bool:
    try:
        return ipaddress.IPv4Address(addr) in LINK_LOCAL_NET
    except ValueError:
        return False


def port_open(host: str, port: int, timeout: float = TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ── Thunderbolt Bridge 인터페이스 ───────────────────────────────────────────

def find_tb_interface() -> str | None:
    """Thunderbolt Bridge 인터페이스 이름 반환 (예: bridge0, en5)."""
    hw = run(["networksetup", "-listallhardwareports"]).stdout
    lines = hw.splitlines()
    for i, line in enumerate(lines):
        if "Thunderbolt Bridge" in line and i + 1 < len(lines):
            m = re.search(r"Device:\s*(\S+)", lines[i + 1])
            if m:
                return m.group(1)

    # 폴백: 169.254 주소를 가진 인터페이스 탐색
    ifc = run(["ifconfig"]).stdout
    current = None
    for line in ifc.splitlines():
        m = re.match(r"^(\S+):", line)
        if m:
            current = m.group(1)
        if current and re.search(r"inet 169\.254\.", line):
            return current
    return None


def get_link_local_ip(iface: str) -> str | None:
    out = run(["ipconfig", "getifaddr", iface]).stdout.strip()
    return out if is_link_local(out) else None


def ensure_interface_up(iface: str) -> bool:
    result = run(["ifconfig", iface, "up"])
    return result.returncode == 0


def tb_interface_summary() -> dict:
    iface = find_tb_interface()
    if not iface:
        return {"found": False}
    ip = get_link_local_ip(iface)
    status_out = run(["ifconfig", iface]).stdout
    active = "status: active" in status_out
    return {"found": True, "iface": iface, "local_ip": ip, "active": active}


# ── 링크-로컬 호스트 탐색 ───────────────────────────────────────────────────

def arp_link_local_hosts() -> list[str]:
    out = run(["arp", "-a"]).stdout
    addrs = re.findall(r"\((\d{1,3}(?:\.\d{1,3}){3})\)", out)
    return [a for a in addrs if is_link_local(a)]


def list_smb_shares(host: str, user: str = "guest") -> list[str]:
    out = run(["smbutil", "view", f"//{user}@{host}"], timeout=8).stdout
    shares = []
    for line in out.splitlines():
        parts = line.split()
        if parts and not line.startswith("Share") and not line.startswith("---"):
            shares.append(parts[0])
    return shares


# ── Time Machine 상태 ───────────────────────────────────────────────────────

def tm_destinations() -> list[dict]:
    out = run(["tmutil", "destinationinfo"]).stdout
    dests, cur = [], {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("===="):
            if cur:
                dests.append(cur)
            cur = {}
        elif ":" in line:
            k, _, v = line.partition(":")
            cur[k.strip()] = v.strip()
    if cur:
        dests.append(cur)
    return dests


# ── 마운트 ──────────────────────────────────────────────────────────────────

def mount_smb(host: str, share: str, user: str = "guest",
              password: str = "", mount_point: Path | None = None) -> Path | None:
    if mount_point is None:
        mount_point = Path("/Volumes") / f"TimeMachine-TB"

    mount_point.mkdir(parents=True, exist_ok=True)

    url = f"smb://{user}:{password}@{host}/{share}" if password \
        else f"smb://{user}@{host}/{share}"

    for cmd in (["mount_smbfs", url, str(mount_point)],
                ["/sbin/mount", "-t", "smbfs", url, str(mount_point)]):
        if run(cmd).returncode == 0:
            return mount_point

    return None


def tmutil_set_destination(path: Path) -> bool:
    for flags in (["-p"], []):
        result = run(["tmutil", "setdestination"] + flags + [str(path)])
        if result.returncode == 0:
            return True
    return False


# ── 모드별 실행 ─────────────────────────────────────────────────────────────

def cmd_diagnostic(host: str) -> None:
    print(f"\n{'═'*55}")
    print(f"  Time Machine 진단 — {host}")
    print(f"{'═'*55}\n")

    # Thunderbolt Bridge
    tb = tb_interface_summary()
    if tb["found"]:
        iface = tb["iface"]
        print(f"  Thunderbolt Bridge 인터페이스 : {iface}")
        print(f"  인터페이스 상태               : {'active' if tb['active'] else 'inactive ← 문제'}")
        print(f"  이 Mac의 링크-로컬 IP          : {tb['local_ip'] or '미할당 ← 문제'}")
    else:
        print("  Thunderbolt Bridge 인터페이스 : 찾을 수 없음")
        print("  → 시스템 설정 > 네트워크 > Thunderbolt Bridge 확인")

    print()

    if is_link_local(host):
        print(f"  대상 IP {host} : 링크-로컬 (Thunderbolt Bridge 정상 동작)")
    else:
        print(f"  대상 IP {host} : 일반 IP")

    smb_ok = port_open(host, SMB_PORT)
    print(f"  SMB 포트 445   : {'열림' if smb_ok else '닫힘'}")

    if not smb_ok:
        print("\n  ─── 호스트 연결 불가 ───────────────────────────────")
        print("  ① Thunderbolt 케이블이 양쪽에 꽂혀 있는지 확인")
        print("  ② 백업 Mac: 시스템 설정 > 일반 > 공유 > 파일 공유 ON")
        print("  ③ 백업 Mac: 시스템 설정 > 네트워크 > Thunderbolt Bridge ON")
        print("  ④ 이 Mac:   시스템 설정 > 네트워크 > Thunderbolt Bridge ON")
        print(f"  ⑤ ARP 캐시 확인: arp -a | grep 169.254")
        sys.exit(1)

    print("\n  현재 Time Machine 대상:")
    dests = tm_destinations()
    if dests:
        for d in dests:
            name = d.get("Name", "?")
            url = d.get("URL") or d.get("Mount Point", "?")
            kind = d.get("Kind", "")
            print(f"    • {name}  [{kind}]  {url}")
    else:
        print("    (설정 없음)")

    print()


def cmd_scan(host: str) -> None:
    print(f"\n{'═'*55}")
    print("  링크-로컬 Time Machine 공유 탐색")
    print(f"{'═'*55}\n")

    tb = tb_interface_summary()
    if tb["found"]:
        print(f"  Thunderbolt Bridge: {tb['iface']}  (이 Mac: {tb['local_ip'] or '주소 없음'})")
    else:
        print("  Thunderbolt Bridge 인터페이스 없음")
    print()

    known = {host} if is_link_local(host) else set()
    from_arp = set(arp_link_local_hosts())
    candidates = sorted(known | from_arp)

    if not candidates:
        print("  링크-로컬 호스트를 찾지 못했습니다.")
        print("  Thunderbolt 케이블 연결 확인 후 재시도하세요.")
        return

    for h in candidates:
        smb = port_open(h, SMB_PORT)
        marker = "← 백업 Mac 가능성 높음" if smb else ""
        print(f"  {h:20s}  SMB={'열림' if smb else '닫힘'}  {marker}")
        if smb:
            shares = list_smb_shares(h)
            if shares:
                for s in shares:
                    print(f"    └─ 공유: {s}")
            else:
                print("    └─ 공유 목록 조회 실패 (인증 필요 가능)")

    print()
    print("  설정하려면:")
    for h in candidates:
        if port_open(h, SMB_PORT):
            print(f"    python3 detect_timemachine_disk.py --host {h} --configure")


def cmd_configure(host: str, share: str, user: str,
                  password: str, mount_point: str | None) -> None:
    print(f"\n{'═'*55}")
    print(f"  Time Machine 설정: {host}/{share}")
    print(f"{'═'*55}\n")

    # Thunderbolt Bridge 활성화
    tb = tb_interface_summary()
    if tb["found"] and not tb["active"]:
        print(f"  Thunderbolt Bridge({tb['iface']}) 활성화 중...")
        ensure_interface_up(tb["iface"])

    if not port_open(host, SMB_PORT):
        print(f"  오류: {host} SMB 포트가 닫혀 있습니다.")
        print("  먼저 --scan 또는 --diagnostic 으로 연결 상태를 확인하세요.")
        sys.exit(1)

    # 공유 이름 자동탐색
    if share == "auto":
        shares = list_smb_shares(host, user)
        if not shares:
            shares = list_smb_shares(host, "guest")
            if shares:
                user = "guest"
        for preferred in ("TimeMachine", "Backup", "Data"):
            if any(s.lower() == preferred.lower() for s in shares):
                share = next(s for s in shares if s.lower() == preferred.lower())
                break
        if share == "auto":
            share = shares[0] if shares else "TimeMachine"
        print(f"  공유 자동선택: {share}")

    mp = Path(mount_point) if mount_point else None
    mounted = mount_smb(host, share, user, password, mp)
    if not mounted:
        print("  SMB 마운트 실패.")
        print(f"  수동: Finder > 서버에 연결 > smb://{host}/{share}")
        sys.exit(1)
    print(f"  마운트 완료: {mounted}")

    if tmutil_set_destination(mounted):
        print(f"  Time Machine 대상 등록 완료: {mounted}")
    else:
        print("  tmutil setdestination 실패 — sudo 로 재실행하거나 수동 등록:")
        print("  시스템 설정 > 일반 > Time Machine > 백업 디스크 추가")
        sys.exit(1)

    print("\n  완료. 즉시 백업 시작:")
    print("    tmutil startbackup")
    print()


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Thunderbolt Bridge Time Machine 디스크 탐지/설정 (169.254.x.x 대응)",
    )
    p.add_argument("--host", default="169.254.72.157",
                   help="백업 Mac IP (기본: 169.254.72.157)")
    p.add_argument("--share", default="auto",
                   help="SMB 공유 이름 (기본: auto = 자동탐색)")
    p.add_argument("--username", default="",
                   help="SMB 사용자 (기본: 현재 사용자)")
    p.add_argument("--password", default="",
                   help="SMB 비밀번호 (기본: 빈값)")
    p.add_argument("--mount-point",
                   help="마운트 경로 (기본: /Volumes/TimeMachine-TB)")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--scan", action="store_true",
                      help="링크-로컬 네트워크에서 백업 공유 탐색")
    mode.add_argument("--configure", action="store_true",
                      help="마운트 후 Time Machine 등록")

    args = p.parse_args()

    user = args.username or subprocess.run(
        ["stat", "-f", "%Su", "/dev/console"],
        capture_output=True, text=True,
    ).stdout.strip() or "guest"

    if args.scan:
        cmd_scan(args.host)
    elif args.configure:
        cmd_configure(args.host, args.share, user, args.password, args.mount_point)
    else:
        cmd_diagnostic(args.host)


if __name__ == "__main__":
    main()
