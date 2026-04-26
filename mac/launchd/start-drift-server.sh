#!/bin/bash
# Starts the uvicorn backend for a keepsake-drift project.
# Uses absolute path to venv/bin/uvicorn — no 'source activate' needed.
# cloudflared tunnel is managed separately by com.keepsake.cloudflared.
#
# Usage: start-drift-server.sh <project_dir> <port>

PROJECT_DIR="$1"
PORT="$2"

if [ -z "$PROJECT_DIR" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <project_dir> <port>" >&2
    exit 1
fi

UVICORN="$PROJECT_DIR/venv/bin/uvicorn"

if [ ! -x "$UVICORN" ]; then
    echo "ERROR: uvicorn not found at $UVICORN" >&2
    exit 1
fi

# Kill any previous uvicorn on this port (clean restart)
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR"
exec "$UVICORN" app:app --host 0.0.0.0 --port "$PORT"
