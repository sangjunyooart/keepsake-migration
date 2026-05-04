#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_DIR="$ROOT_DIR/backups/repo_state/$STAMP"
mkdir -p "$BACKUP_DIR"

BUNDLE_PATH="$BACKUP_DIR/repo.bundle"
SNAPSHOT_PATH="$BACKUP_DIR/status.txt"

git bundle create "$BUNDLE_PATH" --all

{
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "Repo: $ROOT_DIR"
  echo ""
  git status --short --branch
  echo ""
  git remote -v
  echo ""
  git branch -vv
  echo ""
  git log --graph --oneline --decorate --all --max-count=25
} > "$SNAPSHOT_PATH"

echo "Created:"
echo "  $BUNDLE_PATH"
echo "  $SNAPSHOT_PATH"
