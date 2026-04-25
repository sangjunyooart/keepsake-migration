# Cloudflare Tunnel Setup for Pi 1

This exposes the helper dashboard at `keepsake-drift.net/monitor/` from Pi 1's local
port 8080. Run these steps manually on Pi 1 — they require your Cloudflare account
credentials and are not automated by code.

---

## Prerequisites

- Pi 1 running with the helper dashboard (`python -m monitoring.dashboard`)
- A Cloudflare account that owns `keepsake-drift.net`
- Internet connection on Pi 1

---

## One-time setup (on Pi 1)

### 1. Install cloudflared

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared-linux-arm64.deb
cloudflared --version   # verify
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser. Log in to the Cloudflare account that owns `keepsake-drift.net`.
A credentials file is saved to `~/.cloudflared/`.

### 3. Create the tunnel

```bash
cloudflared tunnel create keepsake-monitor
```

This outputs a tunnel UUID (e.g. `a1b2c3d4-...`). Save it — you need it in step 4.

### 4. Create the tunnel config

Copy `cloudflared_config_example.yml` from this directory, fill in your UUID, and save
to `~/.cloudflared/config.yml`:

```bash
cp helper/tunnel/cloudflared_config_example.yml ~/.cloudflared/config.yml
nano ~/.cloudflared/config.yml   # replace <UUID> with your tunnel UUID
```

### 5. Route DNS

```bash
cloudflared tunnel route dns keepsake-monitor keepsake-drift.net
```

This adds a CNAME record in Cloudflare DNS automatically. It may take a minute to
propagate.

### 6. Set environment variables for the dashboard

Add to `helper/.env` (create from `.env.example`):

```
KEEPSAKE_URL_PREFIX=/monitor
KEEPSAKE_DASHBOARD_PASSWORD=<your-strong-password>
KEEPSAKE_SESSION_SECRET=<output-of-python3 -c "import secrets; print(secrets.token_hex(32))">
```

### 7. Install cloudflared as a systemd service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

Verify:

```bash
sudo systemctl status cloudflared
```

---

## Starting the dashboard (with tunnel)

```bash
cd keepsake-migration/helper
source venv/bin/activate       # or wherever your venv is
python -m monitoring.dashboard
```

Run this in a screen/tmux session or as a second systemd service so it persists.

---

## Verify (from an external network)

```
https://keepsake-drift.net/monitor/
```

Should redirect to the login page. Log in with `KEEPSAKE_DASHBOARD_PASSWORD`.

---

## Domain root behavior

The tunnel routes only `/monitor*` to Pi 1. Other paths (`/`) return Cloudflare's
default 404 or a Cloudflare Pages placeholder — the domain root is reserved for
future artwork pages.

To configure this in Cloudflare Pages (one-time, in the Cloudflare dashboard):
- Create a Cloudflare Pages project with a minimal holding page (or leave it as 404)
- The tunnel ingress handles `/monitor*`; Pages handles everything else

---

## Stopping the tunnel

```bash
sudo systemctl stop cloudflared   # stop
sudo systemctl disable cloudflared  # don't restart on reboot
```

Local dashboard at `pi1.local:8080` continues to work regardless.

---

## Troubleshooting

**Tunnel not connecting**
```bash
sudo journalctl -u cloudflared -f
```

**Login page not loading**
- Verify `KEEPSAKE_URL_PREFIX=/monitor` is set in `.env`
- Verify dashboard process is running on port 8080
- Check `~/.cloudflared/config.yml` has correct UUID and service address

**Password rejected**
- Verify `KEEPSAKE_DASHBOARD_PASSWORD` in `.env` matches what you're typing
- Passwords are case-sensitive

**Pi rebooted, tunnel not reconnecting**
- Verify `sudo systemctl enable cloudflared` was run (auto-start on boot)
- Check `sudo systemctl status cloudflared`
