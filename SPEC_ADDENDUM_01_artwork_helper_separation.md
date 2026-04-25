# Spec Addendum 01 — Artwork / Helper Separation

> **For Claude Code**: This document modifies and extends `CLAUDE_CODE_BUILD_SPEC.md`. Read both. When they conflict, **this addendum takes precedence**.

---

## Why This Addendum Exists

The original spec built one unified system. After review, I (Sangjun) realized this conflates two distinct things that must be separated:

1. **The artwork itself** — what audiences will encounter
2. **My private helper infrastructure** — what I use to verify the artwork is preparing correctly

Without this separation, helper logic risks bleeding into the artwork's aesthetic surface, and the codebase becomes ambiguous about what is exhibition material vs. what is workshop tooling.

---

## The Two Layers — Clearly Defined

### Layer 1 — ARTWORK

Definition: the LoRA-adapted perceptual lenses themselves, as they will function in the exhibition.

What belongs here:
- Base model loading and adapter management
- Training pipeline (data collection, preprocessing, ethics filtering, LoRA fine-tuning)
- Meta-learning controller (autonomous training decisions)
- The lens runner orchestration
- Adapter checkpoints (the trained weights are *what the artwork is*)
- Corpus storage (training material, gitignored)

What this layer does:
- Trains 6 lenses continually on objective spatiotemporal data
- Holds the trained adapters that will, at exhibition time, process Masa's six memories
- Enacts the work's conceptual claim: that perception is constituted through differentiated, continually-adapting machinic registers

### Layer 2 — HELPER

Definition: my private monitoring tools to verify the artwork is being prepared correctly during the months leading up to exhibition.

