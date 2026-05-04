# Operations Structure

This document is the lightweight coordination map for contributors.

## Shared base

- Default remote branch: `origin/main`
- Do not begin feature work while a rebase is in progress

## Local services

- Dashboard source: `mac/monitoring/dashboard.py`
- Dashboard URL: `http://localhost:8080/`
- Launchd service helper: `mac/launchd/start-dashboard.sh`
- Launchd setup guide: `mac/launchd/setup.md`

## Monitoring

Use these checks before handoff:

- `bash scripts/repo_status.sh`
- `curl -s http://localhost:8080/ | head`
- `launchctl list | grep keepsake`

## GitHub sync

- Safe sync helper: `bash scripts/sync_with_github.sh`
- This helper will not auto-pull onto a dirty working tree

## Backup

- Git history backup: `bash scripts/backup_repo_state.sh`
- Secrets, adapters, corpus data, runtime state, and logs are intentionally excluded from git backups

## Handoff rule

No contributor should stop after code changes without leaving either:

- a PR with the template filled out, or
- a handoff note under `docs/handoffs/`
