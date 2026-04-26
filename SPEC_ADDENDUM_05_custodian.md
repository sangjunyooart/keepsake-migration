# Spec Addendum 05 — Custodian: Stewarding Agent for Conceptual + Technical Integrity

> **For Claude Code**: This addendum extends `CLAUDE_CODE_BUILD_SPEC_v2.md`. Read v2 spec first. This addendum adds a new helper-side subsystem; it does not modify any artwork-side code.

---

## Why This Addendum Exists

The system now trains 6 lenses on Mac and pushes adapters to 6 Pi inference bodies. As training proceeds autonomously over weeks and months — including during the artist's recovery period in Korea — there needs to be an entity that watches whether the system is operating *both technically and conceptually* in alignment with the work.

This entity is called **Custodian**. It is not part of the artwork. It belongs to the helper side. Its role is to make the artist's authorial gaze persistently present inside the system, even when the artist is recovering or otherwise unavailable.

Custodian is *agent-like* in three senses:
- It performs autonomous evaluations (not just data display)
- It takes contextual actions (auto-quarantine on ethics breach)
- Its judgments derive from delegated authorial intent (not its own)

This is not a fully autonomous agent in the philosophical sense — its intentionality is the artist's. But it operates with enough independence that "stewarding agent" is the appropriate framing.

---

## What Custodian Does (Five Checks)

Custodian runs five checks periodically (default: every hour) and produces three forms of output: continuous dashboard updates, daily email summary, and immediate Telegram push for critical conditions.

### Check 1 — System Activity

**Question**: Are all 6 lenses active?

**Inspects**:
- Last cycle timestamp per lens (from `mac/logs/cycles/<lens>.jsonl`)
- Last meta-controller decision timestamp per lens
- Last active learning search timestamp per lens

**Thresholds**:
- `info`: lens cycled within expected interval × 1.5
- `warning`: lens has not cycled in expected interval × 3
- `critical`: lens has not cycled in expected interval × 6 OR all 6 lenses idle for 24h

### Check 2 — Training Progress

**Question**: Is training actually happening?

**Inspects**:
- Adapter checkpoint count per lens (from `mac/adapters/<lens>/`)
- Last training timestamp per lens
- Loss trajectory of last 5 training sessions per lens
- Corpus size vs `min_corpus_chunks`

**Thresholds**:
- `info`: training proceeding, loss trending down or stable
- `warning`: corpus sufficient but no training in 7 days, OR loss not decreasing across 5 sessions
- `warning`: adapter count growing faster than 1/hour (over-training risk)
- `critical`: adapter count not growing in 14 days despite sufficient corpus

### Check 3 — Data Flow

**Question**: Is data entering the system?

**Inspects**:
- Raw corpus directory file count delta per lens (last 24h, 7d)
- Active learning search results count per lens (last 24h, 7d)
- Historical collector activity (when timeline populated)

**Thresholds**:
- `info`: new data arriving for at least one lens daily
- `warning`: no new data for any lens in 7 days
- `warning`: search queries dispatched but 0 results returned (API issue)
- `critical`: no new data system-wide in 14 days

### Check 4 — Pi Sync

**Question**: Do all 6 Pis have current adapters?

**Inspects**:
- Latest adapter version per lens on Mac
- Current adapter version on each Pi (via `/status` endpoint)
- Last successful push timestamp per Pi
- Pi reachability (HTTP /status response)

**Thresholds**:
- `info`: all Pis at latest version, all reachable
- `warning`: a Pi is more than 2 versions behind, OR was unreachable in last hour
- `warning`: push attempted but failed in last 24h
- `critical`: a Pi unreachable for 24h, OR push has failed 5+ consecutive times

### Check 5 — Ethics Boundary

**Question**: Is the ethics filter actually working?

This check is not optional. It performs **active verification**, not passive trust. The artist has promised Masa that his subjective material never enters training. Custodian must continually verify this is true.

**Inspects**:
- Random sample of 50 chunks from `mac/corpus/processed/<lens>/` per lens per check
- Pass each through `EthicsFilter.is_safe()` independently
- Verify result: should be True for all
- ALSO: scan 50 random chunks for known Masa keyword variants directly (defense in depth)
- Verify recent active learning rejections were logged (filter actively working)

