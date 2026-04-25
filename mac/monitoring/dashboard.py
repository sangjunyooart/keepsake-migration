"""
Flask dashboard for Mac mini — port 8080, URL prefix /monitor.
Mobile-optimised, dark theme.
"""
import os
import sys
import yaml
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from flask import Flask, render_template_string, request, redirect, session, jsonify

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from mac.monitoring.auth import (
    URL_PREFIX, SESSION_SECRET, AUTH_REQUIRED,
    require_auth, verify_password, check_startup,
)
from mac.monitoring.status_aggregator import StatusAggregator
from mac.monitoring.control_panel import ControlPanel

app = Flask(__name__)
app.secret_key = SESSION_SECRET

_pi_targets: list = []
_aggregator: StatusAggregator | None = None
_control: ControlPanel | None = None


def _load_deps():
    global _pi_targets, _aggregator, _control
    if _pi_targets:
        return
    cfg_path = MAC_ROOT / "config" / "pi_targets.yaml"
    if cfg_path.exists():
        _pi_targets = yaml.safe_load(cfg_path.read_text())["pis"]
    else:
        _pi_targets = []
    _aggregator = StatusAggregator(_pi_targets)
    _control = ControlPanel(MAC_ROOT)


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------

P = URL_PREFIX


@app.route(f"{P}/login", methods=["GET", "POST"], strict_slashes=False)
def login():
    error = ""
    if request.method == "POST":
        if verify_password(request.form.get("password", "")):
            session["authenticated"] = True
            return redirect(f"{P}/")
        error = "Incorrect password"
    return render_template_string(_LOGIN_TPL, prefix=P, error=error, css=_CSS)


@app.route(f"{P}/logout")
def logout():
    session.clear()
    return redirect(f"{P}/login")


# ------------------------------------------------------------------
# Main dashboard
# ------------------------------------------------------------------

@app.route(f"{P}/", strict_slashes=False)
@app.route(f"{P}")
@require_auth
def index():
    _load_deps()
    statuses = _aggregator.fetch_all() if _aggregator else {}
    states = _control.all_states() if _control else {}
    return render_template_string(
        _DASHBOARD_TPL,
        prefix=P,
        statuses=statuses,
        states=states,
        css=_CSS,
        refresh_js=_REFRESH_JS,
    )


@app.route(f"{P}/control", strict_slashes=False)
@require_auth
def control():
    _load_deps()
    states = _control.all_states() if _control else {}
    return render_template_string(
        _CONTROL_TPL,
        prefix=P,
        states=states,
        css=_CSS,
    )


# ------------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------------

@app.route(f"{P}/api/lens/<lens_name>/toggle", methods=["POST"])
@require_auth
def toggle_lens(lens_name):
    _load_deps()
    current = _control.get_state(lens_name)
    new_val = not current.get("training_enabled", True)
    state = _control.set_training_enabled(lens_name, new_val)
    return jsonify(state)


@app.route(f"{P}/api/emergency_stop", methods=["POST"])
@require_auth
def emergency_stop():
    _load_deps()
    result = _control.emergency_stop_all()
    return jsonify(result)


@app.route(f"{P}/api/resume_all", methods=["POST"])
@require_auth
def resume_all():
    _load_deps()
    result = _control.resume_all()
    return jsonify(result)


@app.route(f"{P}/api/status")
@require_auth
def api_status():
    _load_deps()
    return jsonify(_aggregator.fetch_all() if _aggregator else {})


@app.route(f"{P}/api/health")
def api_health():
    return jsonify({"ok": True})


# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #080808; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; font-size: 14px; }
header { padding: 16px 20px; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; }
header h1 { font-size: 16px; font-weight: 500; letter-spacing: 0.05em; color: #aaa; }
header nav a { color: #555; text-decoration: none; margin-left: 16px; font-size: 13px; }
header nav a:hover { color: #aaa; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; padding: 20px; }
.card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 16px; }
.card.offline { opacity: 0.45; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.lens-name { font-weight: 600; font-size: 13px; letter-spacing: 0.03em; }
.badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; }
.badge.healthy { background: #0d2b0d; color: #4caf50; }
.badge.warning { background: #2b1e0d; color: #ff9800; }
.badge.error { background: #2b0d0d; color: #f44336; }
.badge.offline { background: #1a1a1a; color: #555; }
.badge.disabled { background: #1a1a2b; color: #5c6bc0; }
.metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.metric { background: #0a0a0a; border-radius: 4px; padding: 8px; }
.metric-label { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.metric-value { font-size: 16px; font-weight: 600; color: #ccc; }
.metric-value.warn { color: #ff9800; }
.metric-value.crit { color: #f44336; }
.hostname { font-size: 11px; color: #444; margin-top: 10px; }
.training-badge { font-size: 11px; margin-top: 8px; color: #666; }
.training-badge.on { color: #4caf50; }
.training-badge.off { color: #5c6bc0; }
.section { padding: 20px; }
.section h2 { font-size: 13px; color: #555; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; }
.control-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.control-card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 14px; display: flex; justify-content: space-between; align-items: center; }
.toggle-btn { background: #222; border: 1px solid #333; color: #aaa; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.toggle-btn:hover { background: #2a2a2a; }
.estop-btn { background: #2b0d0d; border: 1px solid #5a1a1a; color: #f44336; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; width: 100%; margin-top: 16px; }
.estop-btn:hover { background: #3a1010; }
.resume-btn { background: #0d2b0d; border: 1px solid #1a5a1a; color: #4caf50; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; width: 100%; margin-top: 8px; }
.login-wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.login-box { background: #111; border: 1px solid #222; border-radius: 10px; padding: 32px; width: 320px; }
.login-box h1 { font-size: 15px; color: #aaa; margin-bottom: 24px; text-align: center; }
.login-box input { width: 100%; background: #0a0a0a; border: 1px solid #333; color: #ddd; padding: 10px 12px; border-radius: 6px; font-size: 14px; margin-bottom: 12px; }
.login-box button { width: 100%; background: #1a2b3a; border: 1px solid #2a4a6a; color: #7eb8e8; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.error-msg { color: #f44336; font-size: 12px; margin-bottom: 10px; text-align: center; }
@media (max-width: 420px) { .grid { grid-template-columns: 1fr; padding: 12px; } }
"""

_REFRESH_JS = """
<script>
setTimeout(function(){ location.reload(); }, 30000);
</script>
"""

_LOGIN_TPL = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keepsake — Login</title><style>{{ css | safe }}</style></head>
<body><div class="login-wrap"><div class="login-box">
<h1>Keepsake Monitor</h1>
{% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
<form method="post">
<input type="password" name="password" placeholder="Password" autofocus>
<button type="submit">Enter</button>
</form>
</div></div></body></html>"""

_DASHBOARD_TPL = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keepsake Monitor</title><style>{{ css | safe }}</style></head>
<body>
<header>
  <h1>Keepsake Migration</h1>
  <nav>
    <a href="{{ prefix }}/control">Control</a>
    {% if True %}<a href="{{ prefix }}/logout">Logout</a>{% endif %}
  </nav>
</header>
<div class="grid">
{% for lens, status in statuses.items() %}
{% set reachable = status.get('reachable', False) %}
{% set st = states.get(lens, {}) %}
{% set training_on = st.get('training_enabled', True) %}
<div class="card {% if not reachable %}offline{% endif %}">
  <div class="card-header">
    <span class="lens-name">{{ lens.replace('_', ' ') }}</span>
    {% if not reachable %}
      <span class="badge offline">offline</span>
    {% elif not training_on %}
      <span class="badge disabled">paused</span>
    {% else %}
      <span class="badge healthy">online</span>
    {% endif %}
  </div>
  {% if reachable and status.get('system') %}
  {% set sys = status.system %}
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">CPU</div>
      <div class="metric-value {% if sys.cpu_percent > 85 %}crit{% elif sys.cpu_percent > 60 %}warn{% endif %}">
        {{ "%.0f"|format(sys.cpu_percent) }}%
      </div>
    </div>
    <div class="metric">
      <div class="metric-label">RAM</div>
      <div class="metric-value {% if sys.memory_percent > 85 %}crit{% elif sys.memory_percent > 70 %}warn{% endif %}">
        {{ "%.0f"|format(sys.memory_percent) }}%
      </div>
    </div>
    <div class="metric">
      <div class="metric-label">Disk</div>
      <div class="metric-value {% if sys.disk_percent > 90 %}crit{% elif sys.disk_percent > 75 %}warn{% endif %}">
        {{ "%.0f"|format(sys.disk_percent) }}%
      </div>
    </div>
    <div class="metric">
      <div class="metric-label">Temp</div>
      <div class="metric-value {% if sys.cpu_temp and sys.cpu_temp > 75 %}crit{% elif sys.cpu_temp and sys.cpu_temp > 60 %}warn{% endif %}">
        {% if sys.cpu_temp %}{{ "%.0f"|format(sys.cpu_temp) }}°{% else %}—{% endif %}
      </div>
    </div>
  </div>
  {% if status.get('training') %}
  <div class="hostname">trainings: {{ status.training.total_training_count }}</div>
  {% endif %}
  {% else %}
  <div class="hostname">{{ status.get('error', 'unreachable') }}</div>
  {% endif %}
  <div class="training-badge {% if training_on %}on{% else %}off{% endif %}">
    ● training {% if training_on %}enabled{% else %}paused{% endif %}
  </div>
</div>
{% endfor %}
</div>
{{ refresh_js | safe }}
</body></html>"""

_CONTROL_TPL = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Control — Keepsake</title><style>{{ css | safe }}</style></head>
<body>
<header>
  <h1>Control Panel</h1>
  <nav><a href="{{ prefix }}/">Dashboard</a><a href="{{ prefix }}/logout">Logout</a></nav>
</header>
<div class="section">
  <h2>Training Toggles</h2>
  <div class="control-grid">
  {% for lens, st in states.items() %}
  <div class="control-card">
    <span style="font-size:13px">{{ lens.replace('_',' ') }}</span>
    <button class="toggle-btn" onclick="toggleLens('{{ lens }}', this)">
      {% if st.get('training_enabled', True) %}Pause{% else %}Resume{% endif %}
    </button>
  </div>
  {% endfor %}
  </div>
  <button class="estop-btn" onclick="emergencyStop()">⬛ Emergency Stop All</button>
  <button class="resume-btn" onclick="resumeAll()">▶ Resume All</button>
</div>
<script>
var P = "{{ prefix }}";
function toggleLens(lens, btn) {
  fetch(P+"/api/lens/"+lens+"/toggle", {method:"POST"}).then(r=>r.json()).then(d=>{
    btn.textContent = d.training_enabled ? "Pause" : "Resume";
  });
}
function emergencyStop() {
  if (!confirm("Stop training on ALL lenses?")) return;
  fetch(P+"/api/emergency_stop", {method:"POST"}).then(()=>location.reload());
}
function resumeAll() {
  fetch(P+"/api/resume_all", {method:"POST"}).then(()=>location.reload());
}
</script>
</body></html>"""


if __name__ == "__main__":
    check_startup()
    port = int(os.environ.get("KEEPSAKE_DASHBOARD_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
