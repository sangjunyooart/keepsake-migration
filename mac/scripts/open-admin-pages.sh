#!/bin/bash
# Opens Chrome with all admin and monitor pages after reboot.
# Called by com.keepsake.chrome-opener.plist via launchd.

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Wait for services to be ready
sleep 15

"$CHROME" \
    "http://localhost:8080" \
    "http://localhost:8080/monitor" \
    "https://keepsake-drift.net/monitor/" \
    --new-window \
    2>/dev/null &
