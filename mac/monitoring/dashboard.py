"""
Keepsake Training Dashboard — Mac mini M4
http://localhost:8080/

Shows per-lens training status, corpus size, adapter versions, Pi connectivity.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import yaml
from flask import Flask, jsonify, redirect, render_template_string, request, session

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from mac.monitoring.auth import (
    SESSION_SECRET, AUTH_REQUIRED,
    require_auth, verify_password, check_startup,
)
from mac.monitoring.status_aggregator import StatusAggregator
from mac.monitoring.control_panel import ControlPanel, ALL_LENSES

app = Flask(__name__)
app.secret_key = SESSION_SECRET

LENS_ORDER = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]

_aggregator = None
_control = None
_pi_targets = []


def _deps():
    global _aggregator, _control, _pi_targets
    if _aggregator:
        return
    cfg = MAC_ROOT / "config" / "pi_targets.yaml"
    _pi_targets = yaml.safe_load(cfg.read_text())["pis"] if cfg.exists() else []
    _aggregator = StatusAggregator(_pi_targets)
    _control = ControlPanel(MAC_ROOT)


# ── auth ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if verify_password(request.form.get("password", "")):
            session["authenticated"] = True
            return redirect("/")
        err = "Incorrect password"
    return render_template_string(_LOGIN, error=err, css=_CSS)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── pages ─────────────────────────────────────────────────────────────────

@app.route("/")
@require_auth
def index():
    _deps()
    pi_status = _aggregator.fetch_all()
    states = _control.all_states()
    lenses = [_lens_data(ln, pi_status, states) for ln in LENS_ORDER]
    mac_sys = _mac_system()
    return render_template_string(
        _DASH, lenses=lenses, mac_sys=mac_sys,
        css=_CSS, refresh_js=_REFRESH_JS,
    )


@app.route("/control")
@require_auth
def control():
    _deps()
    states = _control.all_states()
    return render_template_string(_CONTROL, states=states, css=_CSS)


# ── api ───────────────────────────────────────────────────────────────────

@app.route("/api/lens/<lens>/toggle", methods=["POST"])
@require_auth
def toggle(lens):
    _deps()
    cur = _control.get_state(lens)
    s = _control.set_training_enabled(lens, not cur.get("training_enabled", True))
    return jsonify(s)


@app.route("/api/emergency_stop", methods=["POST"])
@require_auth
def estop():
    _deps()
    return jsonify(_control.emergency_stop_all())


@app.route("/api/resume_all", methods=["POST"])
@require_auth
def resume():
    _deps()
    return jsonify(_control.resume_all())


@app.route("/api/status")
@require_auth
def api_status():
    _deps()
    pi = _aggregator.fetch_all()
    states = _control.all_states()
    return jsonify({ln: _lens_data(ln, pi, states) for ln in LENS_ORDER})


@app.route("/health")
def health():
    return jsonify({"ok": True})


# ── data helpers ──────────────────────────────────────────────────────────

def _lens_data(lens: str, pi_status: dict, states: dict) -> dict:
    state = states.get(lens, {})
    pi = pi_status.get(lens, {})
    return {
        "name": lens,
        "label": lens.replace("_", " "),
        "training_enabled": state.get("training_enabled", True),
        "corpus_chunks": _count_chunks(lens),
        "last_training": _last_training(lens),
        "adapter_version": _adapter_version(lens),
        "pi_reachable": pi.get("reachable", False),
        "pi_cpu": pi.get("system", {}).get("cpu_percent"),
        "pi_mem": pi.get("system", {}).get("memory_percent"),
        "pi_temp": pi.get("system", {}).get("cpu_temp"),
        "pi_disk": pi.get("system", {}).get("disk_percent"),
        "pi_error": pi.get("error", ""),
    }


def _count_chunks(lens: str) -> int:
    d = MAC_ROOT / "corpus" / "processed" / lens
    if not d.exists():
        return 0
    return len(list(d.glob("*.txt")))


def _last_training(lens: str) -> str:
    log = MAC_ROOT / "logs" / f"decisions_{lens}.jsonl"
    if not log.exists():
        return "never"
    last = None
    with open(log) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("action") == "train":
                    last = e.get("timestamp", "")
            except Exception:
                pass
    if not last:
        return "never"
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 3600:
            return f"{diff // 60}m ago"
        if diff < 86400:
            return f"{diff // 3600}h ago"
        return f"{diff // 86400}d ago"
    except Exception:
        return last[:16]


def _adapter_version(lens: str) -> str:
    cur = MAC_ROOT / "adapters" / lens / "current.json"
    if not cur.exists():
        return "none"
    try:
        d = json.loads(cur.read_text())
        ckpt = Path(d.get("path", "")).name
        return ckpt.replace("checkpoint_", "") if ckpt else "none"
    except Exception:
        return "none"


def _mac_system() -> dict:
    try:
        import psutil
        return {
            "cpu": psutil.cpu_percent(interval=0.3),
            "mem": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage(str(MAC_ROOT)).percent,
        }
    except Exception:
        return {}


# ── CSS ───────────────────────────────────────────────────────────────────

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070707;color:#d8d8d8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;font-size:13px}
a{color:inherit;text-decoration:none}
header{padding:14px 20px;border-bottom:1px solid #1c1c1c;display:flex;justify-content:space-between;align-items:center}
header h1{font-size:14px;font-weight:500;letter-spacing:.06em;color:#888}
nav a{color:#444;margin-left:14px;font-size:12px}
nav a:hover{color:#aaa}
.sys-row{display:flex;gap:10px;padding:14px 20px 0;flex-wrap:wrap}
.sys-pill{background:#111;border:1px solid #1c1c1c;border-radius:20px;padding:5px 12px;font-size:11px;color:#555}
.sys-pill span{color:#888;margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px;padding:14px 20px 20px}
.card{background:#0e0e0e;border:1px solid #1c1c1c;border-radius:8px;padding:14px}
.card.offline{opacity:.4}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.lens-name{font-size:12px;font-weight:600;letter-spacing:.03em;text-transform:capitalize}
.badges{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}
.badge{font-size:10px;padding:2px 7px;border-radius:10px;white-space:nowrap}
.b-online{background:#0a2a0a;color:#4caf50}
.b-offline{background:#1a1a1a;color:#444}
.b-paused{background:#1a1a2e;color:#5c6bc0}
.b-training{background:#1a2a1a;color:#66bb6a}
.b-never{background:#1c1c1c;color:#555}
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px}
.m{background:#080808;border-radius:4px;padding:7px 8px}
.m-label{font-size:9px;color:#444;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px}
.m-val{font-size:15px;font-weight:600;color:#bbb}
.m-val.w{color:#ff9800}.m-val.c{color:#f44336}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.mini{background:#080808;border-radius:4px;padding:5px 8px;font-size:11px}
.mini-label{color:#444;font-size:9px;text-transform:uppercase;letter-spacing:.05em}
.mini-val{color:#777;margin-top:1px}
.divider{border:none;border-top:1px solid #161616;margin:8px 0}
.pi-row{display:flex;justify-content:space-between;align-items:center}
.pi-label{font-size:10px;color:#444}
.pi-metrics{display:flex;gap:8px}
.pm{font-size:11px;color:#555}
.pm.w{color:#ff9800}.pm.c{color:#f44336}
.estop{width:100%;background:#1c0808;border:1px solid #4a1010;color:#ef5350;padding:9px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;margin-top:10px}
.estop:hover{background:#2a0a0a}
.resume-btn{width:100%;background:#081c08;border:1px solid #104a10;color:#66bb6a;padding:9px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;margin-top:6px}
.ctrl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px;padding:16px 20px}
.ctrl-card{background:#0e0e0e;border:1px solid #1c1c1c;border-radius:8px;padding:12px;display:flex;justify-content:space-between;align-items:center}
.tbtn{background:#1a1a1a;border:1px solid #2a2a2a;color:#888;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:11px}
.tbtn:hover{background:#222}
.login-wrap{display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:#0e0e0e;border:1px solid #1c1c1c;border-radius:10px;padding:28px;width:300px}
.login-box h1{font-size:14px;color:#888;margin-bottom:20px;text-align:center}
.login-box input{width:100%;background:#080808;border:1px solid #2a2a2a;color:#ccc;padding:9px 11px;border-radius:6px;font-size:13px;margin-bottom:10px}
.login-box button{width:100%;background:#111e2e;border:1px solid #1e3a5a;color:#5b9bd5;padding:9px;border-radius:6px;cursor:pointer;font-size:13px}
.err{color:#ef5350;font-size:11px;margin-bottom:8px;text-align:center}
.section-title{font-size:11px;color:#444;text-transform:uppercase;letter-spacing:.1em;padding:16px 20px 0}
@media(max-width:420px){.grid{grid-template-columns:1fr;padding:10px}}
"""