**Thresholds**:
- `info`: 0 leaks found, filter logging active rejections
- `critical`: any chunk containing Masa keyword variant — IMMEDIATE quarantine + Telegram push
- `warning`: filter not logging rejections in 7d (filter may be inactive even if no leaks)

**Auto-action on critical**: chunk is moved to `mac/corpus/quarantine/<timestamp>/` with metadata noting source file, what was detected, and which lens's corpus it came from. Training cycles for that lens are temporarily paused until artist reviews.

---

## Output Forms

### Form 1 — Continuous Dashboard Updates

Custodian writes its check results to a structured log that the existing dashboard reads:

- `helper/custodian/state/current.json` — most recent check results
- `helper/custodian/state/history.jsonl` — every check, append-only
- `helper/custodian/state/incidents.jsonl` — all warnings + criticals

Dashboard adds a `/monitor/custodian/` page showing:
- Current status of all 5 checks (color-coded)
- Recent incidents (last 7d)
- Trend graphs (lens differentiation distance over time, adapter version distribution, etc.)
- Quarantine review interface (if any chunks have been quarantined)

### Form 2 — Daily Email Summary

Once per day (default: 09:00 in `system.timezone`), Custodian sends a summary email to the artist.

**Recipient**: configurable via env var `KEEPSAKE_CUSTODIAN_EMAIL`
**SMTP**: configurable via env vars (`KEEPSAKE_SMTP_HOST`, etc.) — supports common providers (Gmail with app password, Fastmail, ProtonMail Bridge)

**Format** (plain text, mobile-readable):

```
Keepsake Custodian Report — 2026-05-10

Overall: 1 warning, 0 critical. System healthy.

System Activity:    ✓ All 6 lenses active in last 24h
Training Progress:  ⚠ digital_time: no training in 48h (last loss: 2.31)
                    ✓ 5 other lenses training normally
Data Flow:          ✓ Active learning producing results across all lenses
Pi Sync:            ✓ 6 Pis at latest adapter versions
Ethics Boundary:    ✓ Filter blocked 3 attempts in last 24h, 0 leaks

Lens activity (last 24h):
  human_time            12 cycles    1 training    loss 2.14 ↓
  infrastructure_time    4 cycles    0 training
  environmental_time     2 cycles    0 training
  digital_time         288 cycles    0 training    [warning]
  liminal_time           1 cycles    0 training
  more_than_human_time   1 cycles    0 training

Dashboard: https://keepsake-drift.net/monitor/custodian/

— Custodian
```

If overall status is `info` (no warnings, no critical), email is still sent — daily heartbeat confirms Custodian itself is alive.

### Form 3 — Telegram Critical Push

For critical incidents only, Custodian sends an immediate Telegram message to the artist via Telegram Bot API.

**Setup**: 
- Artist creates a Telegram bot via @BotFather
- Bot token stored in env var `KEEPSAKE_TELEGRAM_BOT_TOKEN`
- Artist's chat ID stored in env var `KEEPSAKE_TELEGRAM_CHAT_ID`
- Setup instructions in `helper/custodian/setup_telegram.md`

**Message format** (concise, actionable):

```
[Keepsake CRITICAL]
Ethics filter leak detected.

Source: corpus/processed/digital_time/abc123_0008.txt
Detected: Masa keyword variant
Action: Auto-quarantined; digital_time training paused.

Review: keepsake-drift.net/monitor/custodian/quarantine
```

```
[Keepsake CRITICAL]
Pi sync failure.

Pi 3 (environmental_time) unreachable for 24h.
Last successful push: 2026-05-08 14:22

System continues with last known adapter on Pi 3.
Dashboard: keepsake-drift.net/monitor/custodian
```

**Rate limiting**: same critical type does not push more than once per 6 hours. Aggregated digest sent if multiple criticals in short window.

**No Telegram for warnings**: warnings appear in dashboard and daily email only. Telegram is reserved for genuine criticals — protects artist from notification fatigue during recovery.

---

## Architecture

### New directory: `helper/custodian/`

