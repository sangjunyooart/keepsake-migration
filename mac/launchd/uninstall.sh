#!/bin/bash
# Unloads and removes all keepsake launchd agents.
# Usage: bash mac/launchd/uninstall.sh

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

PLISTS=(
    "com.keepsake.cloudflared.plist"
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
    DST="$LAUNCH_AGENTS/$PLIST"
    if [ -f "$DST" ]; then
        launchctl unload "$DST" 2>/dev/null && echo "Unloaded: $PLIST"
        rm "$DST" && echo "  Removed: $DST"
    fi
done

echo "Done."
