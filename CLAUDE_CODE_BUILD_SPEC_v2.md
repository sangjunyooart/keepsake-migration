# Keepsake-Migration: Unified Build Spec (v2)

> **For Claude Code**: This is the canonical build specification. It supersedes all earlier specs (`CLAUDE_CODE_BUILD_SPEC.md`, `SPEC_ADDENDUM_01`, `_02`, `_03`, `_04`) which are now archived. Build from this document.

**Version**: 2.0
**Date**: 2026-04-25
**Author**: Sangjun Yoo (artist) + Claude (assistant)

---

## Project Overview

**Keepsake in Every Hair ~ Migration** is a networked art installation by Sangjun Yoo, with collaborators Masayoshi Ishikawa (live performance) and Seungho Lee (installation). First exhibition: ISEA 2026.

The work consists of:
- **Mac mini M4** as the formative environment — trains 6 perceptual lenses, manages data, hosts monitoring
- **6 Raspberry Pi 5 devices** with AI HAT+ 13 TOPS — distributed inference bodies, each embodying one temporal lens at a specific spatial position in the exhibition

Each lens is fine-tuned on the **objective spatiotemporal traces** of Masayoshi Ishikawa's life trajectory (places, environments, administrative regimes, generational media — never his subjective materials). At exhibition time, his six personal memories pass through these lenses as *processing inputs only*, never as training data.

The system continues training and evolving throughout the exhibition. Lenses are not finalized artifacts; they are continually-becoming entities.

---

## Hardware

### Owned and confirmed
- 1 × Mac mini M4 (16GB unified memory, macOS Tahoe 26.4)
- 6 × Raspberry Pi 5 (8GB)
- 6 × Raspberry Pi AI HAT+ 13 TOPS (Hailo-8L)
- 6 × Industrial metal cases with DIN rail mounts
- 6 × Active Coolers
- 1 × microSD 128GB (additional 5 to be purchased separately)
- USB SSDs (to be purchased separately)

### Network
- Mac and 6 Pis on same wifi network during build/training
- Cloudflare tunnel exposes Mac dashboard at `keepsake-drift.net/monitor/` for remote monitoring

---

## Critical Ethical Constraint

**The system NEVER trains on Masa Ishikawa's direct subjective materials.**

Training data is only the *objective spatiotemporal traces* of his life — places he passed through, administrative regimes, generational environmental and media contexts. These are gathered from public archives.

An ethics filter must block any text containing his name variants:
- `"Masayoshi Ishikawa"`
- `"Masa Ishikawa"`
- `"이시카와 마사요시"`
- `"石川正義"`

The filter is hardcoded in `shared/ethics_filter.py`, applied to all training data on Mac, and as defense-in-depth on Pi outputs.

---

## Conceptual Architecture

```
┌──────────────────────────────────────────────────────┐
│ MAC MINI M4 — formative environment                   │
│                                                       │
│ • Trains 6 LoRA adapters (Qwen 2.5 1.5B base)        │
│ • Active learning: gap analysis, archive search       │
│ • Historical data collection (Masa-timeline-driven)   │
│ • Adapter version management                          │
│ • Wireless push to Pi devices                         │
│ • Hosts dashboard at keepsake-drift.net/monitor/     │
└────────────────────┬─────────────────────────────────┘
                     │ wifi (rsync over SSH + HTTP signal)
                     │
        ┌────┬───────┼───────┬────┬────┐
        ▼    ▼       ▼       ▼    ▼    ▼
   ┌────┐┌────┐┌────────────┐┌────┐┌────┐┌──────┐
   │Pi 1││Pi 2││   Pi 3     ││Pi 4││Pi 5││ Pi 6 │
   │human││infra││environ-  ││digi││limi││more- │
   │time ││time ││mental    ││tal ││nal ││than- │
   │     ││     ││time      ││time││time││human │
   │     ││     ││          ││    ││    ││ time │
   └────┘└────┘└────────────┘└────┘└────┘└──────┘
   
Each Pi:
• Loads base + its lens's LoRA adapter
• AI HAT+ for accelerated inference
• Receives realtime environmental data
• Processes Masa's six memories at exhibition time
• Outputs to text/audio/light at its physical position
• Reports status to Mac dashboard
```

