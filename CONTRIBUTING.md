# Contributing to Keepsake Migration

This repo runs live local services on the Mac mini and syncs work to GitHub.
Use a handoff-first workflow so another contributor can continue without guessing.

## Scope

- `mac/monitoring/` powers the local dashboard at `http://localhost:8080/`
- `mac/launchd/` manages local auto-start services
- `mac/training/`, `mac/data_pipeline/`, and related folders drive the training system

## Branch workflow

1. Start from a clean, current branch:
   `git fetch origin`
   `git checkout -b codex/<short-task-name> origin/main`
2. Keep commits narrow and descriptive.
3. Avoid doing feature work on detached `HEAD` or during an in-progress rebase.
4. Before handoff, leave either:
   - a PR using `.github/PULL_REQUEST_TEMPLATE.md`, or
   - a note in `docs/handoffs/`

## Required handoff content

Every handoff should say:

- what changed
- what is still in progress
- what was intentionally not touched
- how the work was checked
- what the next contributor should do first

## Conflict avoidance

- Do not force-push shared branches.
- Do not rewrite `main` history unless the owner explicitly asks.
- Do not mix unrelated local machine experiments into shared commits.
- Preserve untracked local scratch files unless asked to clean them.
- If launchd, monitoring, or training changes overlap, call out the touched area clearly in the handoff note.

## Localhost monitoring checks

Before handoff or deploy-adjacent work, run:

```bash
bash scripts/repo_status.sh
curl -s http://localhost:8080/ | head
```

If the dashboard should be running, also verify:

```bash
launchctl list | grep keepsake
```

## GitHub sync

Use:

```bash
bash scripts/sync_with_github.sh
```

This performs a safe fetch, prints branch divergence, and fast-forwards the current branch only when the tree is clean.

## Backup

Use:

```bash
bash scripts/backup_repo_state.sh
```

This creates a timestamped git bundle and repository status snapshot under `backups/repo_state/`.
It backs up Git state and handoff context, not secrets or generated training data.
