#!/bin/bash
PROJECT="${1:-/Users/junyoo182/keepsake_drift}"
PORT="${2:-8000}"

cd "$PROJECT"

lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 0.5

exec /Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python \
  -m uvicorn app:app --host 0.0.0.0 --port "$PORT"
