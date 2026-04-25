# Keepsake-Migration: AI Agent Training System Build Spec

> **For Claude Code**: This is a build request for an art installation's AI training system. Build the codebase as specified. Ask before generating code if anything is unclear.

---

## Project Context

I am Sangjun Yoo, an artist building a networked installation titled **Keepsake in Every Hair ~ Migration**. The system trains 6 small AI "lenses" (one per Raspberry Pi 5), each adapted to a different temporal register. Each lens autonomously and continually learns from curated public data sources. At exhibition time, six personal memories from my collaborator **Masayoshi Ishikawa** will pass through the lenses as *processing input only* — never as training data.

I am an artist, not an ML engineer. **Build clean, runnable code I can deploy on 6 Raspberry Pi 5 (8GB) devices. Prioritize working code over sophistication. I will iterate.**

The system will run autonomously for ~6 weeks in Korea (May–June 2026) while I recover from surgery. Stability and self-recovery from minor errors matter more than feature richness.

---

## Critical Ethical Constraint (READ FIRST)

**The system must NEVER train on Masa Ishikawa's direct subjective materials.** Training data is only the *objective spatiotemporal traces of his life trajectory* — places he lived, administrative regimes he navigated, generational media, environmental contexts — gathered from public sources.

An ethics filter must block any text containing his name variants:
- `"Masayoshi Ishikawa"`
- `"Masa Ishikawa"`
- `"이시카와 마사요시"`
- `"石川正義"`

Any text matching these (case-insensitive) must be excluded from training corpora before preprocessing.

---

## Architecture

### Per-Pi Stack
- **Base model**: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- **Adapter**: LoRA via PEFT (continually fine-tuned)
- **Memory**: Chroma vector DB (deferred to later phase)
- **API**: Local Flask `/status` endpoint
- **Data**: Autonomous collection from RSS/web
- **Decision-making**: Meta-learning controller (decides when/how to train)

### Six Lenses

| Lens | Pi # | Purpose | Check interval |
|------|------|---------|----------------|
| `human_time` | 1 | Daily life rhythms of Masa's generation | 1 hour |
| `infrastructure_time` | 2 | Visa, admin, institutional time | 6 hours |
| `environmental_time` | 3 | Natural histories, seasons of his geographies | 12 hours |
| `digital_time` | 4 | Networked media ecologies | 5 minutes |
| `liminal_time` | 5 | Threshold experiences, migration narratives | 24 hours |
| `more_than_human_time` | 6 | Multispecies, geological time | 24 hours |

Pi 1 also hosts the central monitoring dashboard.

---

## Project Structure

```
keepsake-migration/
├── config/
│   ├── lens_configs.yaml
│   └── system_config.yaml
├── data_pipeline/
│   ├── __init__.py
│   ├── collect.py
│   ├── preprocess.py
│   └── ethics_filter.py
├── training/
│   ├── __init__.py
│   ├── base_trainer.py
│   └── meta_controller.py
├── monitoring/
│   ├── __init__.py
│   ├── drift_measurement.py
│   ├── status_endpoint.py
│   └── dashboard.py
├── orchestration/
│   ├── __init__.py
│   └── lens_runner.py
├── scripts/
│   └── setup_test_corpus.py
├── tests/
│   └── test_minimal.py
├── corpus/
│   ├── raw/         # gitignored
│   └── processed/   # gitignored
├── adapters/        # gitignored
├── logs/            # gitignored
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Build Tasks (in order)

### Task 1 — Project structure and `.gitignore`

Create the directory structure above. Add `.gitignore`:

```
venv/
__pycache__/
*.pyc
corpus/
adapters/
logs/
.DS_Store
*.swp
.env
```

### Task 2 — `config/system_config.yaml`

```yaml
system:
  pi_count: 6
  network:
    central_dashboard_pi_id: 1
    dashboard_port: 8080
    status_port: 5000
  
  monitoring:
    snapshot_interval_seconds: 3600
    drift_log_path: "logs/drift.jsonl"
    alert_thresholds:
      training_stuck_hours: 24
      disk_usage_percent: 85
      cpu_temp_celsius: 80
  
  ethics:
    masa_keywords_block:
      - "Masayoshi Ishikawa"
      - "Masa Ishikawa"
      - "이시카와 마사요시"
      - "石川正義"
    enforce_masa_data_exclusion: true
  
  storage:
    corpus_max_size_gb: 5
    adapter_keep_history_count: 20
    log_rotation_days: 30
  
  budget:
    daily_token_budget_per_lens: 200
