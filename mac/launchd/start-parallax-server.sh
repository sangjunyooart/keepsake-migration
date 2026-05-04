#!/bin/bash
PROJECT="${1:-/Users/junyoo182/spectral_parallax}"
PORT="${2:-8765}"

cd "$PROJECT"
source venv/bin/activate
export PYTHONPATH=src

pkill -f "mechanical_perceiver.radio_demo" 2>/dev/null || true
sleep 0.5
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 0.5

exec python -m mechanical_perceiver.radio_demo --multi --port "$PORT"
