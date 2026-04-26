#!/bin/bash
# Opens Chrome with all admin and monitor pages after reboot.
# Called by com.keepsake.chrome-opener.plist via launchd.

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Wait for services to be ready
sleep 20

"$CHROME" \
    "http://localhost:8000" \
    "http://localhost:8001" \
    "http://localhost:8002" \
    "http://localhost:8003" \
    "http://localhost:8080" \
    "http://localhost:8080/monitor" \
    --new-window \
    2>/dev/null &