_REFRESH_JS = "<script>setTimeout(()=>location.reload(),30000)</script>"

# ── templates ─────────────────────────────────────────────────────────────

_LOGIN = """<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Keepsake</title><style>{{ css | safe }}</style></head>
<body><div class=login-wrap><div class=login-box>
<h1>Keepsake Monitor</h1>
{% if error %}<div class=err>{{ error }}</div>{% endif %}
<form method=post>
<input type=password name=password placeholder=Password autofocus>
<button type=submit>Enter</button>
</form></div></div></body></html>"""


_DASH = """<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Keepsake</title><style>{{ css | safe }}</style></head>
<body>
<header>
  <h1>Keepsake Migration</h1>
  <nav>
    <a href=/control>Control</a>
    <a href=/logout>Logout</a>
  </nav>
</header>

{% if mac_sys %}
<div class=sys-row>
  <div class=sys-pill>Mac CPU <span>{{ "%.0f"|format(mac_sys.cpu) }}%</span></div>
  <div class=sys-pill>Mac RAM <span>{{ "%.0f"|format(mac_sys.mem) }}%</span></div>
  <div class=sys-pill>Mac Disk <span>{{ "%.0f"|format(mac_sys.disk) }}%</span></div>
</div>
{% endif %}

<div class=grid>
{% for l in lenses %}
<div class="card {% if not l.pi_reachable %}offline{% endif %}">
  <div class=card-top>
    <div class=lens-name>{{ l.label }}</div>
    <div class=badges>
      {% if l.training_enabled %}
        <span class="badge b-training">training on</span>
      {% else %}
        <span class="badge b-paused">paused</span>
      {% endif %}
      {% if l.pi_reachable %}
        <span class="badge b-online">pi online</span>
      {% else %}
        <span class="badge b-offline">pi offline</span>
      {% endif %}
    </div>
  </div>

  <div class=metrics>
    <div class=m>
      <div class=m-label>Corpus</div>
      <div class="m-val {% if l.corpus_chunks < 10 %}c{% elif l.corpus_chunks < 50 %}w{% endif %}">
        {{ l.corpus_chunks }}
      </div>
    </div>
    <div class=m>
      <div class=m-label>Last trained</div>
      <div class="m-val {% if l.last_training == 'never' %}c{% endif %}" style="font-size:12px;padding-top:2px">
        {{ l.last_training }}
      </div>
    </div>
  </div>

  <div class=row2>
    <div class=mini>
      <div class=mini-label>Adapter</div>
      <div class=mini-val>{{ l.adapter_version }}</div>
    </div>
    <div class=mini>
      <div class=mini-label>Pi temp</div>
      <div class="mini-val {% if l.pi_temp and l.pi_temp > 75 %}c{% elif l.pi_temp and l.pi_temp > 60 %}w{% endif %}">
        {% if l.pi_temp %}{{ "%.0f"|format(l.pi_temp) }}°C{% else %}—{% endif %}
      </div>
    </div>
  </div>

  {% if l.pi_reachable %}
  <hr class=divider>
  <div class=pi-row>
    <span class=pi-label>Pi</span>
    <div class=pi-metrics>
      <span class="pm {% if l.pi_cpu and l.pi_cpu > 85 %}c{% elif l.pi_cpu and l.pi_cpu > 60 %}w{% endif %}">
        CPU {{ "%.0f"|format(l.pi_cpu or 0) }}%
      </span>
      <span class="pm {% if l.pi_mem and l.pi_mem > 85 %}c{% elif l.pi_mem and l.pi_mem > 70 %}w{% endif %}">
        RAM {{ "%.0f"|format(l.pi_mem or 0) }}%
      </span>
      <span class="pm {% if l.pi_disk and l.pi_disk > 90 %}c{% elif l.pi_disk and l.pi_disk > 75 %}w{% endif %}">
        Disk {{ "%.0f"|format(l.pi_disk or 0) }}%
      </span>
    </div>
  </div>
  {% endif %}
</div>
{% endfor %}
</div>
{{ refresh_js | safe }}
</body></html>"""


