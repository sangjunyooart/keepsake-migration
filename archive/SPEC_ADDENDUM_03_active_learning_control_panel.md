# Spec Addendum 03 — Active Learning + Remote Control Panel

> **For Claude Code**: This document extends `CLAUDE_CODE_BUILD_SPEC.md`, `SPEC_ADDENDUM_01_artwork_helper_separation.md`, and `SPEC_ADDENDUM_02_online_monitoring.md`. Read all four. Where they conflict, later addenda take precedence.

---

## Why This Addendum Exists

Through extended dialogue we (artist Sangjun + Claude) identified that the current system's autonomy is **passive** — it fetches from pre-configured RSS feeds. The artwork's conceptual claim requires **active autonomy** — each lens identifies what it doesn't know about Masa's spatiotemporal trajectory, then actively searches archives to fill those gaps.

This addendum adds:

1. **Active learning** — lenses self-assess gaps in their corpus and search archives autonomously
2. **Historical data collector** — processes Masa's life timeline (when received) to drive targeted search
3. **OpenCLAW integration** — re-purposed as the LLM-driven decision engine for active search (not just orchestration)
4. **Systemd services** — true process autonomy (auto-start on boot, auto-restart on crash)
5. **Remote control panel** — dashboard extended so I can monitor health, set token budgets, and toggle autonomous training from anywhere

Without this addendum, the system would be a data pump, not an agent.

---

## Conceptual Framework

### Two Modes of Data Collection — Both Required

The system needs two complementary data flows:

**Mode A — Passive RSS ingestion** (already built):
- Fixed RSS sources fetched on schedule
- General contemporary data
- Provides ongoing "current environmental drift" once exhibition starts

**Mode B — Active historical search** (this addendum):
- Driven by Masa's life timeline
- Targeted searches for specific year × location × topic combinations
- Fills the *Masa-specific* trajectory data the lens needs to embody his spatiotemporal lens
- Self-directed; no human triggers

### Why Active Learning Specifically

The lens cannot be trained on Masa's subjective materials (ethics constraint). It must be trained on the *objective spatiotemporal traces of his life*. This requires:

- Year-by-year, place-by-place archive material
- Beyond what any pre-configured RSS list can deliver
- Discovered through search, not through static configuration

This is the technical reason **active learning is not optional** — without it, the lens cannot become Masa-specific while remaining ethically clean.

### OpenCLAW Re-positioned

Earlier specs treated OpenCLAW as optional orchestration. **This addendum repositions OpenCLAW as the active search decision engine**: query generation, source selection, result evaluation, learning value judgments. Its absence would force these decisions to be hand-coded heuristics, which would not capture the artwork's autonomy claim.

---

## Phase Strategy — Realistic Timeline

Given April 2026 build window before May 15 Korea departure:

### Phase 1 — April (now → May 10): Minimal Active Learning

Build a working but conservative active learning system:
- 1-2 archive sources (NOAA Climate Data, Wikipedia)
- Conservative daily token budget (50 tokens/lens/day default)
- Self-assessment module functional but simple (coverage measurement)
- Active search module functional for environmental_time lens first
- Systemd services for all process autonomy
- Remote control panel operational

**Goal**: System runs autonomously with limited but real active learning by Korea departure.

### Phase 2 — May–June (Korea, recovery): Stable autonomous operation

System runs in Korea with Phase 1 capabilities. I monitor remotely. No new development. If something breaks badly, I disable that lens via the control panel and continue with the rest.

### Phase 3 — July (Plexus residency): Expansion

Add additional sources (Internet Archive, JMA, USGS), increase token budgets, refine evaluation algorithms, integrate Masa's six memory inputs. This is exhibition preparation, not initial build.

**This addendum specifies Phase 1 only.** Phase 3 will be a future addendum.

---

## Architecture — New Modules

### Active Learning Pipeline (artwork/active_learning/)

```
artwork/active_learning/
├── __init__.py
├── self_assessment.py       # Lens evaluates its own corpus gaps
├── query_generator.py       # LLM-driven search query generation
├── search_orchestrator.py   # Dispatches searches across sources
├── source_adapters/
│   ├── __init__.py
│   ├── base.py              # Abstract interface
│   ├── noaa_adapter.py      # NOAA Climate Data API
│   └── wikipedia_adapter.py # Wikipedia search + content extraction
├── result_evaluator.py      # Judges relevance, quality, ethics
└── token_budget.py          # Tracks and enforces daily LLM token usage
```

### Historical Data Collector (artwork/historical/)

