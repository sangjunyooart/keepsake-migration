# Helper — Private Monitoring Infrastructure

> **This is NOT part of the artwork.**
>
> This directory contains private monitoring infrastructure used by the artist (Sangjun Yoo) to verify that the artwork's lenses are training correctly during the preparation phase. Nothing in this directory is exhibited. Audiences will not see this dashboard, these logs, or these metrics. This is a workshop tool, equivalent to a sketchbook or a calibration instrument. It is excluded from the artwork's conceptual frame.

---

## What this does

- **`monitoring/status_endpoint.py`** — Flask service (port 5000) that runs on each Pi alongside the artwork's lens runner. Exposes a `/status` JSON endpoint reporting system health, training stats, adapter checkpoints, and latest drift measurement. Reads from the artwork's logs and adapters — never writes to them.

- **`monitoring/dashboard.py`** — Flask dashboard (port 8080) that runs on Pi 1 only. Aggregates `/status` from all 6 Pis and renders a mobile-friendly HTML page with auto-refresh. Shows KST time. Handles unreachable Pis gracefully.

- **`monitoring/drift_measurement.py`** — Reads LoRA adapter weights from the artwork's checkpoints and computes norm-based drift between consecutive saves. Writes its own log to `helper/logs/drift_<lens>.jsonl`. Does not modify any artwork file.

---

## Dependency

This helper reads from `../artwork/` (adapter checkpoints, training decision logs). It never writes into `../artwork/`. The artwork runs independently and does not know the helper exists.

---

## Setup

```bash
cd keepsake-migration/helper
pip install -r requirements.txt
```

This can share the same virtualenv as the artwork, or use a separate one.

---

## Running the status endpoint (each Pi)

```bash
cd keepsake-migration/helper
python -m monitoring.status_endpoint <lens_name>
# → http://0.0.0.0:5000/status
```

Run this alongside `artwork/orchestration/lens_runner.py` on each Pi.

## Running the dashboard (Pi 1 only)

```bash
cd keepsake-migration/helper
python -m monitoring.dashboard
# → http://0.0.0.0:8080
```

---

## Logs

Helper writes its own logs to `helper/logs/` (gitignored). These are separate from `artwork/logs/`.

| File | Contents |
|---|---|
| `logs/drift_<lens>.jsonl` | LoRA weight drift measurements per lens |
