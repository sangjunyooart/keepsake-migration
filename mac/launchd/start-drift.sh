#!/bin/bash
# Launcher for keepsake-drift server.
# Starts with OPENAI_AUTO=false (auto tick OFF).

PROJECT_DIR="$HOME/keepsake-drift"
VENV="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

# OpenAI auto tick OFF — hardcoded here so it survives .env changes
export OPENAI_AUTO=false

if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
fi

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    # Re-assert: .env must not override this
    export OPENAI_AUTO=false
fi

cd "$PROJECT_DIR"

# Try Node.js server first, fall back to Python
if [ -f "server.js" ]; then
    exec node server.js
elif [ -f "app.py" ]; then
    exec python app.py
elif [ -f "package.json" ]; then
    exec npm start
else
    echo "ERROR: No server entry point found in $PROJECT_DIR" >&2
    exit 1
fi
