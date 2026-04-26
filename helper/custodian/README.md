# Custodian

Custodian is the helper-side stewarding agent for *Keepsake in Every Hair ~ Migration*.
It runs hourly checks and makes the artist's authorial gaze persistently present in the
system during autonomous operation.

**Custodian is helper-side. It never modifies artwork code.**

## Five checks

| # | Check | What it asks |
|---|---|---|
| 1 | `system_activity` | Are all 6 lenses actively cycling? |
| 2 | `training_progress` | Is training actually happening? |
| 3 | `data_flow` | Is data entering the system? |
| 4 | `pi_sync` | Do all 6 Pis have current adapters? |
| 5 | `ethics_boundary` | Is the ethics filter actually working? |

Check 5 is the most consequential. It independently re-verifies corpus chunks —
it does not trust that the data pipeline's filter ran correctly.

## Auto-actions

Custodian takes one automatic action: **ethics quarantine**.

If any corpus chunk contains a Masa keyword variant:
1. The chunk is moved to `mac/corpus/quarantine/<timestamp>/` with a metadata file.
2. Training for the affected lens is paused via `mac/runtime_state/{lens}.json`.
3. A Telegram critical push is sent immediately.

The artist must review quarantined chunks at `/monitor/custodian/quarantine/`
before training resumes.

## Output forms

- **Dashboard**: `/monitor/custodian/` — live status of all 5 checks
- **Daily email**: 09:00 KST — summary of all checks (even if all healthy)
- **Telegram**: immediate push for critical conditions only

## Running

```bash
# Start manually (runs forever):
cd /Users/sangjunyooart/keepsake-migration
source mac/venv/bin/activate
python -m helper.custodian.runner

# Install as launchd service (auto-start on login):
cp mac/launchd/com.keepsake.custodian.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.keepsake.custodian.plist
```

## State files

All written by the runner — do not edit manually.

```
helper/custodian/state/
├── current.json       # most recent check results
├── history.jsonl      # every check, append-only
├── incidents.jsonl    # warnings + criticals only
└── rate_limiter.json  # Telegram rate limit state
```

## Telegram setup

See `setup_telegram.md`.

## Configuration

`mac/config/custodian_config.yaml` — thresholds, intervals, email time.

Environment variables (add to `mac/.env`):
```
KEEPSAKE_CUSTODIAN_EMAIL=
KEEPSAKE_SMTP_HOST=
KEEPSAKE_SMTP_PORT=587
KEEPSAKE_SMTP_USER=
KEEPSAKE_SMTP_PASSWORD=
KEEPSAKE_TELEGRAM_BOT_TOKEN=
KEEPSAKE_TELEGRAM_CHAT_ID=
```
