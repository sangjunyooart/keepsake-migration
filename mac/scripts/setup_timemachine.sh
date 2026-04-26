#!/usr/bin/env bash
# setup_timemachine.sh
#
# One-shot setup for a Time Machine backup disk reachable via Thunderbolt bridge
# or direct Ethernet at a link-local (169.254.x.x) address.
#
# The "Backup Disk Not Available" error with a 169.254.x.x IP means macOS
# Time Machine lost track of the share — usually because:
#   (a) the Thunderbolt Bridge interface needs to be active on both machines, OR
#   (b) the share was previously registered by hostname, not IP, and DNS failed
#
# Run as: sudo bash setup_timemachine.sh
# Env vars you can override:
#   TM_HOST        backup disk IP          (default: 169.254.72.157)
#   TM_SHARE       SMB share name          (default: TimeMachine)
#   TM_USER        SMB username            (default: guest)
#   TM_PASS        SMB password            (default: empty)
#   TM_MOUNT       mount point             (default: /Volumes/TimeMachine)

set -euo pipefail

TM_HOST="${TM_HOST:-169.254.72.157}"
TM_SHARE="${TM_SHARE:-TimeMachine}"
TM_USER="${TM_USER:-guest}"
TM_PASS="${TM_PASS:-}"
TM_MOUNT="${TM_MOUNT:-/Volumes/TimeMachine}"

log()  { printf '\e[34m[TM]\e[0m %s\n' "$*"; }
ok()   { printf '\e[32m[OK]\e[0m %s\n' "$*"; }
fail() { printf '\e[31m[ERR]\e[0m %s\n' "$*" >&2; exit 1; }
warn() { printf '\e[33m[WARN]\e[0m %s\n' "$*"; }

# ── 1. Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    fail "This script is macOS-only."
fi

# ── 2. Require sudo (tmutil setdestination needs it)
if [[ "$EUID" -ne 0 ]]; then
    warn "Not running as root — will try anyway, but tmutil may fail."
    warn "Re-run with: sudo bash $0"
fi

log "Backup host : $TM_HOST"
log "Share       : $TM_SHARE"
log "Mount point : $TM_MOUNT"

# ── 3. Verify link-local address is expected
if [[ "$TM_HOST" =~ ^169\.254\. ]]; then
    log "Link-local address detected (169.254.x.x)"
    log "Expected for Thunderbolt Bridge or direct Ethernet — continuing"
fi

# ── 4. Check Thunderbolt Bridge interface
log "Checking network interfaces for Thunderbolt Bridge..."
if ifconfig | grep -qE "bridge|thunderbolt" 2>/dev/null; then
    ok "Thunderbolt Bridge interface found"
else
    warn "No Thunderbolt Bridge interface visible in ifconfig"
    warn "On the backup Mac: System Settings > Network > Thunderbolt Bridge"
    warn "  must be enabled. This script will continue but mount may fail."
fi

# ── 5. Ping the host
log "Pinging $TM_HOST ..."
if ping -c 3 -W 2 -q "$TM_HOST" > /dev/null 2>&1; then
    ok "Host is reachable"
else
    fail "$TM_HOST is not reachable.
  Checklist:
  • Thunderbolt cable seated on both ends
  • System Settings > Network > Thunderbolt Bridge: active on BOTH Macs
  • Try: sudo ifconfig bridge0 up   (on this Mac)
  • Try: arp -a | grep 169.254       (to see what link-local hosts are known)"
fi

# ── 6. Check SMB port
log "Checking SMB port 445 on $TM_HOST ..."
if nc -z -w 3 "$TM_HOST" 445 2>/dev/null; then
    ok "SMB port open"
else
    warn "SMB port 445 closed — will attempt mount anyway (AFP or alternate port possible)"
fi

# ── 7. Unmount stale mount if present
if mount | grep -q "$TM_MOUNT" 2>/dev/null; then
    log "Unmounting stale mount at $TM_MOUNT ..."
    diskutil unmount force "$TM_MOUNT" 2>/dev/null \
        || umount -f "$TM_MOUNT" 2>/dev/null \
        || warn "Could not unmount existing $TM_MOUNT — proceeding"
fi

mkdir -p "$TM_MOUNT"

# ── 8. Mount SMB share
log "Mounting smb://$TM_USER@$TM_HOST/$TM_SHARE → $TM_MOUNT ..."
if [[ -n "$TM_PASS" ]]; then
    MOUNT_URL="smb://${TM_USER}:${TM_PASS}@${TM_HOST}/${TM_SHARE}"
else
    MOUNT_URL="smb://${TM_USER}@${TM_HOST}/${TM_SHARE}"
fi

if mount -t smbfs "$MOUNT_URL" "$TM_MOUNT" 2>/dev/null; then
    ok "Mounted via mount -t smbfs"
elif mount_smbfs "$MOUNT_URL" "$TM_MOUNT" 2>/dev/null; then
    ok "Mounted via mount_smbfs"
else
    # Last resort: open with Finder protocol
    open "smb://${TM_HOST}/${TM_SHARE}" 2>/dev/null || true
    fail "Could not mount SMB share.
  Manual steps:
  1. Finder > Go > Connect to Server (Cmd+K)
  2. Enter: smb://$TM_HOST/$TM_SHARE
  3. Then re-run: sudo tmutil setdestination -p '$TM_MOUNT'"
fi

# ── 9. Verify mount
if ! mount | grep -q "$TM_MOUNT"; then
    fail "Mount succeeded but $TM_MOUNT not visible in mount table"
fi
ok "Share is mounted at $TM_MOUNT"

# ── 10. Register with Time Machine
log "Registering $TM_MOUNT as Time Machine destination ..."
if tmutil setdestination -p "$TM_MOUNT" 2>/dev/null; then
    ok "Time Machine destination set"
elif tmutil setdestination "$TM_MOUNT" 2>/dev/null; then
    ok "Time Machine destination set (legacy flag)"
else
    warn "tmutil setdestination failed — you may need to re-add manually:"
    warn "  System Settings > General > Time Machine > Add Backup Disk"
fi

# ── 11. Show current destinations
log "Current Time Machine destinations:"
tmutil destinationinfo 2>/dev/null | grep -E "^(Name|URL|Mount)" | sed 's/^/  /'

echo ""
ok "Setup complete. To start a backup now:"
echo "   tmutil startbackup"
echo ""
log "Tip: to make this persistent across reboots, add a launchd plist that"
log "     mounts the share on network-up. See mac/launchd/ for examples."
