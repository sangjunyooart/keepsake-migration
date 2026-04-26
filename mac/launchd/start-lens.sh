#!/bin/bash
# Launcher for individual lens training system.
# Usage: start-lens.sh <lens_name>
# Called by launchd plist; runs with user's HOME set.

LENS_NAME="$1"
PROJECT_DIR="$HOME/keepsake-migration/mac"
VENV="$PROJECT_DIR/venv"

if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
fi

cd "$PROJECT_DIR"
exec python training/continual_loop.py --lens "$LENS_NAME"
