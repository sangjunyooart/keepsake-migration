# Keepsake-Migration: Design Decision History

> **Purpose**: This document preserves the reasoning behind major architectural decisions. It is not a build spec. The current build specification is `CLAUDE_CODE_BUILD_SPEC_v2.md`.

This file is for the artist (Sangjun) and any future collaborators who want to understand *why* the system is designed the way it is.

---

## Decision Timeline

### April 2026 — Initial design (deprecated)

**First design**: Each Pi independently trains its own lens.

**Reasoning at the time**: Each agent should be fully autonomous, including training. Pi's slowness was framed as aesthetically aligned with the work's temporal claims.

**Why deprecated**: Pi 5's CPU is not suitable for sustained LoRA training. 4-month training capacity uncertain. Risk that lenses would not be sufficiently formed by ISEA 2026.

---

### April 25, 2026 — Mac mini M4 architecture

**Final design**: Mac mini M4 trains all 6 lenses. Pi devices serve as inference bodies, receiving adapters wirelessly.

**Reasoning**:

1. **Technical reality**: Mac M4 trains LoRA 50× faster than Pi CPU. 6 lenses can complete initial training in 3-6 hours instead of 4 months of uncertain Pi training.

2. **Reframing autonomy**: "Each lens is its own agent" doesn't require physical training colocation. What matters is:
   - The lens evolves autonomously (no human triggers training cycles) — preserved
   - The lens is not dependent on external corporate AI (ChatGPT, Claude, etc.) — preserved
   - The lens is materially distinct (different LoRA weights) — preserved
   - Each lens has a physical body in the exhibition space — preserved (each Pi is one lens's body)

3. **Reframing slowness**: The work's temporal claim is not about *training speed* but about *evolution duration*. Lenses continue training for months. The 4-6 month duration of becoming is preserved, even if any single training session takes minutes instead of hours.

4. **Conceptual integrity gain**: 
   - Mac as formative environment + Pi as embodiment maps cleanly to Whitehead's process philosophy
   - "Lens is born in Mac, lives in Pi body, continues becoming through Mac-driven updates"
   - Spatial hypertext is now physically embodied: each Pi is at a different location in exhibition, lens is not just code-distinguished but spatially-distinguished

---

### April 25, 2026 — OpenCLAW removal

**Decision**: Remove OpenCLAW from the system entirely.

**Reasoning**:

OpenCLAW was originally introduced as an autonomous orchestration / active learning engine. Upon closer examination:

- All proposed OpenCLAW roles can be implemented with standard Python:
  - Cron-like scheduling → systemd / launchd
  - Self-learning decisions → meta-controller (already built)
  - Active search query generation → template-based, no LLM needed
  - Result evaluation → keyword matching + ethics filter, no LLM needed

- OpenCLAW would have introduced complexity without proportional value
- OpenCLAW potentially required external API calls (token costs, ethical concerns about Masa data leaving local hardware)
- The artist had not actually researched OpenCLAW's specific capabilities; it was proposed speculatively

By removing it, the system becomes:
- Fully self-hosted (no external AI services)
- Token-cost-free
- Conceptually cleaner (no dependency on third-party tooling)

---

### April 2026 — Base model: Qwen 2.5 1.5B

**Decision**: Use Qwen 2.5 1.5B (Apache 2.0) as base model.

**Considered alternatives**:
- TinyLlama 1.1B: lighter, but English-only, weaker expression
- Phi-3 Mini 3.8B: richer expression, but tight on Mac 16GB during training
- Llama 3.2 3B: similar to Phi-3, license complexity

**Reasoning for Qwen**:
1. Strong Japanese language support — critical for Masa's trajectory data (Japan-based years)
2. 1.5B parameters fit comfortably in Mac mini 16GB during LoRA training (~7-8GB peak, leaving headroom for parallel processes)
3. Inference on Pi 5 + AI HAT+ runs at acceptable speed (sub-second)
4. Apache 2.0 license — clean for art project
5. Stronger expression than 1.1B; differences between 6 lenses will be more measurable

LoRA rank increased from 8 (original spec) to 16, since Mac handles the larger size easily and lens differentiation strengthens.

---

### April 2026 — Ethics architecture

**Foundational decision (preserved across all designs)**:

The system NEVER trains on Masa Ishikawa's direct subjective materials. Training data is only objective spatiotemporal traces of his life trajectory.

**Implementation**:
- Hardcoded keyword block in `shared/ethics_filter.py`
- Cannot be bypassed by configuration changes
- Applied to all Mac-side training data
- Defense-in-depth: applied to Pi-side outputs

**Why this matters**:
This commitment is not just ethical hygiene; it's a constitutive feature of what the work *is*. The work performs a sociology of migration: an objective system encountering subjective memory. If the system absorbed Masa's subjective materials, the work would no longer be that performance — it would be a digital portrait, which is a different and weaker artwork.

The hardcoded filter makes this commitment a verifiable property of the codebase, not just a verbal promise.

---

### April 2026 — Active learning

**Decision**: Lenses self-assess corpus gaps and actively search public archives to fill them. Not just passive RSS ingestion.

**Reasoning**:

Original design used static RSS feeds. This wouldn't deliver the Masa-specific historical data the work needs. Each lens needs data corresponding to Masa's *specific* spatiotemporal trajectory: his particular places, in his particular years, with his particular environmental contexts.

Active learning addresses this:
1. Self-assessment: lens identifies what it doesn't know about Masa's trajectory
2. Query generation: template-based, lens-type-specific
3. Search: NOAA, Wikipedia, Internet Archive, etc.
4. Evaluation: keyword + ethics filter
5. Ingestion: only relevant, ethics-clean data enters corpus

This makes each lens an *agent* in the technical sense — capable of identifying its own knowledge gaps and seeking to fill them, without human triggers.

---

### April 2026 — Helper / artwork separation (preserved)

**Decision**: Code is split into:
- Artwork-proper (training, inference, output) 
- Helper (monitoring, dashboards)

In the v2 unified spec, this maps to:
- Artwork: `mac/training/`, `mac/data_pipeline/`, `mac/active_learning/`, `mac/distribution/`, `pi/inference/`, `pi/output/`
- Helper: `mac/monitoring/`

**Reasoning**: The dashboard is the artist's private monitoring tool. It is not part of the artwork. Audiences will not see it. Maintaining this separation prevents helper logic from contaminating the artwork's aesthetic surface.

The one-way dependency principle: helper reads from artwork, artwork never imports from helper. (Sole carve-out: control panel writes to `runtime_state/`, a dedicated directory.)

---

### April 2026 — Online monitoring at keepsake-drift.net/monitor/

**Decision**: Helper dashboard accessible online via Cloudflare Tunnel at `keepsake-drift.net/monitor/`. Domain root reserved for potential future use.

**Reasoning**: Artist needs to monitor system from anywhere (especially during Korea recovery period May–June 2026). Cloudflare Tunnel provides:
- HTTPS automatically
- No router port forwarding
- Survives IP changes
- Free
- DDoS protection

Subpath `/monitor/` keeps domain root free for future artwork-facing pages without rearchitecting.

---

## Reasoning Patterns Worth Preserving

### Pattern 1: Question speculative tooling

OpenCLAW was added speculatively without research. It accumulated weight in subsequent specs. Eventually it was removed entirely.

**Lesson**: When a tool is proposed but not researched, treat it as a placeholder. Do not let it become structural.

### Pattern 2: Reframe before reengineering

When Pi training capacity was identified as risk, the first instinct was to find faster Pi alternatives (Jetson, etc.). Better solution: reframe what Pi does (inference, not training) and use existing Mac for training.

**Lesson**: Hardware constraints often signal a wrong role assignment, not a need for better hardware.

### Pattern 3: Conceptual integrity > technical minimalism

The "fully self-hosted" commitment costs complexity vs. just calling external APIs. But it is constitutive of what the work means (autonomy from corporate AI, ethical containment of Masa's data, long-term operational independence).

**Lesson**: Some complexity is paying for meaning, not paying for nothing.

### Pattern 4: Make ethics structural, not procedural

Ethics filter is hardcoded, not configurable. This means even a careless config change cannot accidentally allow Masa's materials into training data.

**Lesson**: Ethical commitments worth preserving deserve to be embodied in code structure, not just documentation.

---

## Decisions Still Pending (as of 2026-04-25)

1. Mac's physical location during Korea period (travel with Sangjun vs stay in US)
2. Hailo-8L compatibility with Qwen 2.5 1.5B (will be discovered during Phase B)
3. Exhibition output modalities (text vs audio vs light) — Plexus residency decision with Seungho
4. Masa's six memory inputs design — Plexus residency decision with Masa

---

## File History

- `CLAUDE_CODE_BUILD_SPEC.md` (April 2026) — original Pi-trains design
- `SPEC_ADDENDUM_01_artwork_helper_separation.md` (April 2026) — directory separation
- `SPEC_ADDENDUM_02_online_monitoring.md` (April 2026) — Cloudflare tunnel
- `SPEC_ADDENDUM_03_active_learning_control_panel.md` (April 2026) — active learning, control panel
- `SPEC_ADDENDUM_04_mac_centric_architecture.md` (April 2026) — Mac-centric pivot

All five archived under `/archive/`. Current canonical spec: `CLAUDE_CODE_BUILD_SPEC_v2.md`.
