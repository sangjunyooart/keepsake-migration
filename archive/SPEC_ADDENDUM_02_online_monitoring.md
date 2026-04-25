# Spec Addendum 02 — Online Monitoring Access

> **For Claude Code**: This document extends `CLAUDE_CODE_BUILD_SPEC.md` and `SPEC_ADDENDUM_01_artwork_helper_separation.md`. Read all three. Where they conflict, later addenda take precedence.

---

## Why This Addendum Exists

The helper system (defined in Addendum 01) currently runs on the local network only — accessible from `pi1.local:8080`. I (Sangjun) need to monitor the 6 Pis from outside the local network, especially while:

- I am in Korea (May 15 – June 30, 2026) recovering from surgery, with the Pis running autonomously at my Korean residence
- I am traveling between locations
- I'm on mobile, away from a desktop

**The helper must be reachable online — but it remains the artist's private monitoring infrastructure, not part of the artwork.**

---

## Scope

This addendum specifies:
1. How the helper becomes accessible at `keepsake-drift.net`
2. Authentication and security requirements
3. Online/offline parity (helper works whether I'm on local network or remote)
4. URL structure that *does not commit* the domain to being purely monitoring (in case I later add public-facing artwork pages)

This addendum does **not** address:
- Public-facing artwork pages (deferred — separate addendum if/when needed)
- Audience-facing visualizations (artwork, not helper)
- Real-time streaming of lens outputs (artwork, not helper)

---

## URL Structure

Reserve the domain root and a clean public space for future artwork use. Place all monitoring under a dedicated subpath.

```
https://keepsake-drift.net/                  → reserved (currently empty or simple holding page)
https://keepsake-drift.net/monitor/          → helper dashboard (password-protected)
https://keepsake-drift.net/monitor/login     → authentication
https://keepsake-drift.net/monitor/api/...   → JSON status API
https://keepsake-drift.net/monitor/lens/{name}/  → per-lens detail view
```

**Rationale**: The domain bears the artwork series name. Putting the dashboard at `/monitor/` keeps the root and other paths free for any future artwork page, without rearchitecting later.

**Alternative considered**: subdomain `monitor.keepsake-drift.net`. Equally valid. The build should support either via configuration. Default to subpath `/monitor/`.

---

## Architecture — Two Modes, One System

The helper must work in two modes without code changes:

### Mode 1 — Local (offline-friendly)

I'm on the same network as the Pis (e.g., at home, at the residency).

```
[My laptop/phone] ─── local network ─── [Pi 1 dashboard:8080]
                                              ↓ reads
                                        [Pi 1...6 status:5000]
```

Direct access. No internet required. Same as Addendum 01 design.

### Mode 2 — Remote (online)

I'm in Korea, the Pis are at my home (also in Korea, but separate from where I'll be staying), and I check from my phone.

```
[My phone] ─── internet ─── [keepsake-drift.net/monitor/]
                                       ↓ via secure tunnel
                                [Pi 1 dashboard:8080]
                                       ↓ reads
                                [Pi 1...6 status:5000]
```

Same dashboard, accessed via the public domain.

---

## Implementation — Cloudflare Tunnel (Recommended)

Use **Cloudflare Tunnel** (`cloudflared`) to expose Pi 1's local dashboard at `keepsake-drift.net/monitor/`. This is the cleanest approach because:

- No port forwarding on the home router (works behind NAT, fewer security risks)
- Free
- Provides HTTPS automatically
- Easy to start/stop
- Cloudflare provides DDoS protection and access policies
- Survives IP changes (no need to update DNS when Korean home IP changes)

### Build steps for Pi 1

Create `helper/tunnel/setup_cloudflare.md` with these instructions (Claude Code does not execute these — I will run them when ready):

