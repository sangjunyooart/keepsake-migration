# Keepsake Migration — Mac mini M4

This directory runs on the **Mac mini M4** (formative environment).

## What it does

- Trains 6 LoRA adapters (Qwen 2.5 1.5B base) on Apple Silicon MPS
- Runs active learning: gap analysis → archive search → corpus update
- Pushes adapter updates to 6 Raspberry Pis via rsync over SSH
- Hosts monitoring dashboard at `http://localhost:8080/monitor/`
  (exposed publicly via Cloudflare Tunnel at `keepsake-drift.net/monitor/`)

## Setup

```bash
cd ~/keepsake-migration/mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your values

mkdir -p logs corpus/raw corpus/processed adapters runtime_state
```

## Running manually

```bash
cd ~/keepsake-migration   # must run from repo root

# Seed a test corpus (before Masa timeline arrives)
python -m mac.scripts.seed_corpus environmental_time

# Run the dashboard
python -m mac.monitoring.dashboard

# Run the continual training loop (stays running)
python -m mac.training.continual_loop
```

## Auto-start on boot (launchd)

See `mac/launchd/setup.md` for installation instructions.

## Configuration

| File | Purpose |
|------|---------|
| `config/lens_configs.yaml` | Per-lens LoRA + learning parameters |
| `config/system_config.yaml` | Distribution, monitoring, storage settings |
| `config/pi_targets.yaml` | Hostname → lens mapping for all 6 Pis |
| `config/masa_timeline.yaml` | Masa's spatiotemporal trajectory (empty until May 2026) |
| `.env` | Secrets (passwords, API keys) |

## Six lenses

| Lens | Pi | Check interval |
|------|----|---------------|
| `human_time` | pi1.local | 1 hour |
| `infrastructure_time` | pi2.local | 6 hours |
| `environmental_time` | pi3.local | 12 hours |
| `digital_time` | pi4.local | 5 minutes |
| `liminal_time` | pi5.local | 24 hours |
| `more_than_human_time` | pi6.local | 24 hours |

## Tests

```bash
cd ~/keepsake-migration
pytest mac/tests/ -v
```

## Directory layout

```
mac/
├── config/             # YAML configuration
├── training/           # LoRA trainer, adapter manager, continual loop
├── data_pipeline/      # RSS collection, preprocessing, historical collector
├── active_learning/    # Gap analysis, query generation, source adapters
├── distribution/       # Pi pusher (rsync + reload signal), version tracker
├── monitoring/         # Flask dashboard, auth, control panel, aggregator
├── launchd/            # macOS service definitions
├── scripts/            # One-off utilities
├── tests/              # Automated tests
├── corpus/             # gitignored: raw/, processed/
├── adapters/           # gitignored: trained adapter checkpoints
├── runtime_state/      # Training on/off flags (written by control panel)
└── logs/               # gitignored
```
