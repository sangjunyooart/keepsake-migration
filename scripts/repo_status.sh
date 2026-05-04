#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Repo: $ROOT_DIR"
echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

current_branch="$(git rev-parse --abbrev-ref HEAD)"
echo "Current branch: $current_branch"

if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  echo "Rebase state: in progress"
else
  echo "Rebase state: none"
fi

upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -n "$upstream_ref" ]; then
  divergence="$(git rev-list --left-right --count HEAD..."$upstream_ref")"
  ahead="$(echo "$divergence" | awk '{print $1}')"
  behind="$(echo "$divergence" | awk '{print $2}')"
  echo "Upstream: $upstream_ref"
  echo "Ahead/behind: ${ahead}/${behind}"
else
  echo "Upstream: none"
fi

echo ""
echo "Working tree:"
if git diff --quiet && git diff --cached --quiet; then
  echo "clean tracked files"
else
  git status --short
fi

untracked="$(git ls-files --others --exclude-standard)"
if [ -n "$untracked" ]; then
  echo ""
  echo "Untracked files:"
  echo "$untracked"
fi

echo ""
echo "Recent commits:"
git log --oneline --decorate -5
