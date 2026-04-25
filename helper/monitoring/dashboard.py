import sys
from datetime import datetime, timezone, timedelta

import requests
from flask import Flask, render_template_string

PI_HOSTS = {
    "human_time": "pi1.local:5000",
    "infrastructure_time": "pi2.local:5000",
    "environmental_time": "pi3.local:5000",
    "digital_time": "pi4.local:5000",
    "liminal_time": "pi5.local:5000",
    "more_than_human_time": "pi6.local:5000",
}

KST = timezone(timedelta(hours=9))

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="30">
  <title>Keepsake Migration — Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Courier New', monospace;
      background: #0a0a0a;
      color: #c8c8c8;
      padding: 16px;
    }
    h1 {
      font-size: 1.1rem;
      color: #888;
      margin-bottom: 4px;
      letter-spacing: 0.1em;
    }
    .subtitle {
      font-size: 0.75rem;
      color: #444;
      margin-bottom: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 12px;
    }
    .card {
      background: #111;
      border: 1px solid #222;
      border-radius: 4px;
      padding: 14px;
    }
    .card.error {
      border-color: #3a1a1a;
      background: #120a0a;
    }
    .card-title {
      font-size: 0.85rem;
      color: #7a9fcf;
      letter-spacing: 0.05em;
      margin-bottom: 10px;
      text-transform: uppercase;
    }
    .card.error .card-title { color: #7a3a3a; }
    .row {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      margin-bottom: 4px;
      gap: 8px;
    }
    .label { color: #555; flex-shrink: 0; }
    .value { color: #aaa; text-align: right; word-break: break-all; }
    .value.ok { color: #5a9a6a; }
    .value.warn { color: #c8a040; }
    .value.err { color: #9a4a4a; }
    .divider {
      border: none;
      border-top: 1px solid #1e1e1e;
      margin: 8px 0;
    }
    .footer {
      margin-top: 20px;
      font-size: 0.7rem;
      color: #333;
    }
  </style>
</head>
<body>
  <h1>KEEPSAKE IN EVERY HAIR ~ MIGRATION</h1>
  <p class="subtitle">refreshed {{ now_kst }} KST &nbsp;|&nbsp; auto-refresh 30s</p>
  <div class="grid">
    {% for lens_name, data in lenses.items() %}
    <div class="card {% if data.error %}error{% endif %}">
      <div class="card-title">{{ lens_name.replace('_', ' ') }}</div>
      {% if data.error %}
        <div class="row">
          <span class="label">status</span>
          <span class="value err">unreachable</span>
        </div>
        <div class="row">
          <span class="label">host</span>
          <span class="value">{{ data.host }}</span>
        </div>
        <div class="row">
          <span class="label">error</span>
          <span class="value err">{{ data.error }}</span>
        </div>
      {% else %}
        <div class="row">
          <span class="label">last training</span>
          <span class="value">{{ data.training.last_training or '—' }}</span>
        </div>
        <div class="row">
          <span class="label">total trainings</span>
          <span class="value">{{ data.training.total_training_count }}</span>
        </div>
        <div class="row">
          <span class="label">checkpoint</span>
          <span class="value">{{ data.adapter.latest_checkpoint.split('/')[-1] if data.adapter.latest_checkpoint else '—' }}</span>
        </div>
        <hr class="divider">
        <div class="row">
          <span class="label">CPU</span>
          <span class="value {% if data.system.cpu_percent > 80 %}warn{% else %}ok{% endif %}">
            {{ '%.1f'|format(data.system.cpu_percent) }}%
          </span>
        </div>
        <div class="row">
          <span class="label">memory</span>
          <span class="value {% if data.system.memory_percent > 85 %}warn{% else %}ok{% endif %}">
            {{ '%.1f'|format(data.system.memory_percent) }}%
          </span>
        </div>
        <div class="row">
          <span class="label">disk</span>
          <span class="value {% if data.system.disk_percent > 85 %}warn{% else %}ok{% endif %}">
            {{ '%.1f'|format(data.system.disk_percent) }}%
          </span>
        </div>
        {% if data.system.cpu_temp is not none %}
        <div class="row">
          <span class="label">temp</span>
          <span class="value {% if data.system.cpu_temp > 80 %}warn{% else %}ok{% endif %}">
            {{ '%.1f'|format(data.system.cpu_temp) }}°C
          </span>
        </div>
        {% endif %}
        {% if data.drift %}
        <hr class="divider">
        <div class="row">
          <span class="label">drift</span>
          <span class="value">{{ '%.4f'|format(data.drift.total_norm_drift) }}</span>
        </div>
        {% endif %}
      {% endif %}
    </div>
    {% endfor %}
  </div>
  <p class="footer">Sangjun Yoo — Keepsake in Every Hair ~ Migration, 2026</p>
</body>
</html>"""

app = Flask(__name__)


@app.route("/")
def dashboard():
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    lenses = {}
    for lens_name, host in PI_HOSTS.items():
        url = f"http://{host}/status"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            data["host"] = host
            data["error"] = None
            lenses[lens_name] = data
        except Exception as e:
            lenses[lens_name] = {
                "host": host,
                "error": str(e),
                "training": {},
                "adapter": {},
                "system": {},
                "drift": None,
            }

    return render_template_string(DASHBOARD_TEMPLATE, lenses=lenses, now_kst=now_kst)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
