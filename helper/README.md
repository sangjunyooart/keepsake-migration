# Helper — Private Monitoring Infrastructure

> **This is NOT part of the artwork.**
>
> This directory contains private monitoring infrastructure used by the artist (Sangjun Yoo) to verify that the artwork's lenses are training correctly during the preparation phase. Nothing in this directory is exhibited. Audiences will not see this dashboard, these logs, or these metrics. This is a workshop tool, equivalent to a sketchbook or a calibration instrument. It is excluded from the artwork's conceptual frame.

---

## What this does

- **`monitoring/status_endpoint.py`** — Flask service (port 5000) on each Pi. Exposes `/status` JSON with system health, training stats, adapter info, and latest drift. Reads artwork's logs and adapters — never writes to them.
- **`monitoring/dashboard.py`** — Flask dashboard (port 8080) on Pi 1 only. Aggregates `/status` from all 6 Pis. Supports two modes: local LAN access and remote access via Cloudflare tunnel.
- **`monitoring/auth.py`** — Authentication helpers: session management, password verification, `require_auth` decorator.
- **`monitoring/drift_measurement.py`** — Reads LoRA adapter weights from artwork checkpoints, computes norm-based drift between consecutive saves. Writes to `helper/logs/drift_<lens>.jsonl`.

---

## Two modes of operation

### Mode 1 — Local (LAN)

Run without setting `KEEPSAKE_URL_PREFIX`. No authentication required (LAN-only convenience).

```
http://pi1.local:8080/
```

### Mode 2 — Remote (online via Cloudflare tunnel)

Set `KEEPSAKE_URL_PREFIX=/monitor` and `KEEPSAKE_DASHBOARD_PASSWORD`. Dashboard becomes accessible at:

```
https://keepsake-drift.net/monitor/
```

See `tunnel/setup_cloudflare.md` for one-time tunnel setup on Pi 1.

---

## Setup

```bash
cd keepsake-migration/helper
pip install -r requirements.txt

# For online mode: copy and fill in .env
cp .env.example .env
nano .env    # set KEEPSAKE_URL_PREFIX, KEEPSAKE_DASHBOARD_PASSWORD, KEEPSAKE_SESSION_SECRET
```

---

## Running the status endpoint (each Pi)

```bash
cd keepsake-migration/helper
python -m monitoring.status_endpoint <lens_name>
# → http://0.0.0.0:5000/status
```

Run alongside the artwork's `lens_runner.py` on each Pi.

## Running the dashboard (Pi 1 only)

```bash
cd keepsake-migration/helper
python -m monitoring.dashboard
# LAN mode:    http://pi1.local:8080/
# Online mode: https://keepsake-drift.net/monitor/  (after tunnel setup)
```

---

## URL structure (online mode)

| URL | Description |
|---|---|
| `/monitor/` | Main dashboard — all 6 lenses |
| `/monitor/login` | Login page |
| `/monitor/logout` | Clear session |
| `/monitor/lens/<name>` | Per-lens detail view |
| `/monitor/api/status` | Aggregated JSON for all lenses |

The domain root (`keepsake-drift.net/`) is reserved for future artwork pages.

---

## Security notes

- Never commit `.env` to git (it is gitignored)
- Use a strong password (16+ characters, generated)
- Generate SESSION_SECRET with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- HTTPS is enforced automatically by Cloudflare
- Session expires after 24 hours

---

## Dependency on artwork

This helper reads from `../artwork/` (adapter checkpoints, training decision logs). It never writes into `../artwork/`. The artwork runs independently and does not know the helper exists.

---

## Logs

Helper writes its own logs to `helper/logs/` (gitignored).

| File | Contents |
|---|---|
| `logs/drift_<lens>.jsonl` | LoRA weight drift measurements per lens |