```
helper/custodian/
├── __init__.py
├── runner.py                    # Main loop, scheduled checks
├── checks/
│   ├── __init__.py
│   ├── base.py                  # Check abstract class
│   ├── system_activity.py       # Check 1
│   ├── training_progress.py     # Check 2
│   ├── data_flow.py             # Check 3
│   ├── pi_sync.py               # Check 4
│   └── ethics_boundary.py       # Check 5 (with auto-quarantine)
├── alerts/
│   ├── __init__.py
│   ├── telegram_pusher.py       # Telegram Bot API integration
│   ├── email_sender.py          # SMTP integration
│   └── rate_limiter.py          # Avoid notification fatigue
├── state/                       # gitignored
│   ├── current.json             # latest check results
│   ├── history.jsonl            # append-only
│   └── incidents.jsonl          # warnings + criticals
├── dashboard_views/
│   ├── custodian_view.py        # Flask blueprint, mounted at /monitor/custodian
│   └── templates/
│       ├── overview.html
│       ├── incidents.html
│       └── quarantine.html
├── setup_telegram.md            # Artist-facing setup guide
└── README.md
```

### Configuration: `mac/config/custodian_config.yaml`

```yaml
custodian:
  check_interval_seconds: 3600   # hourly
  
  daily_email:
    enabled: true
    time_of_day: "09:00"
    timezone: "Asia/Seoul"
  
  telegram:
    enabled: true
    rate_limit_per_critical_type_seconds: 21600  # 6 hours
  
  thresholds:
    system_activity:
      warning_multiplier: 3.0     # warn at expected_interval × 3
      critical_multiplier: 6.0
    
    training_progress:
      warning_no_training_days: 7
      critical_no_training_days: 14
      over_training_per_hour_threshold: 1
    
    data_flow:
      warning_no_data_days: 7
      critical_no_data_days: 14
    
    pi_sync:
      warning_versions_behind: 2
      critical_unreachable_hours: 24
      critical_consecutive_push_failures: 5
    
    ethics_boundary:
      sample_size_per_check: 50
      warning_no_rejections_days: 7
  
  quarantine:
    auto_pause_lens_training: true
    require_artist_review: true
```

### Launchd integration: `mac/launchd/com.keepsake.custodian.plist`

Custodian runs as a launchd service on Mac, separate from continual_loop. Auto-starts on boot, runs continuously, logs to `helper/custodian/state/`.

### Environment variables

Add to `mac/.env.example`:

```
KEEPSAKE_CUSTODIAN_EMAIL=artist@example.com
KEEPSAKE_SMTP_HOST=smtp.example.com
KEEPSAKE_SMTP_PORT=587
KEEPSAKE_SMTP_USER=...
KEEPSAKE_SMTP_PASSWORD=...
KEEPSAKE_TELEGRAM_BOT_TOKEN=...
KEEPSAKE_TELEGRAM_CHAT_ID=...
```

Setup guide in `helper/custodian/setup_telegram.md` walks artist through Telegram bot creation.

---

## Module Specifications

### `helper/custodian/checks/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class CheckResult:
    check_name: str
    severity: Severity
    summary: str           # one-line summary for dashboard/email
    details: dict          # structured data for full inspection
    timestamp: datetime
    auto_action: Optional[str] = None  # description if Custodian took action

class Check(ABC):
    name: str
    
    def __init__(self, mac_root, config, lens_configs):
        self.mac_root = mac_root
        self.config = config
        self.lens_configs = lens_configs
    
    @abstractmethod
    def run(self) -> CheckResult:
        ...