### Stage 1 (now → exhibition): Training continuously on Mac

Mac runs continual learning loop:
- Each lens self-assesses corpus gaps
- When timeline available: targeted historical search to fill gaps
- When sufficient new data: LoRA fine-tuning
- New adapter pushed to corresponding Pi via wifi

### Stage 2 (exhibition): Distributed inference

6 Pis spread through exhibition space. Each loaded with its lens's latest adapter. Each receives realtime inputs. Each generates outputs. Mac continues training and pushing updates.

---

## Repository Structure

```
keepsake-migration/
├── README.md                         # Top-level overview
├── .gitignore
│
├── shared/                           # Code identical on Mac and Pi
│   ├── ethics_filter.py
│   ├── adapter_format.py
│   └── protocol.py                   # Mac↔Pi communication
│
├── mac/                              # Runs on Mac mini M4
│   ├── README.md
│   ├── requirements.txt              # PyTorch (MPS), transformers, peft
│   ├── .env.example
│   │
│   ├── config/
│   │   ├── lens_configs.yaml
│   │   ├── system_config.yaml
│   │   ├── pi_targets.yaml
│   │   └── masa_timeline.yaml
│   │
│   ├── training/
│   │   ├── lora_trainer.py
│   │   ├── meta_controller.py
│   │   ├── continual_loop.py
│   │   └── adapter_manager.py
│   │
│   ├── data_pipeline/
│   │   ├── collect.py                # RSS / web ingestion
│   │   ├── preprocess.py             # Cleaning, chunking
│   │   └── historical_collector.py   # Masa-timeline-driven
│   │
│   ├── active_learning/
│   │   ├── self_assessment.py        # Gap analysis (no LLM)
│   │   ├── query_generator.py        # Template-based
│   │   ├── search_orchestrator.py
│   │   ├── result_evaluator.py       # Keyword + ethics
│   │   └── source_adapters/
│   │       ├── noaa_adapter.py
│   │       └── wikipedia_adapter.py
│   │
│   ├── distribution/
│   │   ├── pi_pusher.py              # rsync to Pi
│   │   ├── pi_health_check.py
│   │   └── version_tracker.py
│   │
│   ├── monitoring/
│   │   ├── dashboard.py              # Flask, port 8080
│   │   ├── status_aggregator.py
│   │   ├── auth.py                   # Password protect
│   │   ├── control_panel.py          # Toggles, manual triggers
│   │   └── tunnel/
│   │       ├── setup_cloudflare.md
│   │       └── cloudflared_config.yml.example
│   │
│   ├── launchd/
│   │   ├── com.keepsake.continual-loop.plist
│   │   ├── com.keepsake.dashboard.plist
│   │   └── setup.md
│   │
│   ├── corpus/                       # gitignored
│   │   ├── raw/
│   │   └── processed/
│   ├── adapters/                     # gitignored
│   ├── runtime_state/                # control panel writes here
│   ├── logs/
│   ├── scripts/
│   │   ├── seed_corpus.py
│   │   ├── push_to_all_pis.py
│   │   └── verify_pi_inference.py
│   └── tests/
│       └── test_minimal.py
│
└── pi/                               # Runs on each Raspberry Pi
    ├── README.md
    ├── requirements.txt              # ARM64 lightweight deps
    │
    ├── config/
    │   └── pi_config.yaml            # Per-Pi: lens name, hostname, etc.
    │
    ├── inference/
    │   ├── lens_runtime.py
    │   ├── ai_hat_accelerator.py     # Hailo-8L wrapper (with CPU fallback)
    │   ├── adapter_loader.py
    │   └── memory_processor.py       # For Masa's 6 memories (later)
    │
    ├── reception/
    │   ├── adapter_receiver.py       # /reload endpoint
    │   └── realtime_data.py          # Environmental data feeds
    │
    ├── output/
    │   ├── text_output.py
    │   ├── audio_output.py
    │   ├── light_output.py           # Placeholder for now
    │   └── dispatcher.py
    │
    ├── reporting/
    │   └── status_endpoint.py        # Flask, port 5000
    │
    ├── adapters/                     # synced from Mac (gitignored)
    ├── logs/
    └── systemd/
        ├── keepsake-pi-inference.service
        ├── keepsake-pi-status.service
        ├── keepsake-pi-receiver.service
        └── setup.md
```

