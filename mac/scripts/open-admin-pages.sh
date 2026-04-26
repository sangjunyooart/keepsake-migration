#!/bin/bash
# Opens the Keepsake Control Panel in Chrome after reboot.
# Single window replaces all individual admin/monitor pages.

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Wait for the dashboard server to be ready
sleep 20

"$CHROME" "http://localhost:8080" --new-window 2>/dev/null &