```

### `helper/custodian/checks/ethics_boundary.py`

This is the most consequential check. Specification:

```python
class EthicsBoundaryCheck(Check):
    name = "ethics_boundary"
    
    def __init__(self, mac_root, config, lens_configs):
        super().__init__(mac_root, config, lens_configs)
        from shared.ethics_filter import EthicsFilter
        self.filter = EthicsFilter()
    
    def run(self) -> CheckResult:
        leaks = []
        sample_size = self.config['thresholds']['ethics_boundary']['sample_size_per_check']
        
        for lens_name in self.lens_configs['lenses']:
            corpus_dir = self.mac_root / "corpus" / "processed" / lens_name
            if not corpus_dir.exists():
                continue
            
            # Sample 50 chunks
            chunks = list(corpus_dir.glob("*.txt"))
            sampled = random.sample(chunks, min(sample_size, len(chunks)))
            
            for chunk_path in sampled:
                text = chunk_path.read_text()
                # Active verification: independent re-check
                if not self.filter.is_safe(text):
                    leaks.append({
                        "lens": lens_name,
                        "path": str(chunk_path),
                        "detected_at": datetime.now().isoformat(),
                    })
                    self._quarantine(chunk_path, lens_name)
        
        # Verify filter is actively logging rejections
        rejection_log = self.mac_root / "logs" / "ethics_rejections.jsonl"
        recent_rejections = self._count_recent_rejections(rejection_log, days=7)
        
        if leaks:
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=f"{len(leaks)} ethics leak(s) detected, auto-quarantined",
                details={"leaks": leaks, "recent_rejections": recent_rejections},
                timestamp=datetime.now(),
                auto_action=f"Quarantined {len(leaks)} chunks; "
                            f"paused training for affected lenses",
            )
        elif recent_rejections == 0:
            return CheckResult(
                check_name=self.name,
                severity=Severity.WARNING,
                summary="Filter has logged 0 rejections in 7d (may be inactive)",
                details={"recent_rejections": 0},
                timestamp=datetime.now(),
            )
        else:
            return CheckResult(
                check_name=self.name,
                severity=Severity.INFO,
                summary=f"0 leaks; filter blocked {recent_rejections} attempts in last 7d",
                details={"recent_rejections": recent_rejections},
                timestamp=datetime.now(),
            )
    
    def _quarantine(self, chunk_path, lens_name):
        quarantine_dir = self.mac_root / "corpus" / "quarantine" / datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        target = quarantine_dir / chunk_path.name
        chunk_path.rename(target)
        # Write metadata
        meta = {
            "original_path": str(chunk_path),
            "lens": lens_name,
            "quarantined_at": datetime.now().isoformat(),
            "reason": "ethics_filter_leak",
        }
        (quarantine_dir / f"{chunk_path.name}.meta.json").write_text(json.dumps(meta, indent=2))
        # Pause lens training via runtime_state
        runtime_state_path = self.mac_root / "runtime_state" / f"{lens_name}.json"
        if runtime_state_path.exists():
            state = json.loads(runtime_state_path.read_text())
            state['training_enabled'] = False
            state['paused_by'] = 'custodian'
            state['paused_reason'] = 'ethics_quarantine'
            state['paused_at'] = datetime.now().isoformat()
            runtime_state_path.write_text(json.dumps(state, indent=2))
```

### `helper/custodian/alerts/telegram_pusher.py`

```python
import os
import requests
import logging

class TelegramPusher:
    def __init__(self, rate_limiter):
        self.token = os.environ.get("KEEPSAKE_TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("KEEPSAKE_TELEGRAM_CHAT_ID")
        self.rate_limiter = rate_limiter
        if not self.token or not self.chat_id:
            logging.warning("Telegram not configured; criticals will not push")
    
    def push_critical(self, check_name: str, message: str):
        if not self.token:
            return False
        if not self.rate_limiter.allow(check_name):
            logging.info(f"Telegram suppressed by rate limiter: {check_name}")
            return False
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            response = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": f"[Keepsake CRITICAL]\n{message}",
                "disable_web_page_preview": False,
            }, timeout=10)
            return response.ok
        except Exception as e:
            logging.error(f"Telegram push failed: {e}")
            return False
```

### `helper/custodian/runner.py`

Main loop. Runs all checks at interval, dispatches results to dashboard state, daily email accumulator, and Telegram for criticals.

```python
class CustodianRunner:
    def __init__(self, mac_root):
        self.mac_root = mac_root
        self.config = self._load_config()
        self.lens_configs = self._load_lens_configs()
        self.checks = self._init_checks()
        self.telegram = TelegramPusher(...)
        self.email = EmailSender(...)
    
    def run_forever(self):
        while True:
            results = []
            for check in self.checks:
                try:
                    result = check.run()
                    results.append(result)
                    self._record(result)
                    if result.severity == Severity.CRITICAL:
                        self._push_critical(result)
                except Exception as e:
                    logging.exception(f"Check {check.name} failed")
            
            self._update_dashboard_state(results)
            
            if self._is_email_time():
                self._send_daily_email()
            
            time.sleep(self.config['check_interval_seconds'])