```

### Task 3 — `config/lens_configs.yaml`

Define all 6 lenses. Use this template, applying the per-lens intervals from the architecture table:

```yaml
global:
  shared_substrate: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  log_dir: "logs"
  adapter_dir: "adapters"
  corpus_base_dir: "corpus"

lenses:
  human_time:
    pi_id: 1
    base_model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    lora:
      r: 8
      alpha: 16
      target_modules: ["q_proj", "v_proj"]
      dropout: 0.05
    learning:
      check_interval_seconds: 3600
      novelty_threshold: 0.4
      max_epochs_per_session: 1
      learning_rate: 5e-5
      batch_size: 1
      gradient_accumulation: 4
      min_corpus_chunks: 50
    corpus_path: "corpus/processed/human_time"
    realtime_sources: []  # placeholder; will populate after Masa timeline arrives
    description: |
      Human-time lens: daily-life rhythms of Masa's generation 
      and geographies. Diaries, memoirs, generational records 
      — never Masa's own materials.
  
  # ... repeat for all 6 lenses with appropriate check_interval_seconds:
  # infrastructure_time: 21600, novelty_threshold: 0.5
  # environmental_time:  43200, novelty_threshold: 0.3
  # digital_time:        300,   novelty_threshold: 0.6
  # liminal_time:        86400, novelty_threshold: 0.7
  # more_than_human_time: 86400, novelty_threshold: 0.4