_CONTROL = """<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Control — Keepsake</title><style>{{ css | safe }}</style></head>
<body>
<header>
  <h1>Control Panel</h1>
  <nav><a href=/>Dashboard</a><a href=/logout>Logout</a></nav>
</header>
<p class=section-title>Training Toggles</p>
<div class=ctrl-grid>
{% for lens, st in states.items() %}
<div class=ctrl-card>
  <span>{{ lens.replace('_',' ') }}</span>
  <button class=tbtn onclick="toggle('{{ lens }}',this)">
    {{ 'Pause' if st.get('training_enabled', True) else 'Resume' }}
  </button>
</div>
{% endfor %}
</div>
<div style="padding:0 20px 20px">
  <button class=estop onclick="estop()">⬛ Emergency Stop All</button>
  <button class=resume-btn onclick="resumeAll()">▶ Resume All</button>
</div>
<script>
function toggle(lens,btn){
  fetch('/api/lens/'+lens+'/toggle',{method:'POST'})
    .then(r=>r.json()).then(d=>{btn.textContent=d.training_enabled?'Pause':'Resume'})
}
function estop(){
  if(!confirm('Stop ALL training?'))return;
  fetch('/api/emergency_stop',{method:'POST'}).then(()=>location.reload())
}
function resumeAll(){
  fetch('/api/resume_all',{method:'POST'}).then(()=>location.reload())
}
</script>
</body></html>"""


if __name__ == "__main__":
    check_startup()
    port = int(os.environ.get("KEEPSAKE_DASHBOARD_PORT", 8080))
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=port, debug=False)