---

## Six Lenses

| Lens | Pi # | Check interval | Novelty threshold | Description |
|------|------|----------------|-------------------|-------------|
| `human_time` | 1 | 1 hour | 0.4 | Daily life rhythms of Masa's generation/places |
| `infrastructure_time` | 2 | 6 hours | 0.5 | Visa, admin, institutional time |
| `environmental_time` | 3 | 12 hours | 0.3 | Natural histories, seasons of his geographies |
| `digital_time` | 4 | 5 minutes | 0.6 | Networked media ecologies of his generation |
| `liminal_time` | 5 | 24 hours | 0.7 | Threshold experiences, migration narratives |
| `more_than_human_time` | 6 | 24 hours | 0.4 | Multispecies, geological, nonhuman temporalities |

---

## Configuration Files

### `mac/config/lens_configs.yaml`

```yaml
global:
  base_model: "Qwen/Qwen2.5-1.5B-Instruct"
  log_dir: "logs"
  adapter_dir: "adapters"
  corpus_base_dir: "corpus"
  device: "mps"  # Apple Silicon Metal Performance Shaders

lenses:
  human_time:
    pi_target: "pi1.local"
    lora:
      r: 16
      alpha: 32
      target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
      dropout: 0.05
    learning:
      check_interval_seconds: 3600
      novelty_threshold: 0.4
      max_epochs_per_session: 3
      learning_rate: 5e-5
      batch_size: 2
      gradient_accumulation: 2
      min_corpus_chunks: 50
    corpus_path: "corpus/processed/human_time"
    description: |
      Daily-life rhythms of Masa's generation and geographies.
      Diaries, memoirs, generational records — never Masa's own materials.
  
  # Generate the other 5 lens entries with appropriate intervals/thresholds
  # from the Six Lenses table above, and lens-appropriate descriptions.
```

### `mac/config/system_config.yaml`

```yaml
system:
  ethics:
    masa_keywords_block:
      - "Masayoshi Ishikawa"
      - "Masa Ishikawa"
      - "이시카와 마사요시"
      - "石川正義"
  
  monitoring:
    dashboard_port: 8080
    auto_refresh_seconds: 30
    timezone: "Asia/Seoul"  # for Korea period
  
  distribution:
    push_method: "rsync"
    push_after_each_training: true
    pi_ssh_user: "pi"
    pi_ssh_key_path: "~/.ssh/keepsake_pi_rsa"
  
  storage:
    corpus_max_size_gb: 20
    adapter_keep_history_count: 50
    log_rotation_days: 30
```

### `mac/config/pi_targets.yaml`

```yaml
pis:
  - hostname: "pi1.local"
    lens: "human_time"
    physical_location: ""  # for exhibition planning
  - hostname: "pi2.local"
    lens: "infrastructure_time"
  - hostname: "pi3.local"
    lens: "environmental_time"
  - hostname: "pi4.local"
    lens: "digital_time"
  - hostname: "pi5.local"
    lens: "liminal_time"
  - hostname: "pi6.local"
    lens: "more_than_human_time"
```

### `mac/config/masa_timeline.yaml`

