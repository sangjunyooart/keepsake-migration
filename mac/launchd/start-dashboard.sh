#!/bin/bash
# Starts the Keepsake Control Panel (port 8080).
# Uses Python stdlib only — no venv required.

exec /usr/bin/python3 "$HOME/keepsake-migration/mac/monitoring/dashboard.py"