```

---

## Dashboard Integration

Add Flask blueprint at `/monitor/custodian/`:

- `/monitor/custodian/` — overview page (5 checks, current status, last 7d trend)
- `/monitor/custodian/incidents` — chronological list of warnings + criticals
- `/monitor/custodian/quarantine` — review quarantined chunks, restore or permanently delete

The quarantine review interface allows artist to:
- Inspect each quarantined chunk
- See why it was quarantined (which keyword matched)
- Either: confirm quarantine (chunk deleted permanently) or false positive (chunk restored to corpus, ethics filter pattern adjusted if needed)

This human-in-the-loop step is essential. Auto-quarantine is the safe default; final disposition requires artist review.

---

## Setup Guide for Artist

`helper/custodian/setup_telegram.md` content:

```markdown
# Telegram Setup for Custodian

To receive critical alerts on your phone:

1. Open Telegram and search for `@BotFather`. Start a chat.
2. Send `/newbot`. Follow prompts. Choose a name (e.g., "Keepsake Custodian") 
   and a username ending in `bot` (e.g., `keepsake_custodian_bot`).
3. BotFather sends you a token. Copy it.
4. Open a chat with your new bot. Send any message (e.g., "hi").
5. In a browser, visit:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   Find your chat ID in the response (`"chat":{"id":NUMBER}`).
6. Add to `mac/.env`:
   ```
   KEEPSAKE_TELEGRAM_BOT_TOKEN=...your token...
   KEEPSAKE_TELEGRAM_CHAT_ID=...your chat id...
   ```
7. Test:
   ```
   cd mac
   python3 -m helper.custodian.alerts.telegram_pusher --test
   ```
   You should receive a test message.

That's it. Custodian will now push critical alerts to your phone.
```

---

## Build Order

1. `helper/custodian/` directory structure
2. `helper/custodian/checks/base.py` (abstract class)
3. `helper/custodian/checks/ethics_boundary.py` (most critical, build first)
4. `helper/custodian/checks/system_activity.py`
5. `helper/custodian/checks/training_progress.py`
6. `helper/custodian/checks/data_flow.py`
7. `helper/custodian/checks/pi_sync.py`
8. `helper/custodian/alerts/rate_limiter.py`
9. `helper/custodian/alerts/telegram_pusher.py`
10. `helper/custodian/alerts/email_sender.py`
11. `helper/custodian/runner.py` (main loop)
12. `helper/custodian/dashboard_views/` (Flask blueprint)
13. Mount custodian blueprint into existing dashboard at `/monitor/custodian/`
14. `mac/config/custodian_config.yaml`
15. `mac/launchd/com.keepsake.custodian.plist`
16. `helper/custodian/setup_telegram.md`
17. `helper/custodian/README.md`
18. Tests for ethics_boundary check (most consequential)
19. Test for telegram_pusher (with mock API)
20. Update `mac/.env.example` with Custodian env vars
21. Update top-level `README.md` to mention Custodian

---

## Success Criteria

After build:

1. ✅ `helper/custodian/` directory exists with all specified modules
2. ✅ `mac/config/custodian_config.yaml` exists with all thresholds
3. ✅ Custodian launchd service starts on Mac boot
4. ✅ All 5 checks run on schedule, results appear in `helper/custodian/state/current.json`
5. ✅ Dashboard at `/monitor/custodian/` shows current status
6. ✅ Test ethics leak (manually inject keyword into a corpus chunk): Custodian detects, quarantines, pauses lens, pushes Telegram alert (if configured)
7. ✅ Daily email sends at configured time, contains all 5 checks summary
8. ✅ Telegram push works on critical (verified with test_telegram script)
9. ✅ Rate limiter prevents repeated Telegram pushes within 6h window
10. ✅ Quarantine review UI allows restore + permanent delete
11. ✅ Custodian's own failures are logged but do not crash the artwork training pipeline (separation maintained)

---

## What This Addendum Does NOT Address

- Conceptual checks (lens differentiation, temporal authenticity) — deferred to Plexus residency (July 2026)
- Slack / Discord integration — not requested
- SMS push — Telegram suffices
- Multi-recipient emails — single artist recipient
- Dashboard authentication — already handled in Addendum 02

---

## Build Now

This addendum is self-contained. It adds new modules under `helper/custodian/`, new config under `mac/config/`, new launchd plist, and Flask blueprint mounted into existing dashboard. It does not modify artwork-side code.

Read the build order. Begin with `helper/custodian/checks/ethics_boundary.py` since it carries the most consequential function. Stop and confirm after that file before proceeding with remaining checks.

Begin.
