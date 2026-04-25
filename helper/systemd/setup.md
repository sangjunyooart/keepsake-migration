# Systemd Service Installation

Run on each Pi after deploying code.

---

## Prerequisites

- Code deployed to `/home/sangjunyooart/keepsake-migration/`
- `artwork/venv/` created and packages installed
- `helper/venv/` created and packages installed (Pi 1 only for dashboard)
- `artwork/logs/` directory exists (created automatically on first run)

---

## Step 1 — Copy service files

```bash
sudo cp ~/keepsake-migration/helper/systemd/keepsake-lens@.service /etc/systemd/system/
# Pi 1 only:
sudo cp ~/keepsake-migration/helper/systemd/keepsake-dashboard.service /etc/systemd/system/
sudo cp ~/keepsake-migration/helper/systemd/keepsake-tunnel.service /etc/systemd/system/
```

## Step 2 — Reload systemd

```bash
sudo systemctl daemon-reload
```

## Step 3 — Enable and start the lens service for this Pi

Replace `<LENS_NAME>` with this Pi's assigned lens:

| Pi | Lens |
|----|------|
| Pi 1 | human_time |
| Pi 2 | infrastructure_time |
| Pi 3 | environmental_time |
| Pi 4 | digital_time |
| Pi 5 | liminal_time |
| Pi 6 | more_than_human_time |

```bash
sudo systemctl enable keepsake-lens@<LENS_NAME>
sudo systemctl start keepsake-lens@<LENS_NAME>
```

## Step 4 — Pi 1 only: Enable dashboard and tunnel

```bash
sudo systemctl enable keepsake-dashboard
sudo systemctl start keepsake-dashboard

sudo systemctl enable keepsake-tunnel
sudo systemctl start keepsake-tunnel
```

## Step 5 — Verify

```bash
sudo systemctl status keepsake-lens@<LENS_NAME>
journalctl -u keepsake-lens@<LENS_NAME> -f
```

---

## Creating the artwork logs directory

If it doesn't exist yet:

```bash
mkdir -p ~/keepsake-migration/artwork/logs
mkdir -p ~/keepsake-migration/helper/logs
```

---

## Updating after a code change

```bash
cd ~/keepsake-migration
git pull origin claude/review-build-spec-04Bel
pip install -r artwork/requirements.txt --extra-index-url https://www.piwheels.org/simple
sudo systemctl restart keepsake-lens@<LENS_NAME>
```
