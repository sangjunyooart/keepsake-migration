#!/bin/bash
# Rebuilds the spectral_parallax venv so com.keepsake.parallax can auto-start.
# Reads package list from old venv's .dist-info metadata (works even when venv
# binary has a broken shebang), then rebuilds with a fresh venv.
#
# Usage: bash mac/launchd/setup-parallax-venv.sh

PARALLAX_DIR="$HOME/spectral_parallax"
REQ="$PARALLAX_DIR/requirements.txt"

echo "=== spectral_parallax venv setup ==="
echo "Project : $PARALLAX_DIR"
echo ""

if [ ! -d "$PARALLAX_DIR" ]; then
    echo "ERROR: $PARALLAX_DIR not found" >&2
    exit 1
fi

cd "$PARALLAX_DIR"

# ── 1. Generate requirements.txt if missing ──────────────────────────────────
if [ -f "$REQ" ]; then
    echo "Found existing requirements.txt:"
    cat "$REQ"
else
    echo "No requirements.txt — extracting from old venv dist-info..."
    # .dist-info/METADATA is plain text; readable even with broken venv binary
    TMPFILE=$(mktemp)
    find "$PARALLAX_DIR/venv/lib" -name "METADATA" 2>/dev/null | while read -r mf; do
        name=$(grep -m1 "^Name:" "$mf" | sed 's/Name: *//')
        ver=$(grep -m1 "^Version:" "$mf" | sed 's/Version: *//')
        if [ -n "$name" ] && [ -n "$ver" ]; then
            echo "$name==$ver"
        fi
    done | sort > "$TMPFILE"

    if [ -s "$TMPFILE" ]; then
        echo "Detected packages from old venv:"
        cat "$TMPFILE"
        cp "$TMPFILE" "$REQ"
    else
        echo "No dist-info found in old venv — using minimal FastAPI/uvicorn base."
        # Also scan Python imports to hint at what may be needed
        echo ""
        echo "Python imports found in project:"
        grep -rh "^import \|^from " ./*.py 2>/dev/null | sort -u
        echo ""
        cat > "$REQ" <<'EOF'
fastapi
uvicorn[standard]
EOF
        echo "Created minimal requirements.txt. Edit $REQ if more packages are needed."
    fi
    rm -f "$TMPFILE"
fi

echo ""

# ── 2. Rebuild venv ──────────────────────────────────────────────────────────
echo "Rebuilding venv with system python3..."
python3 -m venv venv --clear

echo "Installing packages..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r "$REQ"

echo ""
echo "=== Verification ==="
venv/bin/python -m uvicorn --version && echo "uvicorn OK"
echo "Shebang in venv/bin/uvicorn:"
head -1 venv/bin/uvicorn

echo ""
echo "=== Restart parallax service ==="
echo "Run: launchctl kickstart -k gui/\$(id -u)/com.keepsake.parallax"
echo "Then: curl -s -o /dev/null -w '%{http_code}' http://localhost:8765"
