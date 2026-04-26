#!/bin/bash
# Launcher for keepsake-migration monitoring dashboard (Flask, port 8080).

PROJECT_DIR="$HOME/keepsake-migration/mac"
VENV="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
fi

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

cd "$PROJECT_DIR"
exec python monitoring/dashboard.py