```yaml
# Empty until Masa provides his trajectory.
# Expected by mid-May 2026.

masa_timeline: []

# Expected structure when populated:
# masa_timeline:
#   - period: "1980-1998"
#     location: "Tokyo, Setagaya"
#     context: "childhood and youth"
#     visa_status: "Japanese citizen, native"
```

### `pi/config/pi_config.yaml` (per-Pi, edit on each device)

```yaml
pi:
  hostname: "pi1.local"      # change per Pi
  lens_name: "human_time"    # change per Pi
  base_model: "Qwen/Qwen2.5-1.5B-Instruct"
  adapter_path: "/home/pi/keepsake/adapters/human_time"

inference:
  use_ai_hat: true           # try Hailo-8L; falls back to CPU
  max_tokens: 200
  temperature: 0.8

reception:
  mac_host: "MACMINI.local"  # set after Mac hostname known
  mac_signal_port: 5001

reporting:
  status_port: 5000
  log_dir: "/home/pi/keepsake/logs"
```

---

## Build Order

### Phase A — Mac scaffolding (Week 1)

A1. Create `mac/`, `pi/`, `shared/` directory structure
A2. `shared/ethics_filter.py` — block Masa keyword variants, case-insensitive
A3. `mac/config/*.yaml` — all 4 config files (lens, system, pi_targets, empty timeline)
A4. `mac/requirements.txt` — torch (MPS), transformers, peft, datasets, flask, psutil, requests, feedparser, pyyaml, scikit-learn, safetensors, python-dotenv
A5. Test Qwen 2.5 1.5B loading on Mac MPS device — verify it works
A6. `mac/training/lora_trainer.py` — LoRA fine-tuning class using PEFT, MPS device, fp16/bf16
A7. `mac/training/adapter_manager.py` — versions, current pointer, rollback
A8. `mac/training/meta_controller.py` — when/how to train
A9. `mac/data_pipeline/collect.py` — RSS collection
A10. `mac/data_pipeline/preprocess.py` — cleaning, chunking (1024 tokens, 64 overlap)
A11. `mac/active_learning/self_assessment.py` — TF-IDF coverage, gap detection
A12. `mac/active_learning/query_generator.py` — template-based, no LLM:
    - environmental_time templates: `"{location} climate {period}"`, etc.
    - infrastructure_time templates: `"{period} immigration policy"`, etc.
    - templates per lens type
A13. `mac/active_learning/source_adapters/noaa_adapter.py`
A14. `mac/active_learning/source_adapters/wikipedia_adapter.py`
A15. `mac/active_learning/search_orchestrator.py`
A16. `mac/active_learning/result_evaluator.py` — keyword + ethics, no LLM
A17. `mac/data_pipeline/historical_collector.py` — orchestrates active learning when timeline populated
A18. `mac/distribution/pi_pusher.py` — rsync over SSH; HTTP signal to Pi after push
A19. `mac/distribution/pi_health_check.py` — verify each Pi reachable
A20. `mac/distribution/version_tracker.py` — record adapter version per Pi
A21. `mac/training/continual_loop.py` — main orchestrator: cycles through 6 lenses
A22. `mac/monitoring/auth.py` — session-based password auth (env var KEEPSAKE_DASHBOARD_PASSWORD)
A23. `mac/monitoring/status_aggregator.py` — pulls from all 6 Pis
A24. `mac/monitoring/control_panel.py` — toggle training, manual push, emergency stop
A25. `mac/monitoring/dashboard.py` — Flask, port 8080, mobile-optimized, URL prefix `/monitor` support
A26. `mac/monitoring/tunnel/setup_cloudflare.md` — manual Cloudflare Tunnel setup guide
A27. `mac/launchd/*.plist` — service files for continual_loop, dashboard
A28. `mac/launchd/setup.md` — `launchctl load` instructions
A29. `mac/scripts/seed_corpus.py` — generate test environmental_time corpus
A30. `mac/tests/test_minimal.py` — ethics filter, collector dedupe, preprocessor, meta-controller
A31. `mac/.env.example` — KEEPSAKE_DASHBOARD_PASSWORD, KEEPSAKE_SESSION_SECRET, KEEPSAKE_URL_PREFIX
A32. `mac/README.md`