```
artwork/historical/
├── __init__.py
├── timeline_loader.py       # Parses Masa's timeline YAML
├── gap_identifier.py        # Cross-references timeline against corpus
└── targeted_search.py       # Drives active search toward identified gaps
```

### OpenCLAW Integration (artwork/openclaw/)

```
artwork/openclaw/
├── __init__.py
├── client.py                # OpenCLAW API/SDK wrapper
├── decisions.py             # OpenCLAW-driven decisions (query gen, evaluation)
└── budget_aware.py          # Wraps OpenCLAW calls with budget enforcement
```

### Systemd Services (helper/systemd/)

```
helper/systemd/
├── keepsake-lens@.service   # Template — instantiated per lens
├── keepsake-dashboard.service  # Pi 1 dashboard service
├── keepsake-tunnel.service  # Cloudflare tunnel service
└── setup.md                 # Manual installation instructions
```

### Control Panel Extension (helper/monitoring/)

Existing dashboard extended with:
- Toggle controls (training enable/disable per lens)
- Budget controls (daily token limit per lens)
- Real-time health summary
- Per-lens detail with active search history

---

## Detailed Module Specs

### Module 1 — `artwork/active_learning/self_assessment.py`

```python
class SelfAssessment:
    """
    Evaluates a lens's corpus against the spatiotemporal claims 
    it should be embodying. Identifies gaps.
    """
    
    def __init__(self, lens_name: str, lens_config: dict, 
                 corpus_dir: Path, timeline: Optional[dict]):
        ...
    
    def measure_period_coverage(self, period: str, location: str) -> float:
        """
        Returns 0.0 (no coverage) to 1.0 (well covered) for a 
        specific period × location.
        Uses TF-IDF keyword matching against corpus chunks.
        """
        ...
    
    def identify_gaps(self) -> List[Gap]:
        """
        Returns prioritized list of gaps in lens's coverage of 
        Masa's timeline.
        Each Gap: {period, location, current_coverage, priority, suggested_topics}
        """
        ...
    
    def report_state(self) -> dict:
        """
        Returns full corpus state for control panel display.
        """
        ...
```

The self-assessment runs **without any LLM calls** — it's pure local analysis. Cheap, runs every cycle.

### Module 2 — `artwork/active_learning/query_generator.py`

```python
class QueryGenerator:
    """
    LLM-driven search query generation for identified gaps.
    Uses OpenCLAW for the LLM call.
    """
    
    def __init__(self, openclaw_client, budget_enforcer):
        ...
    
    def generate_queries(self, gap: Gap, max_queries: int = 3) -> List[str]:
        """
        Given a gap, generates 3 diverse search queries.
        Budget-aware: refuses if daily budget would be exceeded.
        Returns empty list if no budget remaining.
        """
        ...
```

This module is the primary token consumer. Budget enforcement happens here. Each query generation costs ~10-20 tokens; with 50 token daily budget, ~3 query generations per day per lens.

### Module 3 — `artwork/active_learning/search_orchestrator.py`

```python
class SearchOrchestrator:
    """
    Dispatches generated queries to source adapters.
    Aggregates and deduplicates results.
    """
    
    def __init__(self, adapters: List[SourceAdapter], ethics_filter):
        ...
    
    def search(self, queries: List[str], gap: Gap) -> List[SearchResult]:
        """
        Runs all queries against all adapters in parallel.
        Filters through ethics filter before returning.
        Returns up to N best results.
        """
        ...
```

### Module 4 — Source adapters

`artwork/active_learning/source_adapters/base.py`:

```python
class SourceAdapter(ABC):
    name: str
    requires_api_key: bool
    
    @abstractmethod
    def search(self, query: str, gap_context: Gap) -> List[SearchResult]:
        ...
    
    @abstractmethod
    def fetch_content(self, result: SearchResult) -> str:
        ...
```

`noaa_adapter.py`: Uses NOAA Climate Data Online API. Free, no API key for limited queries. Ideal for environmental_time gaps with location + year.

`wikipedia_adapter.py`: Uses Wikipedia search API. Free, no API key. Returns article excerpts that match query. Good general-purpose historical context.

### Module 5 — `artwork/active_learning/result_evaluator.py`

```python
class ResultEvaluator:
    """
    Judges search results: relevance to gap, quality, ethics safety.
    """
    
    def __init__(self, ethics_filter, openclaw_client, budget_enforcer):
        ...
    
    def evaluate(self, result: SearchResult, gap: Gap) -> Evaluation:
        """
        Returns: {relevance: 0-1, quality: 0-1, ethics_safe: bool, decision: keep|reject}
        Uses OpenCLAW for relevance judgment (1 LLM call per batch of 5 results, 
        budget-aware).
        """
        ...
```