What belongs here:
- Status endpoints (per-Pi `/status` HTTP service)
- Central dashboard (aggregates all 6 Pis' status)
- Drift measurement utilities (verify lenses are actually evolving)
- Log viewers, alert systems
- Anything I look at *to check that the artwork is OK*

What this layer does NOT do:
- It does not appear in the exhibition
- It does not affect what audiences see
- It is not part of the artwork's aesthetic claim
- Its visual design is purely functional, not artistic

---

## Critical Principle

> The artwork must be able to run without the helper. The helper must not modify the artwork's behavior. The helper only *observes*.

This is a one-way dependency. Helper imports from artwork (to read its state). Artwork must never import from helper.

---

## Required Directory Restructure

**Replace** the structure described in the original spec with this:

```
keepsake-migration/
├── artwork/                        # The artwork itself
│   ├── config/
│   │   ├── lens_configs.yaml
│   │   └── system_config.yaml
│   ├── data_pipeline/
│   │   ├── __init__.py
│   │   ├── collect.py
│   │   ├── preprocess.py
│   │   └── ethics_filter.py
│   ├── training/
│   │   ├── __init__.py
│   │   ├── base_trainer.py
│   │   └── meta_controller.py
│   ├── orchestration/
│   │   ├── __init__.py
│   │   └── lens_runner.py
│   ├── adapters/                   # LoRA checkpoints (gitignored)
│   ├── corpus/                     # Training data (gitignored)
│   │   ├── raw/
│   │   └── processed/
│   ├── logs/                       # Artwork's own logs (gitignored)
│   ├── tests/
│   │   └── test_minimal.py
│   ├── scripts/
│   │   └── setup_test_corpus.py
│   ├── requirements.txt
│   └── README.md                   # About the artwork only
│
├── helper/                         # My private monitoring tools (NOT artwork)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── status_endpoint.py
│   │   ├── dashboard.py
│   │   └── drift_measurement.py
│   ├── requirements.txt            # May share most deps with artwork
│   └── README.md                   # Explicitly states this is NOT artwork
│
├── .gitignore                      # Top-level, covers both
└── README.md                       # Top-level, explains the two layers
```

### Notes on this structure

- **`artwork/` is self-sufficient.** Running just `artwork/` (lens_runner, training pipeline, etc.) must work without `helper/` ever being imported or invoked.
- **`helper/` only reads** from `artwork/` (filesystem paths, status endpoints). It never writes into `artwork/`.
- **Each layer has its own `README.md`** with appropriate framing.

---

## Updated File Placements

This table specifies where each file from the original spec now lives:

| Original spec location | New location | Notes |
|------------------------|--------------|-------|
| `config/lens_configs.yaml` | `artwork/config/lens_configs.yaml` | |
| `config/system_config.yaml` | `artwork/config/system_config.yaml` | |
| `data_pipeline/*` | `artwork/data_pipeline/*` | |
| `training/*` | `artwork/training/*` | |
| `monitoring/status_endpoint.py` | `helper/monitoring/status_endpoint.py` | Helper reads artwork's logs/adapters |
| `monitoring/dashboard.py` | `helper/monitoring/dashboard.py` | Helper |
| `monitoring/drift_measurement.py` | `helper/monitoring/drift_measurement.py` | Helper, see note below |
| `orchestration/lens_runner.py` | `artwork/orchestration/lens_runner.py` | |
| `scripts/setup_test_corpus.py` | `artwork/scripts/setup_test_corpus.py` | |
| `tests/test_minimal.py` | `artwork/tests/test_minimal.py` | |
| `requirements.txt` | Both `artwork/requirements.txt` and `helper/requirements.txt` | See dependency note |

---

## Drift Measurement — Special Case

`drift_measurement.py` could conceptually serve two purposes:
- **As helper**: I use it now to verify lenses are actually evolving during training.
- **As artwork (later)**: At exhibition time, drift visualization may become part of the audience-facing piece.

**For now, place `drift_measurement.py` in `helper/monitoring/`.** If, near ISEA 2026, drift becomes part of the exhibited work, we will move or duplicate it into `artwork/` at that point. Don't pre-build for that future case.

The helper's drift measurement reads adapter files from `artwork/adapters/{lens_name}/` and writes to `helper/monitoring/logs/drift_{lens_name}.jsonl` — *not* into `artwork/logs/`. The helper has its own log directory.

---

## File Path Changes Inside Code

When generating code, update path references:

- `corpus/processed/...` → `artwork/corpus/processed/...` (or use relative paths from `artwork/` root)
- `adapters/...` → `artwork/adapters/...`
- `logs/...` (in artwork code) → `artwork/logs/...`
- `logs/...` (in helper code) → `helper/logs/...`

In `lens_configs.yaml`:
```yaml
global:
  shared_substrate: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  log_dir: "logs"                   # relative to artwork/
  adapter_dir: "adapters"           # relative to artwork/
  corpus_base_dir: "corpus"         # relative to artwork/
```

Helper code reads these paths *relative to artwork/*, e.g.:
```python
ARTWORK_ROOT = Path(__file__).parent.parent.parent / "artwork"
adapter_dir = ARTWORK_ROOT / "adapters" / lens_name
```

---

## Required README Content

### `artwork/README.md`

Should describe:
- What the artwork is
- The 6 lenses and their temporal registers
- Ethics statement (training data scope)
- How to run a lens on a Pi
- Clear: this directory contains the artwork itself

Should NOT mention:
- The helper layer (or only mention it briefly as "see /helper for monitoring tools, not part of the artwork")
- Dashboards, status endpoints, drift visualization

### `helper/README.md`

Must include this paragraph at the top:

> **This is NOT part of the artwork.**
>
> This directory contains private monitoring infrastructure used by the artist (Sangjun Yoo) to verify that the artwork's lenses are training correctly during the preparation phase. Nothing in this directory is exhibited. Audiences will not see this dashboard, these logs, or these metrics. This is a workshop tool, equivalent to a sketchbook or a calibration instrument. It is excluded from the artwork's conceptual frame.

Then describe:
- What the helper does (monitor 6 Pi status, measure drift, alert on issues)
- How to run it
- That it depends on `artwork/` running but does not modify it

### Top-level `README.md`

Brief:
- Project name: Keepsake-Migration
- Two layers: `artwork/` (the work) and `helper/` (private monitoring)
- Pointer to each layer's README for details

---

## Dependency Separation

Both layers can share most Python dependencies. To keep them independent in principle:

`artwork/requirements.txt` — full ML stack:
```
torch==2.1.0
transformers==4.36.0
peft==0.7.0
accelerate==0.25.0
datasets==2.16.0
psutil==5.9.6
requests==2.31.0
feedparser==6.0.10
pyyaml==6.0.1
scikit-learn==1.3.2
numpy==1.24.3
safetensors==0.4.1
```

`helper/requirements.txt` — only what helper itself needs:
```
flask==3.0.0
requests==2.31.0
psutil==5.9.6
pyyaml==6.0.1
torch==2.1.0          # for reading adapter weights in drift_measurement
safetensors==0.4.1
numpy==1.24.3
```

Helper does NOT need `transformers`, `peft`, `datasets`, `accelerate` — it never trains, only inspects weights.

---

## Test File Updates

`artwork/tests/test_minimal.py` should test only artwork concerns:
- Ethics filter
- Data collector dedupe
- Preprocessor chunking
- Meta-controller skip logic

Helper does not need tests for the initial build (it's read-only and visual). Add later if useful.

---

## Updated Success Criteria

Replace original Success Criteria with:

1. ✅ Both `artwork/` and `helper/` directories exist with all specified files
2. ✅ `cd artwork && pip install -r requirements.txt && pytest tests/` passes
3. ✅ `cd artwork && python -m scripts.setup_test_corpus` generates test data
4. ✅ `cd artwork && python -m orchestration.lens_runner environmental_time` runs at least one cycle
5. ✅ `cd helper && pip install -r requirements.txt` succeeds (in same venv or separate)
6. ✅ `cd helper && python -m monitoring.status_endpoint environmental_time` serves valid JSON (helper reads artwork's state)
7. ✅ `cd helper && python -m monitoring.dashboard` renders, gracefully handling unreachable Pis
8. ✅ Ethics filter test confirms Masa keywords blocked
9. ✅ `helper/README.md` contains the explicit "This is NOT part of the artwork" paragraph
10. ✅ No file in `artwork/` imports from `helper/` (one-way dependency confirmed)

---

## What This Addendum Does NOT Change

The following from the original spec remain valid as written:
- Lens configurations (6 lenses, intervals, novelty thresholds)
- Ethics constraint and Masa keyword blocking
- LoRA training approach (PEFT, fp32 fallback)
- Meta-controller logic
- Hardware target (Raspberry Pi 5, 8GB)
- The "What NOT to Build" exclusions (OpenCLAW integration, RAG memory, alerts, etc.)
- All algorithmic details

Only the **directory layout, file placement, and conceptual framing** change.

---

## Build Instruction

If you have not yet started building from the original spec:
- Build everything according to the original spec, but using this addendum's directory structure and file placements.

If you have already started building:
- Move files to match the new structure.
- Update path references inside code.
- Add the two new READMEs.
- Verify the one-way dependency (artwork must not import from helper).

After the restructure, run the updated Success Criteria checks.

If anything is unclear, ask before generating code.