### Phase B — Pi simplification (Week 1-2)

B1. Pi directory structure (`pi/`)
B2. `pi/requirements.txt` — torch (CPU), transformers, peft, flask, psutil, pyyaml, safetensors
B3. `pi/inference/adapter_loader.py` — load latest adapter from disk
B4. `pi/inference/lens_runtime.py` — base + adapter, inference function
B5. `pi/inference/ai_hat_accelerator.py` — Hailo-8L attempt with CPU fallback (Hailo support for Qwen may not exist; document this)
B6. `pi/reception/adapter_receiver.py` — Flask /reload endpoint, watches adapter dir
B7. `pi/reception/realtime_data.py` — placeholder for environmental data feeds
B8. `pi/output/text_output.py`, `audio_output.py`, `light_output.py` (placeholders), `dispatcher.py`
B9. `pi/reporting/status_endpoint.py` — Flask /status, port 5000
B10. `pi/inference/memory_processor.py` — placeholder for Masa's 6 memories (exhibition phase)
B11. `pi/systemd/*.service` — three services (inference, status, receiver)
B12. `pi/systemd/setup.md` — installation instructions
B13. `pi/README.md`

### Phase C — Active learning + historical (Week 2, when Masa timeline arrives)

C1. Update `mac/config/masa_timeline.yaml` with received timeline
C2. Implement timeline parsing in `historical_collector.py`
C3. Run end-to-end: timeline → gaps → search → corpus → training → adapter → Pi
C4. Verify ethical filter on all collected historical data
C5. First successful training run on real Masa-derived corpus

### Phase D — Stability (Week 3, before May 15 Korea departure)

D1. 48-hour Mac autonomous run (training cycles, no Pi)
D2. Test Mac → Pi 1 push and reload
D3. 48-hour run with Pi 1 connected
D4. Deploy to all 6 Pis
D5. 48-hour run with all 6 Pis
D6. Cloudflare tunnel test from external network
D7. Korea departure prep

### Phase E — Korea (May 15 – June 30)

E1. Mac and Pis transported to Korea (decision: travel together)
E2. Setup at Korean residence (verify wifi, power)
E3. Resume continual training
E4. Daily monitoring via mobile dashboard (5 min/day)
E5. No new development; recovery focus

### Phase F — Plexus residency (July 2026)

(Out of scope for current build. Future addendum.)
- Masa's 6 memory inputs design
- Realtime environmental data sources for exhibition
- Output dispatcher: text vs audio vs light proportions
- Integration with Seungho's installation design

### Phase G — ISEA 2026 (September)

(Out of scope for current build.)

---

## Communication Protocol — Mac ↔ Pi

1. **Adapter push**: Mac runs `rsync -avz --delete` over SSH to `pi@piN.local:/home/pi/keepsake/adapters/{lens_name}/`. Uses pre-shared SSH key.

2. **Reload signal**: After successful rsync, Mac sends `POST http://piN.local:5001/reload` with shared-secret header. Pi reloads adapter into running model.

3. **Status read**: Mac dashboard polls `http://piN.local:5000/status` every 30s. Aggregates results.

4. **Failure handling**: 
   - Pi unreachable → Mac retries push later, marks Pi as offline in dashboard
   - Reload signal fails → Pi continues with previous adapter; Mac retries later
   - Mac unreachable → Pis continue inference with their current adapter indefinitely

---

## Authentication