Batched evaluation to economize tokens. 5 results per LLM call.

### Module 6 — `artwork/active_learning/token_budget.py`

```python
class TokenBudgetEnforcer:
    """
    Tracks and enforces per-lens daily token budget.
    Persisted to disk so it survives restarts.
    """
    
    def __init__(self, lens_name: str, daily_budget: int, log_dir: Path):
        ...
    
    def request(self, estimated_tokens: int) -> bool:
        """
        Returns True if budget available, False otherwise.
        On True: deducts from today's budget.
        """
        ...
    
    def remaining_today(self) -> int:
        ...
    
    def reset_daily(self):
        """Called at midnight by scheduler."""
        ...
    
    def update_budget(self, new_daily_budget: int):
        """
        Called when control panel changes the budget. 
        Persists immediately.
        """
        ...
```

Budget is configurable at runtime via control panel — does NOT require redeploy.

### Module 7 — `artwork/historical/timeline_loader.py`

Loads Masa's timeline from YAML:

```yaml
# masa_timeline.yaml — provided by Masa, manually edited if needed
masa_timeline:
  - period: "1980-1998"
    location: "Tokyo, Setagaya"
    context: "childhood and youth"
    visa_status: "Japanese citizen, native"
  
  - period: "1998-2002"
    location: "Tokyo, Shinjuku"
    context: "university"
    visa_status: "Japanese citizen, native"
  
  - period: "2003-2010"
    location: "New York, Brooklyn"
    context: "MFA, early professional"
    visa_status: "F-1, then OPT, then O-1"
  
  - period: "2010-present"
    location: "Los Angeles, Echo Park"
    context: "professional musician"
    visa_status: "O-1, then green card pending"
```

Loader returns structured timeline that other modules consume.

### Module 8 — `artwork/historical/gap_identifier.py`

```python
class GapIdentifier:
    """
    Cross-references Masa's timeline against the lens's corpus.
    Returns gaps prioritized by:
    - Coverage shortfall (lower coverage = higher priority)
    - Time period weight (more recent ≠ higher priority; depends on lens)
    - Location significance (longer residence = higher priority)
    """
```

Each lens type weights periods differently:
- environmental_time: weights by environmental significance (extreme weather years rank higher)
- infrastructure_time: weights by visa transition years (status changes rank higher)
- digital_time: weights by media transitions of his generation
- etc.

### Module 9 — `artwork/openclaw/client.py`

OpenCLAW SDK wrapper. Specifics depend on OpenCLAW's actual API (artist will review at https://openclaw.ai). Wrapper provides:

```python
class OpenCLAWClient:
    def __init__(self, mode: Literal["local", "api"], config: dict):
        """
        mode='local' if OpenCLAW runs on the Pi (preferred)
        mode='api' if OpenCLAW requires external API calls
        """
        ...
    
    def generate(self, prompt: str, max_tokens: int = 50) -> str:
        ...
    
    def estimate_tokens(self, prompt: str) -> int:
        ...
```

If OpenCLAW operates locally on the Pi, token costs are zero (only compute time). If it operates via external API, the budget enforcer is critical.

**Note for Claude Code**: until OpenCLAW's actual API is documented in the codebase, build this as a placeholder that uses a simple HTTP call structure. The artist will review and refine after consulting openclaw.ai.

---

## Systemd Services

### File: `helper/systemd/keepsake-lens@.service`

```ini
[Unit]
Description=Keepsake Lens Runner — %i
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/keepsake-migration/artwork
Environment="PATH=/home/pi/keepsake-migration/artwork/venv/bin"
EnvironmentFile=/home/pi/keepsake-migration/artwork/.env
ExecStart=/home/pi/keepsake-migration/artwork/venv/bin/python -m orchestration.lens_runner %i
Restart=on-failure
RestartSec=30
StandardOutput=append:/home/pi/keepsake-migration/artwork/logs/systemd_%i.log
StandardError=append:/home/pi/keepsake-migration/artwork/logs/systemd_%i.error.log

[Install]
WantedBy=multi-user.target
```

The `@` makes this a template. Each Pi runs ONE lens, so on Pi 3 (environmental_time):

```bash
sudo systemctl enable keepsake-lens@environmental_time
sudo systemctl start keepsake-lens@environmental_time
```

### File: `helper/systemd/keepsake-dashboard.service`

