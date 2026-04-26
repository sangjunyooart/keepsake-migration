#!/bin/bash
# One-shot installer — run this once on the Mac mini after git clone/pull.
# Replaces YOUR_USERNAME with the actual macOS username in all plists,
# copies them to ~/Library/LaunchAgents/, then loads them.
#
# Usage:  bash mac/launchd/install.sh

set -e

USERNAME=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/keepsake-migration/mac/logs"

echo "=== Keepsake auto-start installer ==="
echo "Username  : $USERNAME"
echo "Plist dir : $SCRIPT_DIR"
echo "LaunchAgents: $LAUNCH_AGENTS"
echo ""

# Make sure log dirs exist
mkdir -p "$LOG_DIR"

# Make launcher scripts executable
chmod +x "$SCRIPT_DIR/start-lens.sh"
chmod +x "$SCRIPT_DIR/start-dashboard.sh"
chmod +x "$HOME/keepsake-migration/mac/scripts/open-admin-pages.sh"

PLISTS=(
    "com.keepsake.drift.plist"
    "com.keepsake.drift-en.plist"
    "com.keepsake.drift-gr.plist"
    "com.keepsake.drift-br.plist"
    "com.keepsake.migration.lens-human-time.plist"
    "com.keepsake.migration.lens-infrastructure-time.plist"
    "com.keepsake.migration.lens-environmental-time.plist"
    "com.keepsake.migration.lens-digital-time.plist"
    "com.keepsake.migration.lens-liminal-time.plist"
    "com.keepsake.migration.lens-more-than-human-time.plist"
    "com.keepsake.migration.dashboard.plist"
    "com.keepsake.chrome-opener.plist"
)

for PLIST in "${PLISTS[@]}"; do
    SRC="$SCRIPT_DIR/$PLIST"
    DST="$LAUNCH_AGENTS/$PLIST"

    # Substitute YOUR_USERNAME with real username
    sed "s/YOUR_USERNAME/$USERNAME/g" "$SRC" > "$DST"
    echo "Installed: $DST"

    # Unload if already loaded (ignore errors on first install)
    launchctl unload "$DST" 2>/dev/null || true

    # Load
    launchctl load "$DST"
    echo "  Loaded: $PLIST"
done

echo ""
echo "=== Done. All services will auto-start on every reboot. ==="
echo "To check status: launchctl list | grep keepsake"
echo "Logs: $LOG_DIR/"
