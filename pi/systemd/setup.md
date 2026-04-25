# Pi Systemd Service Setup

Run on each Raspberry Pi after deploying code.

## Prerequisites

- Code at `/home/pi/keepsake-migration/`
- Python venv at `pi/venv/`
- `pi/requirements.txt` installed
- SSH key from Mac configured for rsync

## Step 1 — Clone / pull repo

```bash
cd ~
git clone https://github.com/sangjunyooart/keepsake-migration.git
# or: git pull origin claude/review-build-spec-04Bel
```

## Step 2 — Create venv and install

```bash
cd ~/keepsake-migration/pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --extra-index-url https://www.piwheels.org/simple
```

(torch install takes ~10 min on Pi — be patient)

## Step 3 — Configure this Pi

Edit `pi/config/pi_config.yaml`:

```bash
nano ~/keepsake-migration/pi/config/pi_config.yaml
```

Set `lens_name` and `hostname` for this specific Pi.

## Step 4 — Create .env

```bash
cp ~/keepsake-migration/pi/.env.example ~/keepsake-migration/pi/.env
nano ~/keepsake-migration/pi/.env
# Set KEEPSAKE_RELOAD_SECRET to match Mac's value
```

## Step 5 — Create logs directory

```bash
mkdir -p ~/keepsake-migration/pi/logs
mkdir -p ~/keepsake-migration/pi/adapters
```

## Step 6 — Install service files

Replace `<LENS_NAME>` with this Pi's lens (e.g. `environmental_time`):

```bash
# Copy template services — these are parameterised with %i (instance name)
sudo cp ~/keepsake-migration/pi/systemd/keepsake-pi-inference.service \
        /etc/systemd/system/keepsake-pi-inference@.service
sudo cp ~/keepsake-migration/pi/systemd/keepsake-pi-status.service \
        /etc/systemd/system/keepsake-pi-status@.service
sudo cp ~/keepsake-migration/pi/systemd/keepsake-pi-receiver.service \
        /etc/systemd/system/keepsake-pi-receiver@.service

sudo systemctl daemon-reload
```

## Step 7 — Enable and start

```bash
LENS=environmental_time   # change per Pi

sudo systemctl enable keepsake-pi-inference@${LENS}
sudo systemctl enable keepsake-pi-status@${LENS}
sudo systemctl enable keepsake-pi-receiver@${LENS}

sudo systemctl start keepsake-pi-status@${LENS}
sudo systemctl start keepsake-pi-receiver@${LENS}
sudo systemctl start keepsake-pi-inference@${LENS}
```

Start status + receiver first — inference takes ~2 min to load Qwen.

## Step 8 — Verify

```bash
sudo systemctl status keepsake-pi-status@${LENS}
curl http://localhost:5000/status   # should return JSON
curl http://localhost:5001/health   # should return {"ok": true}
```

## Updating after code change

```bash
cd ~/keepsake-migration
git pull origin claude/review-build-spec-04Bel

sudo systemctl restart keepsake-pi-inference@${LENS}
sudo systemctl restart keepsake-pi-status@${LENS}
sudo systemctl restart keepsake-pi-receiver@${LENS}
```

## Lens assignments

| Pi | Lens |
|----|------|
| pi1.local | human_time |
| pi2.local | infrastructure_time |
| pi3.local | environmental_time |
| pi4.local | digital_time |
| pi5.local | liminal_time |
| pi6.local | more_than_human_time |