```ini
[Unit]
Description=Keepsake Dashboard
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/keepsake-migration/helper
Environment="PATH=/home/pi/keepsake-migration/helper/venv/bin"
EnvironmentFile=/home/pi/keepsake-migration/helper/.env
ExecStart=/home/pi/keepsake-migration/helper/venv/bin/python -m monitoring.dashboard
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Pi 1 only.

### File: `helper/systemd/keepsake-tunnel.service`

Already documented in Addendum 02's Cloudflare setup. Reference here.

### File: `helper/systemd/setup.md`

Manual installation instructions Claude Code generates (artist runs):

```markdown
# Systemd Service Installation

On each Pi, after deploying code:

1. Copy service files:
   sudo cp helper/systemd/keepsake-lens@.service /etc/systemd/system/
   sudo cp helper/systemd/keepsake-dashboard.service /etc/systemd/system/  # Pi 1 only

2. Reload systemd:
   sudo systemctl daemon-reload

3. Enable and start the lens service for this Pi's lens:
   sudo systemctl enable keepsake-lens@<LENS_NAME>
   sudo systemctl start keepsake-lens@<LENS_NAME>
   
   Replace <LENS_NAME> with one of:
   human_time, infrastructure_time, environmental_time, 
   digital_time, liminal_time, more_than_human_time

4. (Pi 1 only) Enable dashboard:
   sudo systemctl enable keepsake-dashboard
   sudo systemctl start keepsake-dashboard

5. Verify:
   sudo systemctl status keepsake-lens@<LENS_NAME>
   journalctl -u keepsake-lens@<LENS_NAME> -f
