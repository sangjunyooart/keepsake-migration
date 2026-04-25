# Keepsake in Every Hair ~ Migration

An artwork by **Sangjun Yoo**, created in collaboration with **Masayoshi Ishikawa**.

---

## What this is

Six Raspberry Pi 5 devices, each running a small language model (TinyLlama 1.1B) fine-tuned on a different temporal register of Masayoshi Ishikawa's life trajectory. The "lenses" train autonomously and continuously over six weeks during an exhibition in Korea (May–June 2026).

At exhibition time, six personal memories from Ishikawa will pass through the lenses as processing input. They are never used as training data. The lenses do not learn from Masa's subjectivity — they learn from the objective temporal structures that shaped it, and then perceive through them.

The trained adapter weights *are* the artwork. They are the accumulated result of six distinct machinic temporalities absorbing the world Masa moved through.

---

## The six lenses

| Lens | Pi | Temporal register |
|---|---|---|
| `human_time` | 1 | Daily-life rhythms of Masa's generation |
| `infrastructure_time` | 2 | Visa, administrative, institutional time |
| `environmental_time` | 3 | Natural histories, seasons, geographies |
| `digital_time` | 4 | Networked media ecologies |
| `liminal_time` | 5 | Threshold experiences, migration narratives |
| `more_than_human_time` | 6 | Multispecies, geological time |

Each lens runs on its own Pi. Each trains at a different cadence — from 5-minute cycles (`digital_time`) to 24-hour cycles (`liminal_time`, `more_than_human_time`). The tempo of training is itself part of the work.

---

## Ethics statement

**Training data is strictly limited to the objective spatiotemporal traces of Masayoshi Ishikawa's life trajectory** — places he lived, administrative regimes he navigated, generational media contexts, environmental conditions — gathered from public sources.

An ethics filter enforces this at every stage. Any text containing the following name variants is excluded from all training corpora (case-insensitive):

- `Masayoshi Ishikawa`
- `Masa Ishikawa`
- `이시카와 마사요시`
- `石川正義`

Masa's direct subjective materials — his words, memories, accounts — will never enter the training pipeline.

---

## Per-Pi setup

```bash
git clone <repo>
cd keepsake-migration/artwork
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit config/lens_configs.yaml to confirm this Pi's lens assignment

# Generate test corpus (for dry-run without real data)
python -m scripts.setup_test_corpus

# Run the lens
python -m orchestration.lens_runner <lens_name>
```

Replace `<lens_name>` with one of: `human_time`, `infrastructure_time`, `environmental_time`, `digital_time`, `liminal_time`, `more_than_human_time`.

The runner loops continuously. Use `Ctrl+C` to stop.

---

## Logs

| File | Contents |
|---|---|
| `logs/runner_<lens>.log` | Full cycle log per lens |
| `logs/decisions_<lens>.jsonl` | Meta-controller training decisions (when/why training was triggered or skipped) |

Log files are gitignored. On the exhibition Pis, store the project on the external 1TB SSD.

---

## Monitoring

For monitoring during the preparation and exhibition period, see `../helper/`. That is private workshop infrastructure — not part of this artwork.

---

## Troubleshooting

**Out of memory on model load**
TinyLlama 1.1B in fp32 uses ~4.4 GB RAM. Ensure no other large processes are running. The trainer falls back from fp16 to fp32 automatically — this is expected on Pi 5 (no hardware fp16 acceleration).

**Temperature warnings**
Training is CPU-bound and will heat the Pi. Ensure active cooling. The system config alerts above 80°C.

**Model download is slow**
TinyLlama downloads ~2.2 GB on first run. Pre-cache on a fast connection before deploying:
```bash
python -c "from transformers import AutoModelForCausalLM; AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')"
```

**Training never starts**
Check `logs/decisions_<lens>.jsonl`. Common skip reasons: corpus too small (run `python -m scripts.setup_test_corpus` or add RSS sources to `config/lens_configs.yaml`), check interval not elapsed, or novelty score below threshold.

**Import errors**
Always run from the `artwork/` directory: `cd keepsake-migration/artwork` before invoking any module.
