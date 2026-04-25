# launchd Service Setup — Mac mini M4

## Prerequisites

- Python venv created at `mac/venv/`
- `mac/requirements.txt` installed
- `mac/logs/` directory exists
- `.env` file in `mac/` with credentials (see `.env.example`)

## Step 1 — Create venv and install dependencies

```bash
cd ~/keepsake-migration/mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2 — Create logs directory

```bash
mkdir -p ~/keepsake-migration/mac/logs
```

## Step 3 — Install launchd services

LaunchAgents run as your user and start on login.

```bash
cp ~/keepsake-migration/mac/launchd/com.keepsake.continual-loop.plist \
   ~/Library/LaunchAgents/

cp ~/keepsake-migration/mac/launchd/com.keepsake.dashboard.plist \
   ~/Library/LaunchAgents/
```

## Step 4 — Load services

```bash
launchctl load ~/Library/LaunchAgents/com.keepsake.continual-loop.plist
launchctl load ~/Library/LaunchAgents/com.keepsake.dashboard.plist
```

## Step 5 — Verify

```bash
launchctl list | grep keepsake
# Should show both services with PID (non-zero = running)

# Check logs
tail -f ~/keepsake-migration/mac/logs/continual_loop.log
tail -f ~/keepsake-migration/mac/logs/dashboard.log
```

Dashboard should be live at: http://localhost:8080/monitor/

## Managing services

```bash
# Stop a service
launchctl unload ~/Library/LaunchAgents/com.keepsake.dashboard.plist

# Start again
launchctl load ~/Library/LaunchAgents/com.keepsake.dashboard.plist

# Restart (unload + load)
launchctl unload ~/Library/LaunchAgents/com.keepsake.continual-loop.plist
launchctl load ~/Library/LaunchAgents/com.keepsake.continual-loop.plist
```

## After code update

```bash
cd ~/keepsake-migration
git pull

# Restart services
launchctl unload ~/Library/LaunchAgents/com.keepsake.continual-loop.plist
launchctl load ~/Library/LaunchAgents/com.keepsake.continual-loop.plist

launchctl unload ~/Library/LaunchAgents/com.keepsake.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.keepsake.dashboard.plist
```

## Note on macOS Tahoe / Sequoia

If macOS security prompts appear when loading, go to System Settings → Privacy & Security
and allow the process. This is a one-time step per service.
