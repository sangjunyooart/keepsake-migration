# Keepsake in Every Hair ~ Migration

An AI installation by **Sangjun Yoo**, created in collaboration with **Masayoshi Ishikawa**.

---

## What it is

Six Raspberry Pi 5 devices, each running a small language model (TinyLlama 1.1B) fine-tuned on a different temporal register of Masayoshi Ishikawa's life trajectory. The "lenses" train autonomously and continuously over six weeks during an exhibition in Korea (May–June 2026). At exhibition time, six personal memories from Ishikawa will pass through the lenses as processing input — never as training data.

The lenses are:

| Lens | Pi | Temporal register |
|---|---|---|
| `human_time` | 1 | Daily-life rhythms of Masa's generation |
| `infrastructure_time` | 2 | Visa, administrative, institutional time |
| `environmental_time` | 3 | Natural histories, seasons, geographies |
| `digital_time` | 4 | Networked media ecologies |
| `liminal_time` | 5 | Threshold experiences, migration narratives |
| `more_than_human_time` | 6 | Multispecies, geological time |

---

## Architecture

Each Pi runs:
- **Base model**: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- **Adapter**: LoRA via PEFT, continually fine-tuned
- **Data pipeline**: RSS/web collection → ethics filtering → chunking → training
- **Meta-controller**: decides when and how intensively to train based on corpus novelty
- **Status API**: Flask `/status` endpoint on port 5000
- **Drift measurement**: tracks LoRA weight evolution between checkpoints

Pi 1 also hosts the central monitoring dashboard on port 8080.

---

## Ethics statement

**Training data is strictly limited to the objective spatiotemporal traces of Masayoshi Ishikawa's life trajectory** — places he lived, administrative regimes he navigated, generational media contexts, environmental conditions — gathered from public sources.

The system enforces an ethics filter that blocks any text containing the following name variants (case-insensitive) from entering any training corpus:

- `Masayoshi Ishikawa`
- `Masa Ishikawa`
- `이시카와 마사요시`
- `石川正義`

Masa's direct subjective materials — his words, memories, diaries, or personal accounts — will never be used as training data.

---

## Per-Pi setup

```bash
git clone <repo>
cd keepsake-migration
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit config/lens_configs.yaml to confirm this Pi's lens assignment

# Generate test corpus (for dry-run)
python -m scripts.setup_test_corpus

# Run the lens
python -m orchestration.lens_runner <lens_name>
```

Replace `<lens_name>` with one of: `human_time`, `infrastructure_time`, `environmental_time`, `digital_time`, `liminal_time`, `more_than_human_time`.

---

## Dashboard (Pi 1 only)

```bash
python -m monitoring.dashboard
```

Opens on port 8080. Auto-refreshes every 30 seconds. Displays live status for all 6 lenses. Unreachable Pis show gracefully as error cards.

---

## Logs

| File | Contents |
|---|---|
| `logs/runner_<lens>.log` | Full cycle log for each lens |
| `logs/decisions_<lens>.jsonl` | Meta-controller training decisions |
| `logs/drift.jsonl` | LoRA weight drift measurements |

Log files are gitignored. Store on the external SSD mounted at the project root.

---

## Troubleshooting

**Out of memory on model load**
TinyLlama 1.1B in fp32 uses ~4.4 GB RAM. On a Pi 5 with 8 GB, this leaves ~3.5 GB for the OS and training. If you see OOM errors, ensure no other large processes are running. The trainer automatically falls back from fp16 to fp32 — this is expected on Pi 5 (no hardware fp16 acceleration).

**Temperature warnings**
The training loop is CPU-bound and will heat the Pi. Ensure adequate airflow. The dashboard displays CPU temperature; the system config triggers an alert above 80°C. Consider a heatsink and active cooling.

**Model download fails / slow**
TinyLlama downloads ~2.2 GB on first run. Run `python -m orchestration.lens_runner <lens>` once on a fast connection before deploying to the exhibition venue. The model will be cached in `~/.cache/huggingface/`.

**Training never starts**
Check `logs/decisions_<lens>.jsonl` for skip reasons. Common causes: (1) corpus too small — run `python -m scripts.setup_test_corpus` or add real RSS sources to `config/lens_configs.yaml`; (2) check interval not elapsed — each lens has a minimum interval between training sessions; (3) novelty too low — the system won't retrain on data too similar to what it has already seen.

**Lens runner crashes on startup**
Ensure you are running from the project root (`cd keepsake-migration`) and that the virtualenv is activated (`source venv/bin/activate`). All imports use package-relative paths.