Dashboard at `keepsake-drift.net/monitor/` requires:
- Password stored in `KEEPSAKE_DASHBOARD_PASSWORD` env var (never in code)
- Session cookie after login (httpOnly, secure)
- HTTPS via Cloudflare Tunnel
- Rate limiting via Cloudflare default

Pi-Mac communication:
- SSH key-based for adapter push
- Shared secret in HTTP header for /reload signal (env var)
- /status endpoint open on local network only (no Masa-sensitive data exposed)

---

## Critical Module Specifications

### `shared/ethics_filter.py`

```python
class EthicsFilter:
    """
    Hardcoded keyword block for Masa Ishikawa's name variants.
    Used on Mac (training data filtering) and Pi (output safety check).
    """
    
    BLOCKED_KEYWORDS = [
        "Masayoshi Ishikawa",
        "Masa Ishikawa",
        "이시카와 마사요시",
        "石川正義",
    ]
    
    def __init__(self):
        self._patterns = [
            re.compile(re.escape(kw), re.IGNORECASE)
            for kw in self.BLOCKED_KEYWORDS
        ]
    
    def is_safe(self, text: str) -> bool:
        return not any(p.search(text) for p in self._patterns)
    
    def filter_batch(self, texts: List[str]) -> List[str]:
        return [t for t in texts if self.is_safe(t)]
```

### `mac/training/lora_trainer.py` (key pattern)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, PeftModel, TaskType

class LensLoRATrainer:
    def __init__(self, lens_name, lens_config, adapter_dir):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.adapter_dir = adapter_dir / lens_name
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        
        # Apple Silicon MPS
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        
        self.tokenizer = AutoTokenizer.from_pretrained(lens_config['global']['base_model'])
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def load_model(self):
        # Try bf16 (better for M-series), fall back to fp16, then fp32
        for dtype in [torch.bfloat16, torch.float16, torch.float32]:
            try:
                self.base_model = AutoModelForCausalLM.from_pretrained(
                    self.lens_config['global']['base_model'],
                    torch_dtype=dtype,
                ).to(self.device)
                break
            except Exception:
                continue
        
        # Load existing adapter if present, else create new
        latest = self._find_latest_checkpoint()
        if latest:
            self.model = PeftModel.from_pretrained(self.base_model, latest, is_trainable=True)
        else:
            lora_config = LoraConfig(
                r=self.lens_config['lora']['r'],
                lora_alpha=self.lens_config['lora']['alpha'],
                target_modules=self.lens_config['lora']['target_modules'],
                lora_dropout=self.lens_config['lora']['dropout'],
                bias="none",
                task_type=TaskType.CAUSAL_LM,
            )
            self.model = get_peft_model(self.base_model, lora_config)
    
    def train_session(self, corpus_path):
        # Standard HF Trainer with mps device, save adapter only
        ...
```

### `mac/distribution/pi_pusher.py` (key pattern)

```python
import subprocess
import requests
import os