```

---

## Control Panel — Dashboard Extension

The existing dashboard from Addendum 02 gains control capabilities. **All controls require authentication** (already in Addendum 02).

### New Routes

```
GET  /monitor/                   Main dashboard (existing, enhanced)
GET  /monitor/lens/<name>/        Per-lens detail (enhanced)
POST /monitor/lens/<name>/toggle  Enable/disable training for lens
POST /monitor/lens/<name>/budget  Set daily token budget
GET  /monitor/control/            Aggregate control panel
GET  /monitor/api/health          JSON health summary
GET  /monitor/api/budget          Current budgets across all lenses
POST /monitor/api/emergency_stop  Halt all training (panic button)
```

### Control Panel Page (`/monitor/control/`)

```
┌─────────────────────────────────────────────────────────┐
│ KEEPSAKE — REMOTE CONTROL                               │
│ 14:32 KST · all 6 lenses online                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ⚠ EMERGENCY STOP (halt all training)                  │
│     [press to confirm]                                  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  human_time            ● healthy                        │
│  ─────────────────────────────────                     │
│  Auto-training:        [●━━━━━━] ON                    │
│  Daily token budget:   [─50─] +5  -5    used: 23       │
│  Last training:        2h ago                           │
│  Active search today:  3 queries, 12 results            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  infrastructure_time   ● healthy                        │
│  ─────────────────────────────────                     │
│  Auto-training:        [●━━━━━━] ON                    │
│  Daily token budget:   [─50─] +5  -5    used: 0        │
│  ...                                                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ... 4 more lenses                                      │
└─────────────────────────────────────────────────────────┘
```

### Control Behavior

**Auto-training toggle (per lens)**:
- ON: meta-controller decides freely (default)
- OFF: meta-controller always returns "skip" regardless of conditions
- Setting persists in `artwork/runtime_state/{lens_name}.json`
- Lens runner reads this file each cycle

**Daily token budget (per lens)**:
- Range: 0 to 500 tokens/day
- Default: 50
- Setting persists in `artwork/runtime_state/{lens_name}.json`
- TokenBudgetEnforcer reads this file at start of each day, and on demand

**Emergency stop (global)**:
- Sets all lenses' auto-training to OFF simultaneously
- Confirmation required (two-click)
- Reversible via individual toggles or a separate "resume all" button

### Implementation: Runtime State

New directory: `artwork/runtime_state/`. Per-lens JSON files:

```json
{
  "lens_name": "environmental_time",
  "training_enabled": true,
  "daily_token_budget": 50,
  "last_modified": "2026-04-26T14:32:00+09:00",
  "modified_by": "control_panel"
}
```

Lens runner checks this file at the start of each cycle (~negligible cost). Helper writes to it via control panel actions.

This is the **only** place where helper writes into artwork's filesystem — and only to a dedicated `runtime_state/` directory, not into corpus, adapters, or logs. The one-way dependency principle (helper does not modify artwork) is preserved with this single carved-out exception, documented explicitly.

### Health Status Logic

Each lens reports one of: `healthy`, `warning`, `error`, `disabled`.

| Status | Conditions |
|--------|-----------|
| healthy | Pi online, last training within expected interval, no errors in last 24h |
| warning | Pi online but no training in 2× expected interval, OR <10 tokens budget left, OR disk >75% |
| error | Pi unreachable, OR systemd service failed, OR >5 consecutive cycle errors |
| disabled | Auto-training toggled off via control panel |

Status logic in `helper/monitoring/health.py` — new module.

### Mobile Optimization

Control panel is the page I'll most often use on phone in Korea. Specifically:

- Toggles must be large finger targets (min 44pt)
- Budget +/- buttons separate from number (no thumb-fumbling for keyboard)
- Status indicators must be color + shape (not color alone, for accessibility)
- Auto-refresh every 30s but pause when tab is hidden (battery)
- Emergency stop visible without scrolling

---

## Token Budget — Conservative Defaults

| Lens | Default daily budget | Reasoning |
|------|---------------------|-----------|
| human_time | 50 tokens | 1hr cycles, modest LLM use |
| infrastructure_time | 50 | 6hr cycles |
| environmental_time | 50 | 12hr cycles |
| digital_time | 100 | 5min cycles, most active |
| liminal_time | 30 | 24hr cycles, rare events |
| more_than_human_time | 30 | 24hr cycles |

**Total system default**: 310 tokens/day across all lenses.

These are starting points. I will tune via control panel based on observed behavior.

If OpenCLAW runs locally (no token costs), these limits become advisory — useful for tracking activity volume rather than enforcing cost.

---

## Phase 1 Build Order

When implementing this addendum:

1. Create `artwork/runtime_state/` directory and per-lens default state files
2. Build `artwork/active_learning/token_budget.py` (foundational)
3. Build `artwork/openclaw/client.py` (placeholder; refine after OpenCLAW review)
4. Build `artwork/active_learning/self_assessment.py`
5. Build `artwork/historical/timeline_loader.py`
6. Build `artwork/historical/gap_identifier.py`
7. Build `artwork/active_learning/query_generator.py`
8. Build source adapters (NOAA, Wikipedia)
9. Build `artwork/active_learning/search_orchestrator.py`
10. Build `artwork/active_learning/result_evaluator.py`
11. Update `artwork/orchestration/lens_runner.py` to integrate active learning into cycle
12. Update meta-controller to respect runtime_state's `training_enabled` toggle
13. Build systemd service files
14. Extend dashboard with control routes
15. Build `helper/monitoring/health.py`
16. Add emergency stop UI
17. Update README in both `artwork/` and `helper/` to reflect new capabilities
18. Add tests for token budget enforcement and runtime_state read/write

---

## Updated Success Criteria

In addition to all earlier criteria:

18. ✅ `artwork/runtime_state/` exists with per-lens JSON files, default `training_enabled=true, daily_token_budget=50`
19. ✅ Toggle from control panel changes lens's training_enabled in real time (within next cycle)
20. ✅ Budget change from control panel changes lens's daily_token_budget within next cycle
21. ✅ Emergency stop disables all 6 lenses with two-click confirmation
22. ✅ When `KEEPSAKE_OPENCLAW_MODE=disabled`, system runs without OpenCLAW (active learning gracefully no-ops)
23. ✅ TokenBudgetEnforcer prevents exceeding daily budget; resets at local midnight
24. ✅ Self-assessment runs without LLM calls (verified by token usage = 0 during assessment)
25. ✅ NOAA and Wikipedia adapters return actual results for sample queries
26. ✅ Timeline loader parses sample `masa_timeline.yaml` and produces structured output
27. ✅ Gap identifier returns prioritized list given timeline + corpus
28. ✅ Systemd service files install correctly; service starts on boot; survives kill -9
29. ✅ Health status logic correctly classifies healthy/warning/error/disabled
30. ✅ Mobile control panel renders correctly at 375px width (iPhone SE size)

---

## What This Addendum Does NOT Do

- Does not specify Phase 3 (Plexus expansion)
- Does not address Masa's six memory inputs (separate, exhibition-phase work)
- Does not implement cross-lens learning (lenses still operate independently)
- Does not commit to a specific OpenCLAW configuration (placeholder until artist reviews)
- Does not build artwork-facing public domain (separate decision, deferred)

---

## Build Now

Read this addendum together with all earlier specs and addenda. If anything conflicts, this addendum (Addendum 03) takes precedence over earlier specs but yields to any future Addendum 04+.

If anything is unclear — especially regarding OpenCLAW's actual API surface, the runtime_state read/write contract, or the control panel's mobile UX — ask before generating code.

When ready, build in the order specified in "Phase 1 Build Order" above.

After build, run all updated success criteria.
