#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "HEAD" ]; then
  echo "Detached HEAD detected. Stop here and attach to a branch before syncing."
  exit 1
fi

if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  echo "Rebase in progress. Finish or abort the rebase before syncing."
  exit 1
fi

echo "Fetching origin..."
git fetch origin --prune

upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -z "$upstream_ref" ]; then
  echo "No upstream configured for $branch."
  echo "Set one with: git branch --set-upstream-to origin/$branch $branch"
  exit 1
fi

divergence="$(git rev-list --left-right --count HEAD..."$upstream_ref")"
ahead="$(echo "$divergence" | awk '{print $1}')"
behind="$(echo "$divergence" | awk '{print $2}')"

echo "Branch: $branch"
echo "Upstream: $upstream_ref"
echo "Ahead/behind: ${ahead}/${behind}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Tracked changes are present. Commit or stash before syncing."
  exit 1
fi

if [ "$behind" -gt 0 ]; then
  echo "Fast-forwarding from $upstream_ref..."
  git pull --ff-only
else
  echo "No pull needed."
fi

if [ "$ahead" -gt 0 ]; then
  echo "Local commits are ready to push with: git push"
else
  echo "No local commits waiting to push."
fi
