#!/bin/bash
# Starts the spectral_parallax server (mechanical_perceiver.radio_demo).
# This project uses its own HTTP server, not uvicorn.
#
# Usage: start-parallax-server.sh <project_dir> <port>

PROJECT_DIR="$1"
PORT="${2:-8765}"

if [ -z "$PROJECT_DIR" ]; then
    echo "Usage: $0 <project_dir> [port]" >&2
    exit 1
fi

PYTHON="$PROJECT_DIR/venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: python not found at $PYTHON" >&2
    exit 1
fi

# Kill any previous instance on this port
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src"
exec "$PYTHON" -m mechanical_perceiver.radio_demo --multi --port "$PORT"
