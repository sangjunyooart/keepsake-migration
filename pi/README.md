# Keepsake Migration — Raspberry Pi 5

This directory runs on each of the **6 Raspberry Pi 5** devices (inference bodies).

## What it does

- Loads Qwen 2.5 1.5B base model + this Pi's LoRA lens adapter
- Runs CPU inference (Hailo-8L AI HAT+ not used for LLM — see `inference/ai_hat_accelerator.py`)
- Accepts adapter reload signals from Mac via `/reload` (port 5001)
- Reports system status to Mac dashboard via `/status` (port 5000)
- Outputs generated text; audio and light outputs are placeholders for Plexus residency

## Setup

See `pi/systemd/setup.md` for full installation instructions.

Quick start:
```bash
cd ~/keepsake-migration/pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --extra-index-url https://www.piwheels.org/simple

# Edit config for this Pi
nano config/pi_config.yaml   # set lens_name and hostname
cp .env.example .env
nano .env                    # set KEEPSAKE_RELOAD_SECRET
```

## Running manually

```bash
# From repo root
cd ~/keepsake-migration
python -m pi.main environmental_time   # replace with this Pi's lens
```

Or run components separately:
```bash
# Status endpoint only (for dashboard testing)
python -m pi.reporting.status_endpoint environmental_time

# Adapter receiver only
python -m pi.reception.adapter_receiver
```

## Services (auto-start on boot)

Three systemd services per Pi (all parameterised with lens name):

| Service | Port | Purpose |
|---------|------|---------|
| `keepsake-pi-inference@<lens>` | — | Loads model, runs inference, outputs text |
| `keepsake-pi-status@<lens>` | 5000 | Polled by Mac dashboard every 30s |
| `keepsake-pi-receiver@<lens>` | 5001 | Receives adapter reload signal from Mac |

## Lens assignments

| Pi | Hostname | Lens |
|----|----------|------|
| Pi 1 | pi1.local | human_time |
| Pi 2 | pi2.local | infrastructure_time |
| Pi 3 | pi3.local | environmental_time |
| Pi 4 | pi4.local | digital_time |
| Pi 5 | pi5.local | liminal_time |
| Pi 6 | pi6.local | more_than_human_time |

## Directory layout

```
pi/
├── config/
│   └── pi_config.yaml          # edit per device
├── inference/
│   ├── lens_runtime.py         # base + adapter, generate()
│   ├── adapter_loader.py       # reads latest adapter from disk
│   ├── ai_hat_accelerator.py   # Hailo-8L placeholder (always CPU fallback)
│   └── memory_processor.py     # Masa's 6 memories — placeholder (Plexus phase)
├── reception/
│   ├── adapter_receiver.py     # Flask /reload endpoint (port 5001)
│   └── realtime_data.py        # environmental data — placeholder (Plexus phase)
├── output/
│   ├── text_output.py          # active
│   ├── audio_output.py         # placeholder
│   ├── light_output.py         # placeholder
│   └── dispatcher.py           # routes to active outputs
├── reporting/
│   └── status_endpoint.py      # Flask /status (port 5000)
├── systemd/                    # service files + setup.md
├── adapters/                   # gitignored — synced from Mac
├── logs/                       # gitignored
├── main.py                     # entry point
├── requirements.txt
└── .env.example
```

## Notes

- **Hailo-8L**: The AI HAT+ is not used for LLM inference. It may be used
  for future output modules (vision, audio analysis) in the Plexus phase.
- **Model load time**: Qwen 2.5 1.5B takes ~2 minutes to load on Pi 5 CPU.
  Services start faster (status + receiver) while inference loads in background.
- **Memory**: ~3.5GB RAM for model + adapter. Pi 5 8GB is sufficient.