class PiPusher:
    def __init__(self, system_config, pi_targets):
        self.config = system_config
        self.targets = pi_targets
    
    def push_adapter(self, lens_name, adapter_path, pi_hostname):
        # rsync over SSH
        cmd = [
            "rsync", "-avz", "--delete",
            "-e", f"ssh -i {self.config['distribution']['pi_ssh_key_path']}",
            f"{adapter_path}/",
            f"{self.config['distribution']['pi_ssh_user']}@{pi_hostname}:"
            f"/home/pi/keepsake/adapters/{lens_name}/",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        # Signal Pi to reload
        try:
            response = requests.post(
                f"http://{pi_hostname}:5001/reload",
                headers={"X-Keepsake-Secret": os.environ["KEEPSAKE_RELOAD_SECRET"]},
                timeout=10,
            )
            return {"success": response.ok, "reload_status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### `mac/active_learning/query_generator.py` (template-based, no LLM)

```python
class QueryGenerator:
    """
    Template-based search query generation. No LLM calls.
    Each lens type has its own templates.
    """
    
    TEMPLATES = {
        "environmental_time": [
            "{location} climate {period}",
            "{location} weather history {period}",
            "{location} natural disasters {period}",
            "{location} environmental conditions {period}",
            "{location} ecology {period}",
        ],
        "infrastructure_time": [
            "{period} immigration policy {country}",
            "{period} visa regulation {country}",
            "{period} administrative procedure {country}",
        ],
        "human_time": [
            "{location} daily life {period}",
            "{location} {period} memoir",
            "{location} cultural history {period}",
        ],
        "digital_time": [
            "{period} digital media {country}",
            "{period} internet {country}",
            "{period} mobile phone {country}",
        ],
        "liminal_time": [
            "migration narrative {period}",
            "{country} immigrants {period}",
            "rite of passage {country} {period}",
        ],
        "more_than_human_time": [
            "{location} natural history {period}",
            "{location} wildlife {period}",
            "{location} ecosystem {period}",
        ],
    }
    
    def generate(self, gap):
        templates = self.TEMPLATES[gap["lens_type"]]
        return [
            t.format(
                location=gap.get("location", ""),
                period=gap.get("period", ""),
                country=gap.get("country", ""),
            ).strip()
            for t in templates
        ]
```

---

## Success Criteria

After full build:

1. ✅ Directory structure as specified (mac/, pi/, shared/)
2. ✅ `cd mac && pip install -r requirements.txt` succeeds on macOS
3. ✅ Qwen 2.5 1.5B loads on Mac MPS device successfully
4. ✅ LoRA fine-tuning completes one epoch on test corpus in <10 min on Mac
5. ✅ Ethics filter blocks Masa keywords (test passes)
6. ✅ Mac generates LoRA adapter checkpoint files
7. ✅ Pi `pip install -r requirements.txt` succeeds on Raspberry Pi OS ARM64
8. ✅ Pi loads adapter and runs inference (response time <2s on CPU, <1s with Hailo if compatible)
9. ✅ Adapter rsync from Mac to Pi succeeds
10. ✅ Pi /reload endpoint accepts signal and reloads adapter
11. ✅ Mac dashboard at http://localhost:8080/monitor/ shows aggregate Pi status
12. ✅ Dashboard requires password if env var set
13. ✅ Control panel toggles affect training (next cycle)
14. ✅ Emergency stop disables all 6 lenses with two-click confirmation
15. ✅ launchd services start on Mac boot, survive reboot
16. ✅ Pi systemd services start on boot, survive reboot
17. ✅ Cloudflare tunnel guide complete in `mac/monitoring/tunnel/setup_cloudflare.md`
18. ✅ Mobile dashboard renders at 375px width

---

## Pending Decisions

These are NOT blockers for build but should be resolved by the artist:

1. **Mac location during Korea (May 15 – June 30)**: travel with artist (recommended) or stay in US?
2. **Hailo-8L compatibility for Qwen 2.5 1.5B**: research during Phase B; CPU fallback acceptable
3. **Output modalities for exhibition**: text only initially, audio/light added in Plexus phase

---

## What's NOT in This Build

Deferred to future work:
- Masa's six memories processing pipeline (exhibition phase, Plexus 2026)
- Real RSS source URLs (placeholders for now; populate after Masa timeline arrives)
- Realtime environmental data feeds for exhibition
- Output visualization design (with Seungho)
- Public-facing artwork pages on `keepsake-drift.net` root
- Inter-lens communication (intentionally excluded; lenses operate independently)
- OpenCLAW integration (removed; Mac handles orchestration directly)

---

## Build Now

This is the canonical specification. Read entirely. Build in Phase A → B order. Pause at end of Phase A and confirm before continuing to Phase B.

If anything is unclear — especially regarding:
- Hailo-8L Python SDK and Qwen compatibility
- launchd plist file specifics for macOS Tahoe
- MPS device support for LoRA training peculiarities

— ask before generating code.

Begin.
