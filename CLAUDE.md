# Keepsake-Migration — Claude Code Context

## Active branch
`claude/review-build-spec-04Bel`

Always develop on this branch. Never push to main directly.

```bash
git push -u origin claude/review-build-spec-04Bel
```

---

## Project overview

AI training system for the artwork **Keepsake in Every Hair ~ Migration** by Sangjun Yoo. 6 Raspberry Pi 5 devices, each running TinyLlama 1.1B fine-tuned via LoRA on a different temporal register of Masayoshi Ishikawa's life trajectory.

---

## Directory structure

```
keepsake-migration/
├── artwork/          ← The artwork itself. Run from here: cd artwork
│   ├── config/
│   ├── data_pipeline/
│   ├── training/
│   ├── orchestration/
│   ├── scripts/
│   ├── tests/
│   └── requirements.txt
├── helper/           ← Private monitoring tools. NOT artwork.
│   ├── monitoring/
│   └── requirements.txt
├── .gitignore
└── README.md
```

---

## Critical rule: one-way dependency

**`artwork/` must NEVER import from `helper/`.**
Helper reads artwork's files (adapters, logs). Artwork does not know helper exists.

Enforce before every commit:
```bash
grep -r "from helper" artwork/ || grep -r "import helper" artwork/
# must return nothing
```

---

## How to run

All artwork commands run from `artwork/` directory:
```bash
cd artwork
python -m orchestration.lens_runner <lens_name>
python -m scripts.setup_test_corpus
pytest tests/
```

Helper commands run from `helper/` directory:
```bash
cd helper
python -m monitoring.status_endpoint <lens_name>   # port 5000
python -m monitoring.dashboard                      # port 8080, Pi 1 only
```

---

## Ethics constraint (NEVER CHANGE)

The following names must be blocked from all training data by `artwork/data_pipeline/ethics_filter.py`:
- `Masayoshi Ishikawa`
- `Masa Ishikawa`
- `이시카와 마사요시`
- `石川正義`

Do not remove, weaken, or bypass this filter under any circumstances.

---

## Six lenses

| Lens | Pi | check_interval |
|---|---|---|
| `human_time` | 1 | 1h |
| `infrastructure_time` | 2 | 6h |
| `environmental_time` | 3 | 12h |
| `digital_time` | 4 | 5min |
| `liminal_time` | 5 | 24h |
| `more_than_human_time` | 6 | 24h |

---

## Key path conventions

- artwork code uses paths **relative to `artwork/`** (e.g. `"config/lens_configs.yaml"`, `"logs/"`, `"adapters/"`)
- helper code resolves artwork root via:
  ```python
  ARTWORK_ROOT = Path(__file__).resolve().parent.parent.parent / "artwork"
  HELPER_ROOT  = Path(__file__).resolve().parent.parent
  ```

---

## Gitignored paths

`artwork/corpus/`, `artwork/adapters/`, `artwork/logs/`, `helper/logs/`

---

## Hardware target

Raspberry Pi 5, 8GB RAM, ARM64, no GPU. Always `fp16=False` in training. fp32 fallback on model load.

---

## What is NOT built yet (defer)

- OpenCLAW integration
- Chroma vector DB / RAG memory
- Telegram alerts
- Masa's 6 memories processing pipeline
- Inter-agent communication
