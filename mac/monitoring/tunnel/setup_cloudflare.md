# Cloudflare Tunnel Setup — keepsake-drift.net/monitor/

This guide sets up the tunnel so the dashboard is accessible at
`https://keepsake-drift.net/monitor/` from anywhere.

## Prerequisites

- Cloudflare account with `keepsake-drift.net` managed
- `cloudflared` installed on Mac:
  ```bash
  brew install cloudflared
  ```

## Step 1 — Authenticate

```bash
cloudflared tunnel login
```

This opens a browser. Select `keepsake-drift.net`.

## Step 2 — Create the tunnel

```bash
cloudflared tunnel create keepsake-monitor
```

Note the UUID printed. Copy it.

## Step 3 — Create config file

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste (replace `<UUID>` with your tunnel UUID):

```yaml
tunnel: <UUID>
credentials-file: /Users/sangjunyooart/.cloudflared/<UUID>.json

ingress:
  - hostname: keepsake-drift.net
    path: /monitor
    service: http://localhost:8080
  - service: http_status:404
```

## Step 4 — Create DNS route

```bash
cloudflared tunnel route dns keepsake-monitor keepsake-drift.net
```

## Step 5 — Test manually

```bash
# Start dashboard first
cd ~/keepsake-migration/mac
python -m monitoring.dashboard &

# Run tunnel
cloudflared tunnel run keepsake-monitor
```

Visit `https://keepsake-drift.net/monitor/` — should show dashboard.

## Step 6 — Install as launchd service

```bash
cloudflared service install
```

This installs the tunnel as a system launchd service that starts on boot.

## Notes

- Dashboard must be running on port 8080 before tunnel is useful
- Cloudflare provides HTTPS automatically
- Set `KEEPSAKE_DASHBOARD_PASSWORD` in mac/.env for password protection
- Path matching: Cloudflare routes `/monitor/*` to `http://localhost:8080/monitor/*`
  The Flask app uses URL_PREFIX=/monitor, so routes align automatically
