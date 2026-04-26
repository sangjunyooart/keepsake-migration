#!/bin/bash
# Starts only the uvicorn backend for a keepsake-drift project.
# cloudflared tunnel is managed separately by com.keepsake.cloudflared.
#
# Usage: start-drift-server.sh <project_dir> <port>
#   e.g. start-drift-server.sh /Users/junyoo182/Desktop/keepsake_drift 8000

PROJECT_DIR="$1"
PORT="$2"

if [ -z "$PROJECT_DIR" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <project_dir> <port>" >&2
    exit 1
fi

cd "$PROJECT_DIR"
source venv/bin/activate

# Kill any previous uvicorn on this port (clean restart)
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 1

exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