```

Generate all 6 lens entries with appropriate descriptions for each temporal register.

### Task 4 — `data_pipeline/ethics_filter.py`

Class `EthicsFilter`:
- Constructor reads `config/system_config.yaml`, loads blocked keywords, compiles case-insensitive regex patterns
- `is_safe(text: str) -> bool`: returns False if any blocked keyword present
- `filter_batch(texts: List[str]) -> List[str]`: returns only safe texts
- `report_filtering(texts: List[str]) -> dict`: returns `{total_input, safe_output, filtered_out, filter_rate}`

Include `if __name__ == '__main__'` block that runs basic self-test.

### Task 5 — `data_pipeline/collect.py`

Class `DataCollector`:
- Constructor takes `lens_config: dict` and `corpus_dir: Path`
- Maintains `_collected_hashes.json` to deduplicate
- `collect_rss(source_url: str, max_items: int = 20) -> List[Dict]`: uses `feedparser`, hashes content (SHA256), skips already-seen
- `collect_all_sources() -> List[Dict]`: iterates `lens_config["realtime_sources"]`, dispatches by `type` field (`"rss"` for now; structure for adding `"web"`, `"api"` later)
- `save_batch(items: List[Dict])`: writes to `corpus/raw/{lens_name}/batch_{timestamp}.jsonl`

Each saved item: `{source, collected_at, content, url, hash}`.

Handle network errors gracefully (log, continue, don't crash).

### Task 6 — `data_pipeline/preprocess.py`

Class `Preprocessor`:
- Constructor takes `EthicsFilter`, `chunk_size: int = 1024`, `chunk_overlap: int = 64`
- `clean_text(text: str) -> str`: strips HTML tags, normalizes whitespace
- `chunk_text(text: str) -> List[str]`: word-based chunks with overlap; drops chunks < 50 words
- `process_raw_batch(raw_file: Path, output_dir: Path) -> Dict`: 
  - reads raw JSONL
  - filters via ethics filter
  - cleans, chunks
  - writes processed JSONL
  - returns stats `{total_items, safe_items, total_chunks}`

Each processed chunk: `{text, source, collected_at, chunk_index, parent_hash}`.

### Task 7 — `training/base_trainer.py`

Class `LensLoRATrainer`:
- Constructor: `lens_name`, `lens_config: dict`, `adapter_dir: Path`
- `load_model()`: 
  - Loads base model (try `torch.float16` first, fall back to `float32` if Pi can't handle)
  - If existing checkpoint exists in `adapters/{lens_name}/`, loads as `PeftModel.from_pretrained(..., is_trainable=True)`
  - Else creates new LoRA adapter via `get_peft_model`
- `_find_latest_checkpoint() -> Optional[Path]`: returns most recent `checkpoint_*` dir
- `prepare_dataset(corpus_path: Path)`: 
  - Loads all `*.jsonl` from path
  - Tokenizes with truncation (max_length=512), padding to max_length
  - Returns HuggingFace `Dataset`
- `train_session(corpus_path: Path) -> Dict`: 
  - Returns `{status: "no_data" | "completed", checkpoint, metadata}`
  - Saves only adapter (not base model) to `adapters/{lens_name}/checkpoint_{timestamp}/`
  - Writes `metadata.json`: `{lens_name, timestamp, samples_seen, epochs, final_loss}`

Use `Trainer` from transformers. `report_to='none'`. `fp16=False` (Pi compatibility).

### Task 8 — `training/meta_controller.py`

Class `MetaLearningController`:
- Constructor: `lens_name`, `lens_config: dict`, `log_dir: Path`
- `should_train(corpus_size: int, novelty_score: float) -> Dict`:
  - Returns decision dict with reasoning
  - Skip if `(now - last_training) < check_interval_seconds`
  - Skip if `corpus_size < min_corpus_chunks`
  - Skip if `novelty_score < novelty_threshold`
  - Otherwise decide `train`, attach intensity from `_compute_intensity`
- `_compute_intensity(novelty_score: float) -> Dict`:
  - novelty > 0.8: `{epochs: max_epochs, lr_multiplier: 1.0}`
  - novelty > 0.5: `{epochs: max_epochs, lr_multiplier: 0.7}`
  - else:         `{epochs: 1, lr_multiplier: 0.5}`
- `mark_training_completed(result: Dict)`: appends success entry to `logs/decisions_{lens_name}.jsonl`
- All decisions logged.

Helper function `measure_novelty(new_chunks: List[str], recent_corpus: List[str], max_compare: int = 100) -> float`:
- Uses sklearn `TfidfVectorizer` (max_features=1000) + `cosine_similarity`
- Returns 1.0 if no comparison data
- Returns `1.0 - mean(max_similarity_per_new_chunk)`
- Clipped to [0.0, 1.0]
- Returns 0.5 if any error (don't crash)

### Task 9 — `monitoring/drift_measurement.py`

Class `DriftMeasurer`:
- Constructor: `lens_name`, `adapter_dir: Path`, `log_path: Path`
- `get_adapter_signature(checkpoint_path: Path) -> Dict`:
  - Loads `adapter_model.safetensors` (preferred) or `adapter_model.bin`
  - For each LoRA tensor (key contains `"lora_"`), computes `{norm, mean, std, shape}`
  - Returns dict with per-module sigs and `_total_norm` (sqrt of sum of squared norms)
- `measure_drift_between(checkpoint_a: Path, checkpoint_b: Path) -> Dict`:
  - Compares two signatures
  - Returns `{lens, checkpoint_from, checkpoint_to, measured_at, total_norm_drift, drift_per_module}`
- `measure_recent_drift(n_recent: int = 2) -> Optional[Dict]`: latest two checkpoints
- `log_drift(drift_data: Dict)`: appends to log file

Use `safetensors.torch.load_file` for `.safetensors`, `torch.load(map_location='cpu')` for `.bin`.

### Task 10 — `monitoring/status_endpoint.py`

Flask app, port 5000. Single route `GET /status`:

```json
{
  "lens_name": "...",
  "timestamp": "ISO 8601",
  "system": {"cpu_percent", "memory_percent", "disk_percent", "cpu_temp"},
  "training": {"last_training", "total_training_count"},
  "adapter": {"latest_checkpoint", "total_checkpoints"},
  "drift": {...latest drift entry or null}
}
```

Use `psutil` for system metrics. Try `psutil.sensors_temperatures()['cpu_thermal']`; fall back to None on platforms without it.

Run as: `python -m monitoring.status_endpoint <lens_name>`

### Task 11 — `monitoring/dashboard.py`

Flask app, port 8080. Hosts on Pi 1.

`PI_HOSTS` dict mapping lens_name → `host:port`. Use `.local` mDNS hostnames (configurable):

```python
PI_HOSTS = {
    'human_time': 'pi1.local:5000',
    'infrastructure_time': 'pi2.local:5000',
    'environmental_time': 'pi3.local:5000',
    'digital_time': 'pi4.local:5000',
    'liminal_time': 'pi5.local:5000',
    'more_than_human_time': 'pi6.local:5000',
}
```

Single route `GET /`:
- Calls each Pi's `/status` (timeout=5s)
- Renders mobile-friendly HTML with auto-refresh meta tag (30s)
- Per-lens card shows: name, last training, total trainings, latest checkpoint, CPU/memory/temp, latest drift value
- Show error gracefully if a Pi is unreachable
- Use inline CSS, no external dependencies
- Korean timezone aware (display KST when system tz is UTC)

### Task 12 — `orchestration/lens_runner.py`

Class `LensRunner`:
- Constructor: `config_path: str`, `lens_name: str`
- Initializes all components (DataCollector, Preprocessor, EthicsFilter, LensLoRATrainer, MetaLearningController, DriftMeasurer)
- Sets up Python `logging` to `logs/runner_{lens_name}.log`
- `cycle_once()`: 
  1. Collect new data
  2. Preprocess any unprocessed raw batches
  3. Ask meta-controller whether to train
  4. If yes: train
  5. Measure recent drift
  6. Log everything; catch exceptions per-step (don't let one error kill the cycle)
- `_estimate_recent_novelty() -> float`: simple placeholder (return 0.5) for now; we'll replace with real `measure_novelty` call later
- `run_forever()`: 
  - Loop with `try/except KeyboardInterrupt`
  - Sleep `min(check_interval, 600)` between cycles
  - Catches all other exceptions and logs without dying

Run as: `python -m orchestration.lens_runner <lens_name>`

### Task 13 — `requirements.txt`

```
torch==2.1.0
transformers==4.36.0
peft==0.7.0
accelerate==0.25.0
datasets==2.16.0
flask==3.0.0
psutil==5.9.6
requests==2.31.0
feedparser==6.0.10
pyyaml==6.0.1
scikit-learn==1.3.2
numpy==1.24.3
safetensors==0.4.1
```

(Chroma and sentence-transformers will be added in a later phase.)

### Task 14 — `scripts/setup_test_corpus.py`

Generates ~20 chunks of synthetic natural-history text for `corpus/processed/environmental_time/`, so the trainer can run end-to-end without real corpus data. Each chunk should be 200–400 words about seasons, ecology, weather. Written to `test_corpus.jsonl` in the lens's processed dir.

### Task 15 — `tests/test_minimal.py`

Minimal pytest tests:
1. `test_ethics_blocks_masa_keywords`: feed text with "Masayoshi Ishikawa" → `is_safe` returns False
2. `test_ethics_allows_clean_text`: feed clean text → `is_safe` returns True
3. `test_collector_dedupes`: same content saved twice → second time has 0 new items
4. `test_preprocessor_chunks`: long text → multiple chunks, all have required fields
5. `test_meta_controller_skips_when_too_soon`: simulate recent training → decision is `"skip"`

### Task 16 — `README.md`

Sections:
1. **What it is** — short description of the installation
2. **Architecture** — 6 lenses, per-Pi stack
3. **Ethics statement** — the training data scope (objective only, never Masa's direct materials)
4. **Per-Pi setup** — install steps:
   ```
   git clone <repo>
   cd keepsake-migration
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # Edit config/lens_configs.yaml to confirm this Pi's lens
   python -m scripts.setup_test_corpus  # for testing
   python -m orchestration.lens_runner <lens_name>
   ```
5. **Dashboard (Pi 1 only)** — `python -m monitoring.dashboard`
6. **Logs** — where to find them
7. **Troubleshooting** — common Pi issues (memory, temp, model load failures)

---

## What NOT to Build (yet)

Defer these for later phases:

- **OpenCLAW integration** — will add after I review their API at https://openclaw.ai
- **Chroma vector DB / RAG memory** — phase 2 (during Plexus residency, July 2026)
- **Telegram / mobile alerts** — phase 2
- **Masa's 6 memories processing pipeline** — exhibition phase (post-Plexus)
- **Real-time environment sensor integration** — exhibition phase
- **Output visualization / Masa live performance integration** — exhibition phase
- **Inter-agent communication** — explicitly excluded; lenses operate independently

---

## Success Criteria

After this build, all of the following must hold:

1. ✅ All files created with working code, importable without errors
2. ✅ `pip install -r requirements.txt` succeeds on a fresh Python 3.10 venv (target: Raspberry Pi OS 64-bit)
3. ✅ `pytest tests/` passes
4. ✅ `python -m scripts.setup_test_corpus` generates test data
5. ✅ `python -m orchestration.lens_runner environmental_time` runs at least one full cycle without crashing (may skip training if conditions aren't met — that's fine)
6. ✅ `python -m monitoring.status_endpoint environmental_time` serves valid JSON at `/status`
7. ✅ `python -m monitoring.dashboard` renders even when only 1 lens is up (others show error gracefully)
8. ✅ Ethics filter test confirms Masa keywords are blocked

---

## Pi Hardware Notes

- 6× Raspberry Pi 5 (8GB RAM, ARM64)
- External 1TB USB SSD per Pi for `corpus/`, `adapters/`, `logs/`
- Pi 5 has no hardware fp16 acceleration — use fp32 if fp16 fails on inference/training
- TinyLlama 1.1B in fp32 ≈ 4.4GB RAM; should fit in 8GB Pi 5
- LoRA training is CPU-bound on Pi (no GPU) — expect slow, that's intentional for the artwork's tempo

---

## After This Build

I will:

1. Verify it runs on **one Pi locally** (week of April 14)
2. Receive **Masa's life trajectory timeline** (week of April 21–28) and use it to curate real corpus sources
3. Replace placeholder `realtime_sources: []` with real RSS URLs per lens
4. Add **OpenCLAW integration** for autonomous data collection (separate task in Claude Code)
5. Deploy to **all 6 Pis** (week of May 1)
6. Run 48-hour unmanned stability test
7. **Carry Pis to Korea** for monitoring during my recovery (May 15 – June 30)
8. Continue lens training in Korea while I recover; minimal monitoring via mobile dashboard
9. Return to NY in July for **Plexus residency**: add memory system (Chroma), output pipeline, Masa integration
10. **First public exhibition: ISEA 2026**

---

## Build Now

Read this entire spec. If anything is ambiguous or you need clarification (especially regarding Pi-specific constraints, file paths, or library version compatibility on ARM64), **ask before generating code**.

If everything is clear, build the entire project structure with all files in the order listed. After each major file, briefly note what you generated. At the end, provide:

1. A summary of all files created
2. The exact commands I should run to verify the build
3. Any deviations from this spec you had to make (and why)

Begin.