```markdown
# Cloudflare Tunnel Setup for Pi 1

## One-time setup (on Pi 1)

1. Install cloudflared:
   ```
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
   sudo dpkg -i cloudflared-linux-arm64.deb
   ```

2. Authenticate with Cloudflare:
   ```
   cloudflared tunnel login
   ```
   This opens a browser. Log in to Cloudflare account that owns keepsake-drift.net.

3. Create the tunnel:
   ```
   cloudflared tunnel create keepsake-monitor
   ```
   This generates a tunnel UUID. Save it.

4. Create config at `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <UUID-from-step-3>
   credentials-file: /home/pi/.cloudflared/<UUID>.json
   
   ingress:
     - hostname: keepsake-drift.net
       path: /monitor/*
       service: http://localhost:8080
     - hostname: keepsake-drift.net
       path: /monitor
       service: http://localhost:8080
     - service: http_status:404
   ```

5. Route DNS:
   ```
   cloudflared tunnel route dns keepsake-monitor keepsake-drift.net
   ```

6. Run as service:
   ```
   sudo cloudflared service install
   sudo systemctl enable cloudflared
   sudo systemctl start cloudflared
   ```

## Verify

From any external network, visit https://keepsake-drift.net/monitor/ — should show login page.

## Stop tunnel (e.g., during exhibition setup)

```
sudo systemctl stop cloudflared
```
```

### What Claude Code builds vs. what I do manually

- **Claude Code builds**: the dashboard code itself (with `/monitor/` path prefix support, authentication, etc.)
- **I run manually** (because they require my Cloudflare account credentials): the cloudflared installation and tunnel setup

This separation is intentional — credentials should not pass through code generation.

---

## Authentication

The dashboard at `/monitor/` must require authentication. Use a simple but adequate scheme:

### Approach: HTTP Basic Auth via Flask

Add a single shared password (read from environment variable) plus a session cookie for browser convenience.

```python
# In helper/monitoring/dashboard.py

import os
from functools import wraps
from flask import request, Response, session, redirect

DASHBOARD_PASSWORD = os.environ.get('KEEPSAKE_DASHBOARD_PASSWORD')
SESSION_SECRET = os.environ.get('KEEPSAKE_SESSION_SECRET', 'change-me-in-production')

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('authenticated'):
            return f(*args, **kwargs)
        return redirect('/monitor/login')
    return decorated
```

Login route accepts password, sets `session['authenticated'] = True`, redirects to dashboard.

**Important**: 
- Password is set via environment variable, never hardcoded
- HTTPS-only (Cloudflare provides this for the public domain)
- Session cookie is `httpOnly` and `secure`
- Logout route clears session

Default for local-only mode: if `KEEPSAKE_DASHBOARD_PASSWORD` env var is not set, dashboard logs a warning and skips auth (LAN-only convenience). When deployed online via tunnel, the env var must be set, otherwise the dashboard refuses to start.

---

## URL Path Prefix Support

The dashboard must support both:
- Local mode: `http://pi1.local:8080/` (root)
- Remote mode: `https://keepsake-drift.net/monitor/` (subpath)

Implementation: read URL prefix from environment variable.

```python
URL_PREFIX = os.environ.get('KEEPSAKE_URL_PREFIX', '')

# All routes registered with prefix:
@app.route(f'{URL_PREFIX}/')
@app.route(f'{URL_PREFIX}/lens/<lens_name>')
@app.route(f'{URL_PREFIX}/api/status')
# etc.
```

When deployed via Cloudflare tunnel, set `KEEPSAKE_URL_PREFIX=/monitor` so internal links resolve correctly.

When running locally for offline access, leave it unset.

---

## What the Dashboard Must Show

Same as Addendum 01, plus these additions for remote use:

### Top-level dashboard view

```
KEEPSAKE LENS MONITOR        [logged in as artist] [logout]
Last refresh: 14:32 KST 2026-04-26
Auto-refresh: 30s              [pause]

┌─────────────────────────────────────────┐
│  human_time          ●●●○○ healthy      │  ← clickable to detail view
│  Trainings: 47 · Drift: 0.0234          │
│  Last training: 2h ago                  │
├─────────────────────────────────────────┤
│  infrastructure_time ●●○○○ healthy      │
│  Trainings: 12 · Drift: 0.0089          │
│  Last training: 12h ago                 │
├─────────────────────────────────────────┤
│  ... 4 more lenses ...                  │
└─────────────────────────────────────────┘

System summary: All 6 Pis online. No alerts.
```

### Per-lens detail view (`/monitor/lens/{name}/`)

When a lens card is tapped:
- Full training history (last 50 sessions)
- Drift trajectory chart (simple SVG, no JS libraries)
- Recent decisions log (last 20)
- System metrics over last 24h
- Adapter checkpoint list
- Raw `/api/status` JSON link

### Mobile-optimized

- Single-column layout
- Large tap targets
- Auto-refresh that respects battery (pause when tab hidden)
- No external CDN dependencies (works on poor connections)

---

## API Endpoint

Add `GET /monitor/api/status` returning aggregated JSON of all 6 lenses. This allows:
- External scripts (e.g., a daily summary cron job) to read state
- My phone widget (if I build one later) to fetch data
- Future ChatGPT/Claude conversations: I can paste the JSON to give myself context about current system state

JSON shape:

```json
{
  "timestamp": "2026-04-26T14:32:00+09:00",
  "lenses": {
    "human_time": { ... full status from Pi's /status endpoint ... },
    "infrastructure_time": { ... },
    ...
  },
  "summary": {
    "total_lenses": 6,
    "online": 6,
    "offline": 0,
    "alerts": []
  }
}
```

API endpoint also requires authentication (same session cookie).

---

## Offline-First Principle

The helper must work *exactly the same way* whether or not Cloudflare tunnel is running. Specifically:

1. The dashboard runs on Pi 1 regardless of tunnel state
2. Local network access (`pi1.local:8080`) always works for me when I'm on the LAN
3. The tunnel adds remote access on top; it does not replace local access
4. If Cloudflare is down, local access still functions
5. If Pi 1 is rebooted, the tunnel reconnects automatically (systemd service)

This matters because:
- Korea internet to my residence may be intermittent
- I may be on the local Korean wifi *and* on cellular at different times
- Cloudflare itself can have outages

---

## File Updates

Update these files from Addendum 01:

### `helper/monitoring/dashboard.py`

Add:
- URL prefix support via env var
- Authentication via session cookie
- Login/logout routes
- Per-lens detail view at `/lens/{name}/`
- API endpoint at `/api/status`
- Mobile-optimized responsive HTML

### `helper/monitoring/auth.py` (new)

Authentication helpers:
- `require_auth` decorator
- `verify_password` function
- Session management

### `helper/tunnel/` (new directory)

- `setup_cloudflare.md` — manual setup instructions (content above)
- `cloudflared_config_example.yml` — config template I can copy and fill

### `helper/.env.example` (new)

Document required environment variables:

```
KEEPSAKE_DASHBOARD_PASSWORD=set-a-strong-password-here
KEEPSAKE_SESSION_SECRET=generate-with-secrets-token-hex-32
KEEPSAKE_URL_PREFIX=/monitor
KEEPSAKE_TIMEZONE=Asia/Seoul
```

### `helper/README.md`

Update to describe:
- Dual-mode operation (local + online)
- How to set environment variables
- Pointer to `tunnel/setup_cloudflare.md` for online setup
- Security notes (don't commit `.env`, use strong password)
- Reaffirmation: this is monitoring infrastructure, NOT artwork

### `helper/requirements.txt`

Add:
```
python-dotenv==1.0.0
```

For loading `.env` file in development.

---

## Domain Root Behavior

Currently `keepsake-drift.net/` (root) should serve a minimal holding page or 404 — *not* the monitoring dashboard. This preserves the domain root for future use (potential public artwork pages).

For now, configure Cloudflare ingress to route only `/monitor*` paths to the Pi. Other paths return Cloudflare's default page or a static "Coming soon" placeholder hosted on Cloudflare Pages.

This is a one-time Cloudflare configuration, not code Claude Code generates. Document this in `helper/tunnel/setup_cloudflare.md`.

---

## Security Considerations

This is an art project, not a bank, but reasonable hygiene:

1. **Strong password**: 16+ characters, generated, stored only in `.env` and a password manager
2. **HTTPS only**: Cloudflare enforces this automatically
3. **Rate limiting**: Cloudflare provides default protection
4. **No sensitive data exposed**: status endpoint exposes Pi metrics only, not Masa's data, not corpus content, not adapter weights
5. **`.env` excluded from git** (add to `.gitignore`)
6. **Session timeout**: 24 hours, then re-login required

What is *not* exposed via the dashboard:
- Masa's name or any identifying information about him
- Training corpus content (only counts and metadata)
- Adapter weights themselves (only norm signatures for drift measurement)

This means even in the worst case (password leaked), no ethically sensitive material is at risk.

---

## Updated Success Criteria (additions)

In addition to Addendum 01's criteria:

11. ✅ Dashboard runs locally without env vars (LAN mode)
12. ✅ Dashboard refuses to start without `KEEPSAKE_DASHBOARD_PASSWORD` if `KEEPSAKE_URL_PREFIX` is set (production safety)
13. ✅ Login flow works: wrong password → reject; correct password → session created
14. ✅ Per-lens detail view loads and shows training history
15. ✅ `/monitor/api/status` returns valid aggregated JSON when authenticated
16. ✅ `helper/tunnel/setup_cloudflare.md` exists with complete manual instructions
17. ✅ `.env.example` exists; `.env` is gitignored

---

## Build Order (when implementing this addendum)

1. Add URL prefix support to existing dashboard
2. Add authentication (login route, session, decorator)
3. Add per-lens detail view
4. Add API endpoint
5. Add mobile-optimized CSS
6. Create `helper/tunnel/setup_cloudflare.md`
7. Create `helper/.env.example`
8. Update `helper/README.md`
9. Update `helper/requirements.txt`
10. Verify against new success criteria

---

## What Comes After This Addendum

Future addenda may cover:
- **Addendum 03** (probable): OpenCLAW integration for autonomous data collection
- **Addendum 04** (probable): RAG memory system (Chroma) — Plexus residency phase
- **Addendum 05** (later): Daily summary auto-generation and work journal system
- **Addendum 06** (much later, if at all): Public-facing artwork pages at the domain root

Each will reference this addendum's authentication and URL structure as the foundation.

---

## Build Now

Read this entire addendum together with `CLAUDE_CODE_BUILD_SPEC.md` and `SPEC_ADDENDUM_01_artwork_helper_separation.md`.

If anything conflicts with earlier specs, this addendum takes precedence.

If anything is unclear, ask before generating code.
