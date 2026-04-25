import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from flask import Flask, render_template_string, request, redirect, jsonify as flask_jsonify

from monitoring.auth import URL_PREFIX, SESSION_SECRET
from monitoring.health import (
    get_health_status, load_runtime_state, write_runtime_state, load_token_usage,
)

_FILE_DIR = Path(__file__).resolve().parent
ARTWORK_ROOT = _FILE_DIR.parent.parent / "artwork"
HELPER_ROOT = _FILE_DIR.parent
RUNTIME_STATE_DIR = ARTWORK_ROOT / "runtime_state"

KST = timezone(timedelta(hours=9))

LENS_NAMES = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]

PI_HOSTS = {
    "human_time":           "pi1.local:5000",
    "infrastructure_time":  "pi2.local:5000",
    "environmental_time":   "pi3.local:5000",
    "digital_time":         "pi4.local:5000",
    "liminal_time":         "pi5.local:5000",
    "more_than_human_time": "pi6.local:5000",
}

P = URL_PREFIX

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SESSION_SECRET,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=bool(URL_PREFIX),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")


def _relative_time(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return iso_str


def _fetch_one(lens_name: str) -> dict:
    host = PI_HOSTS[lens_name]
    try:
        resp = requests.get(f"http://{host}/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        data["host"] = host
        data["error"] = None
    except Exception as e:
        data = {"host": host, "error": str(e),
                "training": {}, "adapter": {}, "system": {}, "drift": None}
    return data


def _fetch_all() -> dict:
    return {name: _fetch_one(name) for name in LENS_NAMES}


def _health_score(data: dict) -> int:
    if data.get("error"):
        return 0
    sys_ = data.get("system", {})
    score = 5
    if sys_.get("cpu_percent", 0) > 80:
        score -= 1
    if sys_.get("memory_percent", 0) > 85:
        score -= 1
    if (sys_.get("cpu_temp") or 0) > 80:
        score -= 1
    if sys_.get("disk_percent", 0) > 85:
        score -= 1
    return max(0, score)


def _read_drift_history(lens_name: str, max_entries: int = 50) -> list:
    log_path = HELPER_ROOT / "logs" / f"drift_{lens_name}.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[-max_entries:]


def _read_decisions(lens_name: str, max_entries: int = 20) -> list:
    log_path = ARTWORK_ROOT / "logs" / f"decisions_{lens_name}.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[-max_entries:]


def _make_drift_svg(entries: list, width: int = 320, height: int = 56) -> str:
    if len(entries) < 2:
        return '<p style="color:#444;font-size:0.72rem;margin-top:6px">Not enough drift data yet</p>'
    values = [float(e.get("total_norm_drift", 0)) for e in entries]
    max_val = max(values) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = round(i / (n - 1) * width, 1)
        y = round(height - (v / max_val) * (height - 6) - 3, 1)
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'style="width:100%;height:{height}px;display:block;overflow:visible">'
        f'<polyline points="{poly}" fill="none" stroke="#7a9fcf" stroke-width="1.5"/>'
        f'</svg>'
    )


def _all_runtime_states() -> dict:
    return {name: load_runtime_state(name, ARTWORK_ROOT) for name in LENS_NAMES}


def _all_token_usage() -> dict:
    return {name: load_token_usage(name, ARTWORK_ROOT) for name in LENS_NAMES}

# ── shared CSS ────────────────────────────────────────────────────────────────

_BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #c8c8c8; padding: 16px; max-width: 860px; margin: 0 auto; }
a { color: #7a9fcf; text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1rem; color: #888; letter-spacing: 0.1em; }
h2 { font-size: 0.85rem; color: #666; letter-spacing: 0.05em; margin: 20px 0 10px; }
.sub { font-size: 0.72rem; color: #444; margin: 4px 0 16px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 4px; }
.header-right { font-size: 0.72rem; color: #555; display: flex; gap: 12px; align-items: center; }
.btn { background: #1a1a1a; border: 1px solid #333; color: #888; padding: 5px 12px; cursor: pointer; font-family: inherit; font-size: 0.72rem; border-radius: 2px; min-height: 44px; min-width: 44px; }
.btn:hover { border-color: #555; color: #aaa; }
.btn-danger { background: #2a0a0a; border-color: #5a2a2a; color: #9a5a5a; }
.btn-danger:hover { border-color: #9a4a4a; color: #c87a7a; }
.btn-danger.armed { background: #3a0a0a; border-color: #9a3a3a; color: #c85a5a; }
.card { background: #111; border: 1px solid #222; border-radius: 4px; padding: 14px; margin-bottom: 10px; }
.card.error { border-color: #3a1a1a; background: #120a0a; }
.card.clickable { cursor: pointer; transition: border-color 0.1s; }
.card.clickable:hover { border-color: #7a9fcf44; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-title { font-size: 0.85rem; color: #7a9fcf; letter-spacing: 0.05em; text-transform: uppercase; }
.card.error .card-title { color: #7a3a3a; }
.dots { font-size: 0.75rem; letter-spacing: 2px; }
.row { display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 4px; gap: 8px; }
.label { color: #555; flex-shrink: 0; }
.value { color: #aaa; text-align: right; word-break: break-all; }
.ok { color: #5a9a6a; }
.warn { color: #c8a040; }
.err { color: #9a4a4a; }
.disabled-badge { color: #555; }
.divider { border: none; border-top: 1px solid #1e1e1e; margin: 8px 0; }
.summary { margin-top: 16px; font-size: 0.75rem; color: #555; }
.footer { margin-top: 24px; font-size: 0.68rem; color: #2a2a2a; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 0.7rem; }
.badge.online { background: #0f2a1a; color: #5a9a6a; border: 1px solid #1a4a2a; }
.badge.offline { background: #2a0a0a; color: #9a4a4a; border: 1px solid #4a1a1a; }
table { width: 100%; border-collapse: collapse; font-size: 0.73rem; margin-top: 6px; }
th { color: #444; font-weight: normal; text-align: left; padding: 4px 8px 4px 0; border-bottom: 1px solid #1e1e1e; }
td { color: #888; padding: 4px 8px 4px 0; border-bottom: 1px solid #161616; }
td.act-train { color: #5a9a6a; }
td.act-skip { color: #555; }
.back { font-size: 0.75rem; margin-bottom: 16px; display: inline-block; }
input[type=password], input[type=number] { background: #111; border: 1px solid #333; color: #c8c8c8; padding: 10px 14px; font-family: inherit; font-size: 0.9rem; width: 100%; border-radius: 2px; margin-bottom: 10px; }
input[type=password]:focus, input[type=number]:focus { outline: none; border-color: #7a9fcf; }
.login-box { max-width: 360px; margin: 80px auto; }
.login-box h1 { margin-bottom: 6px; }
.login-box .sub { margin-bottom: 24px; }
.err-msg { color: #9a4a4a; font-size: 0.75rem; margin-bottom: 10px; }
.toggle-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.toggle-label { font-size: 0.78rem; color: #666; }
.toggle-btn { min-width: 56px; font-size: 0.75rem; }
.toggle-btn.on { border-color: #2a5a3a; color: #5a9a6a; }
.toggle-btn.off { border-color: #3a2a2a; color: #6a4a4a; }
.budget-row { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.budget-num { background: #111; border: 1px solid #333; color: #aaa; padding: 6px 10px; font-family: inherit; font-size: 0.8rem; width: 60px; border-radius: 2px; text-align: center; }
.budget-btn { min-height: 36px; min-width: 36px; padding: 4px 8px; font-size: 0.8rem; }
.status-healthy { color: #5a9a6a; }
.status-warning { color: #c8a040; }
.status-error { color: #9a4a4a; }
.status-disabled { color: #555; }
.nav-links { font-size: 0.72rem; display: flex; gap: 12px; margin-bottom: 16px; }
"""

_REFRESH_JS = """
<script>
var _paused = false;
var _timer = null;
function _scheduleRefresh() {
  if (!_paused) _timer = setTimeout(function(){ location.reload(); }, 30000);
}
function togglePause() {
  _paused = !_paused;
  var btn = document.getElementById('pause-btn');
  if (_paused) { clearTimeout(_timer); btn.textContent = 'resume'; }
  else { btn.textContent = 'pause'; _scheduleRefresh(); }
}
document.addEventListener('visibilitychange', function() {
  if (document.hidden) clearTimeout(_timer);
  else if (!_paused) _scheduleRefresh();
});
_scheduleRefresh();
</script>
"""

_ESTOP_JS = """
<script>
var _armed = false;
function armStop() {
  var btn = document.getElementById('estop-btn');
  if (!_armed) {
    _armed = true;
    btn.textContent = 'confirm: halt ALL training';
    btn.classList.add('armed');
    setTimeout(function(){ _armed = false; btn.textContent = 'emergency stop'; btn.classList.remove('armed'); }, 4000);
  } else {
    document.getElementById('estop-form').submit();
  }
}
</script>
"""

# ── templates ─────────────────────────────────────────────────────────────────

_LOGIN_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Keepsake Monitor — Login</title><style>{{ css }}</style></head>
<body><div class="login-box">
<h1>KEEPSAKE LENS MONITOR</h1><p class="sub">Keepsake in Every Hair ~ Migration</p>
{% if error %}<p class="err-msg">{{ error }}</p>{% endif %}
<form method="POST" action="{{ prefix }}/login">
<input type="password" name="password" placeholder="password" autofocus>
<button type="submit" class="btn" style="width:100%;min-height:44px;font-size:0.85rem">Enter</button>
</form></div></body></html>"""

_DASHBOARD_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Keepsake Monitor</title><style>{{ css }}</style></head>
<body>
<div class="header"><h1>KEEPSAKE LENS MONITOR</h1>
<div class="header-right">
<a href="{{ prefix }}/control/" class="btn">control</a>
<button id="pause-btn" class="btn" onclick="togglePause()">pause</button>
</div></div>
<p class="sub">{{ now_kst }} &nbsp;·&nbsp; auto-refresh 30s</p>
{% for lens_name in lens_names %}
{% set data = lenses[lens_name] %}{% set score = scores[lens_name] %}{% set hs = health[lens_name] %}
<a href="{{ prefix }}/lens/{{ lens_name }}" style="text-decoration:none;display:block">
<div class="card {% if data.error %}error{% else %}clickable{% endif %}">
<div class="card-header">
<span class="card-title">{{ lens_name.replace('_',' ') }}</span>
{% if hs == 'disabled' %}<span class="status-disabled">◌ disabled</span>
{% elif data.error %}<span class="dots err">○○○○○</span>
{% else %}<span class="dots" style="color:{% if score >= 4 %}#5a9a6a{% elif score >= 2 %}#c8a040{% else %}#9a4a4a{% endif %}">{{ '●' * score }}{{ '○' * (5-score) }}</span>{% endif %}
</div>
{% if data.error %}<div class="row"><span class="label">status</span><span class="value err">unreachable</span></div>
{% else %}<div class="row"><span class="label">trainings</span><span class="value">{{ data.training.total_training_count }}</span></div>
<div class="row"><span class="label">last training</span><span class="value">{{ rel_times[lens_name] }}</span></div>
{% if data.drift %}<div class="row"><span class="label">drift</span><span class="value">{{ '%.4f'|format(data.drift.total_norm_drift) }}</span></div>{% endif %}
<div class="row" style="margin-top:6px">
<span class="label">cpu</span><span class="value {% if data.system.cpu_percent>80 %}warn{% else %}ok{% endif %}">{{ '%.0f'|format(data.system.cpu_percent) }}%</span>
<span class="label">mem</span><span class="value {% if data.system.memory_percent>85 %}warn{% else %}ok{% endif %}">{{ '%.0f'|format(data.system.memory_percent) }}%</span>
{% if data.system.cpu_temp %}<span class="label">temp</span><span class="value {% if data.system.cpu_temp>80 %}warn{% else %}ok{% endif %}">{{ '%.0f'|format(data.system.cpu_temp) }}°C</span>{% endif %}
</div>{% endif %}
</div></div></a>
{% endfor %}
<p class="summary">{{ n_online }}/{{ n_total }} lenses online{% if n_online==n_total %} · no alerts{% endif %}</p>
<p class="footer">Sangjun Yoo — Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js }}
</body></html>"""

_CONTROL_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Keepsake Control Panel</title><style>{{ css }}</style></head>
<body>
<a class="back" href="{{ prefix }}/">← dashboard</a>
<div class="header"><h1>KEEPSAKE — REMOTE CONTROL</h1>
<div class="header-right">
<button id="pause-btn" class="btn" onclick="togglePause()">pause</button>
</div></div>
<p class="sub">{{ now_kst }} &nbsp;·&nbsp; changes take effect within next cycle</p>

<div class="card" style="border-color:#3a1a1a;margin-bottom:20px">
<div class="card-header"><span class="card-title" style="color:#7a3a3a">EMERGENCY STOP</span></div>
<p style="font-size:0.75rem;color:#555;margin-bottom:10px">Halts training on all 6 lenses. Reversible via individual toggles.</p>
<form id="estop-form" method="POST" action="{{ prefix }}/api/emergency_stop">
<button type="button" id="estop-btn" class="btn btn-danger" onclick="armStop()" style="width:100%;min-height:48px">emergency stop</button>
</form></div>

{% for lens_name in lens_names %}
{% set rs = runtime_states[lens_name] %}{% set enabled = rs.training_enabled if rs else true %}
{% set budget = rs.daily_token_budget if rs else 50 %}{% set used = token_usage[lens_name] %}
{% set hs = health[lens_name] %}
<div class="card">
<div class="card-header">
<span class="card-title">{{ lens_name.replace('_',' ') }}</span>
<span class="status-{{ hs }}">{% if hs=='healthy' %}● healthy{% elif hs=='warning' %}▲ warning{% elif hs=='error' %}✕ error{% else %}◌ disabled{% endif %}</span>
</div>
<div class="toggle-row">
<span class="toggle-label">auto-training</span>
<form method="POST" action="{{ prefix }}/lens/{{ lens_name }}/toggle" style="display:inline">
<button type="submit" class="btn toggle-btn {% if enabled %}on{% else %}off{% endif %}" style="min-height:44px">
{% if enabled %}ON{% else %}OFF{% endif %}</button>
</form></div>
<div class="budget-row">
<span class="label" style="font-size:0.75rem;min-width:80px">token budget</span>
<form method="POST" action="{{ prefix }}/lens/{{ lens_name }}/budget" style="display:flex;gap:6px;align-items:center">
<button type="submit" name="action" value="minus" class="btn budget-btn">-5</button>
<input type="number" name="budget" value="{{ budget }}" min="0" max="500" class="budget-num" readonly>
<button type="submit" name="action" value="plus" class="btn budget-btn">+5</button>
</form>
<span style="font-size:0.72rem;color:#444;margin-left:8px">used: {{ used }}</span>
</div>
</div>
{% endfor %}

<p class="footer">Sangjun Yoo — Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js }}{{ estop_js }}
</body></html>"""

_DETAIL_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ lens_name.replace('_',' ') }} — Keepsake Monitor</title><style>{{ css }}</style></head>
<body>
<a class="back" href="{{ prefix }}/">← dashboard</a>
<div class="header"><h1>{{ lens_name.replace('_',' ').upper() }}</h1>
<span class="badge {% if not data.error %}online{% else %}offline{% endif %}">{% if not data.error %}online{% else %}offline{% endif %}</span>
</div>
<p class="sub">Pi {{ pi_id }} &nbsp;·&nbsp; {{ now_kst }}</p>
{% if data.error %}
<div class="card error"><div class="row"><span class="label">error</span><span class="value err">{{ data.error }}</span></div>
<div class="row"><span class="label">host</span><span class="value">{{ data.host }}</span></div></div>
{% else %}
<h2>SYSTEM</h2><div class="card">
<div class="row"><span class="label">CPU</span><span class="value {% if data.system.cpu_percent>80 %}warn{% else %}ok{% endif %}">{{ '%.1f'|format(data.system.cpu_percent) }}%</span></div>
<div class="row"><span class="label">memory</span><span class="value {% if data.system.memory_percent>85 %}warn{% else %}ok{% endif %}">{{ '%.1f'|format(data.system.memory_percent) }}%</span></div>
<div class="row"><span class="label">disk</span><span class="value {% if data.system.disk_percent>85 %}warn{% else %}ok{% endif %}">{{ '%.1f'|format(data.system.disk_percent) }}%</span></div>
{% if data.system.cpu_temp %}<div class="row"><span class="label">temp</span><span class="value {% if data.system.cpu_temp>80 %}warn{% else %}ok{% endif %}">{{ '%.1f'|format(data.system.cpu_temp) }}°C</span></div>{% endif %}
</div>
<h2>TRAINING</h2><div class="card">
<div class="row"><span class="label">total sessions</span><span class="value">{{ data.training.total_training_count }}</span></div>
<div class="row"><span class="label">last training</span><span class="value">{{ data.training.last_training or '—' }}</span></div>
<div class="row"><span class="label">checkpoints</span><span class="value">{{ data.adapter.total_checkpoints }}</span></div>
<div class="row"><span class="label">latest</span><span class="value" style="font-size:0.68rem">{{ data.adapter.latest_checkpoint.split('/')[-1] if data.adapter.latest_checkpoint else '—' }}</span></div>
</div>
<h2>DRIFT</h2><div class="card">
{% if data.drift %}<div class="row"><span class="label">latest</span><span class="value">{{ '%.4f'|format(data.drift.total_norm_drift) }}</span></div>
<div class="row"><span class="label">measured</span><span class="value" style="font-size:0.68rem">{{ data.drift.measured_at }}</span></div>{% else %}
<div class="row"><span class="label">drift</span><span class="value">no data yet</span></div>{% endif %}
{{ drift_svg }}
{% if drift_history %}<hr class="divider"><table><tr><th>measured at</th><th>norm drift</th></tr>
{% for e in drift_history[-10:]|reverse %}<tr><td>{{ e.measured_at[:19] }}</td><td>{{ '%.4f'|format(e.total_norm_drift) }}</td></tr>{% endfor %}
</table>{% endif %}</div>
{% if decisions %}<h2>RECENT DECISIONS (last {{ decisions|length }})</h2><div class="card">
<table><tr><th>time</th><th>action</th><th>reason</th></tr>
{% for d in decisions|reverse %}<tr>
<td>{{ d.timestamp[:16] }}</td>
<td class="{% if d.action=='train' %}act-train{% else %}act-skip{% endif %}">{{ d.action }}</td>
<td style="color:#555;font-size:0.68rem">{{ d.get('reason', d.get('result',{}).get('status','')) }}</td>
</tr>{% endfor %}</table></div>{% endif %}
{% endif %}
<p class="footer">Sangjun Yoo — Keepsake in Every Hair ~ Migration, 2026</p>{{ refresh_js }}
</body></html>"""

# ── routes ────────────────────────────────────────────────────────────────────

@app.route(f"{P}/", strict_slashes=False)
def dashboard_home():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    scores = {n: _health_score(d) for n, d in lenses.items()}
    health = {
        n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n])
        for n in LENS_NAMES
    }
    rel_times = {
        n: _relative_time(lenses[n].get("training", {}).get("last_training"))
        for n in LENS_NAMES
    }
    n_online = sum(1 for d in lenses.values() if not d.get("error"))
    return render_template_string(
        _DASHBOARD_TMPL,
        css=_BASE_CSS, refresh_js=_REFRESH_JS, prefix=P,
        lens_names=LENS_NAMES, lenses=lenses, scores=scores, health=health,
        rel_times=rel_times, now_kst=_now_kst(),
        n_online=n_online, n_total=len(LENS_NAMES),
    )


@app.route(f"{P}/lens/<lens_name>")
def lens_detail(lens_name: str):
    if lens_name not in PI_HOSTS:
        return f"Unknown lens: {lens_name}", 404
    data = _fetch_one(lens_name)
    drift_history = _read_drift_history(lens_name)
    drift_svg = _make_drift_svg(drift_history)
    decisions = _read_decisions(lens_name)
    pi_id = LENS_NAMES.index(lens_name) + 1
    return render_template_string(
        _DETAIL_TMPL,
        css=_BASE_CSS, refresh_js=_REFRESH_JS, prefix=P,
        lens_name=lens_name, data=data, pi_id=pi_id, now_kst=_now_kst(),
        drift_history=drift_history, drift_svg=drift_svg, decisions=decisions,
    )


@app.route(f"{P}/control/")
@app.route(f"{P}/control")
def control_panel():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    health = {
        n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n])
        for n in LENS_NAMES
    }
    return render_template_string(
        _CONTROL_TMPL,
        css=_BASE_CSS, refresh_js=_REFRESH_JS, estop_js=_ESTOP_JS, prefix=P,
        lens_names=LENS_NAMES, runtime_states=runtime_states,
        token_usage=token_usage, health=health,
        now_kst=_now_kst(),
    )


@app.route(f"{P}/lens/<lens_name>/toggle", methods=["POST"])
def toggle_training(lens_name: str):
    if lens_name not in LENS_NAMES:
        return "Unknown lens", 404
    state = load_runtime_state(lens_name, ARTWORK_ROOT) or {}
    current = state.get("training_enabled", True)
    write_runtime_state(lens_name, ARTWORK_ROOT, {"training_enabled": not current})
    return redirect(f"{P}/control/")


@app.route(f"{P}/lens/<lens_name>/budget", methods=["POST"])
def set_budget(lens_name: str):
    if lens_name not in LENS_NAMES:
        return "Unknown lens", 404
    state = load_runtime_state(lens_name, ARTWORK_ROOT) or {}
    current = int(state.get("daily_token_budget", 50))
    action = request.form.get("action", "")
    try:
        manual = int(request.form.get("budget", current))
    except ValueError:
        manual = current
    if action == "plus":
        new_budget = min(500, current + 5)
    elif action == "minus":
        new_budget = max(0, current - 5)
    else:
        new_budget = max(0, min(500, manual))
    write_runtime_state(lens_name, ARTWORK_ROOT, {"daily_token_budget": new_budget})
    return redirect(f"{P}/control/")


@app.route(f"{P}/api/emergency_stop", methods=["POST"])
def emergency_stop():
    for lens_name in LENS_NAMES:
        write_runtime_state(lens_name, ARTWORK_ROOT, {"training_enabled": False})
    return redirect(f"{P}/control/")


@app.route(f"{P}/api/status")
def api_status():
    lenses = _fetch_all()
    n_online = sum(1 for d in lenses.values() if not d.get("error"))
    return flask_jsonify({
        "timestamp": datetime.now(KST).isoformat(),
        "lenses": lenses,
        "summary": {
            "total_lenses": len(LENS_NAMES),
            "online": n_online,
            "offline": len(LENS_NAMES) - n_online,
            "alerts": [n for n, d in lenses.items() if d.get("error") or _health_score(d) < 3],
        },
    })


@app.route(f"{P}/api/health")
def api_health():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    health = {
        n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n])
        for n in LENS_NAMES
    }
    return flask_jsonify({
        "timestamp": datetime.now(KST).isoformat(),
        "health": health,
        "summary": {s: sum(1 for v in health.values() if v == s)
                    for s in ("healthy", "warning", "error", "disabled")},
    })


@app.route(f"{P}/api/budget")
def api_budget():
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    result = {}
    for n in LENS_NAMES:
        rs = runtime_states[n] or {}
        result[n] = {
            "daily_budget": rs.get("daily_token_budget", 50),
            "used_today": token_usage[n],
            "remaining": max(0, rs.get("daily_token_budget", 50) - token_usage[n]),
        }
    return flask_jsonify({"timestamp": datetime.now(KST).isoformat(), "budgets": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
