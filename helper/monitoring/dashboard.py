import json
from concurrent.futures import ThreadPoolExecutor
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

import os
_tz_name = os.environ.get("KEEPSAKE_TIMEZONE", "America/New_York")
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo(_tz_name)
except Exception:
    _TZ = timezone(timedelta(hours=-5))

LENS_NAMES = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]

# Pi 1 (this machine) is queried via localhost; others via mDNS when deployed
PI_HOSTS = {
    "human_time":           "pi1.local:5000",
    "infrastructure_time":  "pi2.local:5000",
    "environmental_time":   "localhost:5000",
    "digital_time":         "pi4.local:5000",
    "liminal_time":         "pi5.local:5000",
    "more_than_human_time": "pi6.local:5000",
}

P = URL_PREFIX

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SESSION_SECRET,
    SESSION_COOKIE_HTTPONLY=True,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _now_local() -> str:
    now = datetime.now(timezone.utc).astimezone(_TZ)
    return now.strftime("%Y-%m-%d %H:%M %Z")


def _relative_time(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:   return f"{secs}s ago"
        if secs < 3600: return f"{secs // 60}m ago"
        if secs < 86400: return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return iso_str


def _fetch_one(lens_name: str) -> dict:
    host = PI_HOSTS[lens_name]
    try:
        resp = requests.get(f"http://{host}/status", timeout=2)
        resp.raise_for_status()
        data = resp.json()
        data["host"] = host
        data["error"] = None
    except Exception as e:
        data = {"host": host, "error": str(e),
                "training": {}, "adapter": {}, "system": {}, "drift": None}
    return data


def _fetch_all() -> dict:
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_fetch_one, LENS_NAMES))
    return dict(zip(LENS_NAMES, results))


def _health_score(data: dict) -> int:
    if data.get("error"):
        return 0
    sys_ = data.get("system", {})
    score = 5
    if sys_.get("cpu_percent", 0) > 80:    score -= 1
    if sys_.get("memory_percent", 0) > 85: score -= 1
    if (sys_.get("cpu_temp") or 0) > 80:   score -= 1
    if sys_.get("disk_percent", 0) > 85:   score -= 1
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
                try: entries.append(json.loads(line))
                except Exception: pass
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
                try: entries.append(json.loads(line))
                except Exception: pass
    return entries[-max_entries:]


def _make_drift_svg(entries: list, width: int = 300, height: int = 50) -> str:
    if len(entries) < 2:
        return ""
    values = [float(e.get("total_norm_drift", 0)) for e in entries]
    max_val = max(values) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = round(i / (n - 1) * width, 1)
        y = round(height - (v / max_val) * (height - 4) - 2, 1)
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'style="width:100%;height:{height}px;display:block">'
        f'<polyline points="{poly}" fill="none" stroke="#4a7aaf" stroke-width="1.5"/>'
        f'</svg>'
    )


def _all_runtime_states() -> dict:
    return {name: load_runtime_state(name, ARTWORK_ROOT) for name in LENS_NAMES}


def _all_token_usage() -> dict:
    return {name: load_token_usage(name, ARTWORK_ROOT) for name in LENS_NAMES}

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Courier New',monospace;background:#080808;color:#b0b0b0;padding:20px;max-width:800px;margin:0 auto;font-size:14px}
a{color:#5a8abf;text-decoration:none}
a:hover{text-decoration:underline}
h1{font-size:13px;color:#666;letter-spacing:.15em;font-weight:normal}
h2{font-size:11px;color:#444;letter-spacing:.1em;margin:24px 0 10px;text-transform:uppercase}
.sub{font-size:11px;color:#383838;margin:4px 0 20px}
.topbar{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;flex-wrap:wrap;gap:8px}
.topbar-right{display:flex;gap:8px;align-items:center}
.btn{background:#111;border:1px solid #2a2a2a;color:#666;padding:6px 14px;cursor:pointer;font-family:inherit;font-size:11px;border-radius:2px;min-height:36px;display:inline-block}
.btn:hover{border-color:#444;color:#999}
.btn-danger{background:#180808;border-color:#3a1818;color:#7a4040}
.btn-danger:hover{border-color:#6a2a2a;color:#b06060}
.btn-danger.armed{background:#280808;border-color:#8a2a2a;color:#d06060}
.card{background:#0e0e0e;border:1px solid #1c1c1c;border-radius:3px;padding:16px;margin-bottom:8px}
.card.online{border-left:2px solid #2a4a2a}
.card.offline{opacity:.55}
.card.clickable:hover{border-color:#2a3a4a;cursor:pointer}
.lens-name{font-size:13px;color:#7a9abf;letter-spacing:.06em;text-transform:uppercase}
.lens-status{font-size:11px}
.status-ok{color:#4a8a5a}
.status-warn{color:#8a7a3a}
.status-err{color:#6a3a3a}
.status-off{color:#383838}
.status-pending{color:#333}
.card-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;margin-top:8px}
.metric{background:#0a0a0a;padding:8px 10px;border-radius:2px}
.metric-label{font-size:10px;color:#383838;margin-bottom:3px}
.metric-value{font-size:13px;color:#888}
.metric-value.ok{color:#4a7a5a}
.metric-value.warn{color:#8a7030}
.metric-value.err{color:#7a3030}
.divider{border:none;border-top:1px solid #181818;margin:12px 0}
.row{display:flex;justify-content:space-between;font-size:11px;margin-bottom:5px}
.row .lbl{color:#383838}
.row .val{color:#666}
table{width:100%;border-collapse:collapse;font-size:11px;margin-top:6px}
th{color:#333;font-weight:normal;text-align:left;padding:4px 8px 4px 0;border-bottom:1px solid #181818}
td{color:#555;padding:4px 8px 4px 0;border-bottom:1px solid #111}
td.train{color:#4a7a5a}
td.skip{color:#333}
.back{font-size:11px;margin-bottom:16px;display:inline-block;color:#555}
.back:hover{color:#888}
.toggle-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.toggle-lbl{font-size:11px;color:#444}
.toggle-on{border-color:#2a4a2a;color:#4a7a5a}
.toggle-off{border-color:#2a1a1a;color:#4a2a2a}
.budget-row{display:flex;align-items:center;gap:6px;font-size:11px;color:#444}
.budget-num{width:50px;background:#0a0a0a;border:1px solid #222;color:#666;padding:4px 6px;font-family:inherit;font-size:11px;text-align:center;border-radius:2px}
.footer{margin-top:32px;font-size:10px;color:#222;text-align:center}
.summary{font-size:11px;color:#333;margin-top:16px}
@media(max-width:480px){.metrics{grid-template-columns:1fr 1fr}.topbar{flex-direction:column}}
"""

_REFRESH_JS = """<script>
var _p=false,_t=null;
function _sched(){if(!_p)_t=setTimeout(function(){location.reload()},30000)}
function togglePause(){_p=!_p;var b=document.getElementById('pb');if(_p){clearTimeout(_t);b.textContent='resume'}else{b.textContent='pause';_sched()}}
document.addEventListener('visibilitychange',function(){if(document.hidden)clearTimeout(_t);else if(!_p)_sched()});
_sched();
</script>"""

_ESTOP_JS = """<script>
var _armed=false;
function armStop(){var b=document.getElementById('estop-btn');if(!_armed){_armed=true;b.textContent='confirm — halt ALL';b.classList.add('armed');setTimeout(function(){_armed=false;b.textContent='emergency stop';b.classList.remove('armed')},4000)}else{document.getElementById('estop-form').submit()}}
</script>"""

# ── templates ─────────────────────────────────────────────────────────────────

_DASH_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Keepsake Migration — Monitor</title><style>{{ css }}</style></head>
<body>
<div class="topbar">
  <div><h1>KEEPSAKE IN EVERY HAIR &mdash; MIGRATION</h1><p class="sub">{{ now }} &nbsp;&middot;&nbsp; auto-refresh 30s</p></div>
  <div class="topbar-right">
    <a href="{{ P }}/control/" class="btn">control</a>
    <button id="pb" class="btn" onclick="togglePause()">pause</button>
  </div>
</div>

{% for name in lens_names %}
{% set d = lenses[name] %}
{% set hs = health[name] %}
<a href="{{ P }}/lens/{{ name }}" style="text-decoration:none;display:block">
<div class="card {% if not d.error %}online clickable{% else %}offline{% endif %}">
  <div class="card-head">
    <span class="lens-name">{{ name.replace('_', ' ') }}</span>
    <span class="lens-status
      {%- if hs == 'healthy' %} status-ok
      {%- elif hs == 'warning' %} status-warn
      {%- elif hs == 'disabled' %} status-off
      {%- elif not d.error %} status-ok
      {%- else %} status-pending{%- endif %}">
      {%- if not d.error %}online
      {%- elif hs == 'disabled' %}disabled
      {%- else %}pending{%- endif %}
    </span>
  </div>
  {% if not d.error %}
  <div class="metrics">
    <div class="metric"><div class="metric-label">last training</div><div class="metric-value">{{ rel_times[name] }}</div></div>
    <div class="metric"><div class="metric-label">trainings</div><div class="metric-value">{{ d.training.total_training_count or 0 }}</div></div>
    <div class="metric"><div class="metric-label">cpu</div><div class="metric-value {% if d.system.cpu_percent > 80 %}warn{% else %}ok{% endif %}">{{ '%.0f' | format(d.system.cpu_percent) }}%</div></div>
    <div class="metric"><div class="metric-label">memory</div><div class="metric-value {% if d.system.memory_percent > 85 %}warn{% else %}ok{% endif %}">{{ '%.0f' | format(d.system.memory_percent) }}%</div></div>
    {% if d.system.cpu_temp %}<div class="metric"><div class="metric-label">temp</div><div class="metric-value {% if d.system.cpu_temp > 80 %}warn{% else %}ok{% endif %}">{{ '%.0f' | format(d.system.cpu_temp) }}&deg;C</div></div>{% endif %}
    {% if d.drift %}<div class="metric"><div class="metric-label">drift</div><div class="metric-value">{{ '%.4f' | format(d.drift.total_norm_drift) }}</div></div>{% endif %}
  </div>
  {% endif %}
</div></a>
{% endfor %}

<p class="summary">{{ n_online }} / {{ n_total }} lenses online</p>
<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js }}
</body></html>"""

_DETAIL_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ name.replace('_',' ') }} &mdash; Keepsake</title><style>{{ css }}</style></head>
<body>
<a class="back" href="{{ P }}/">&larr; dashboard</a>
<h1>{{ name.replace('_',' ').upper() }}</h1>
<p class="sub">Pi {{ pi_id }} &nbsp;&middot;&nbsp; {{ now }}</p>

{% if d.error %}
<div class="card offline">
  <div class="row"><span class="lbl">status</span><span class="val status-pending">pending deployment</span></div>
  <div class="row"><span class="lbl">host</span><span class="val">{{ d.host }}</span></div>
</div>
{% else %}
<h2>System</h2>
<div class="card online">
  <div class="metrics">
    <div class="metric"><div class="metric-label">cpu</div><div class="metric-value {% if d.system.cpu_percent > 80 %}warn{% else %}ok{% endif %}">{{ '%.1f' | format(d.system.cpu_percent) }}%</div></div>
    <div class="metric"><div class="metric-label">memory</div><div class="metric-value {% if d.system.memory_percent > 85 %}warn{% else %}ok{% endif %}">{{ '%.1f' | format(d.system.memory_percent) }}%</div></div>
    <div class="metric"><div class="metric-label">disk</div><div class="metric-value {% if d.system.disk_percent > 85 %}warn{% else %}ok{% endif %}">{{ '%.1f' | format(d.system.disk_percent) }}%</div></div>
    {% if d.system.cpu_temp %}<div class="metric"><div class="metric-label">temp</div><div class="metric-value {% if d.system.cpu_temp > 80 %}warn{% else %}ok{% endif %}">{{ '%.1f' | format(d.system.cpu_temp) }}&deg;C</div></div>{% endif %}
  </div>
</div>

<h2>Training</h2>
<div class="card online">
  <div class="row"><span class="lbl">total sessions</span><span class="val">{{ d.training.total_training_count or 0 }}</span></div>
  <div class="row"><span class="lbl">last training</span><span class="val">{{ d.training.last_training or '—' }}</span></div>
  <div class="row"><span class="lbl">checkpoints</span><span class="val">{{ d.adapter.total_checkpoints or 0 }}</span></div>
</div>

{% if drift_history %}
<h2>Drift</h2>
<div class="card online">
  {% if d.drift %}
  <div class="row"><span class="lbl">latest</span><span class="val">{{ '%.4f' | format(d.drift.total_norm_drift) }}</span></div>
  {% endif %}
  {{ drift_svg }}
</div>
{% endif %}

{% if decisions %}
<h2>Recent decisions</h2>
<div class="card online">
  <table><tr><th>time</th><th>action</th><th>reason</th></tr>
  {% for dec in decisions | reverse %}
  <tr>
    <td>{{ dec.timestamp[:16] }}</td>
    <td class="{% if dec.action == 'train' %}train{% else %}skip{% endif %}">{{ dec.action }}</td>
    <td style="color:#333;font-size:10px">{{ dec.get('reason', '') }}</td>
  </tr>
  {% endfor %}
  </table>
</div>
{% endif %}
{% endif %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js }}
</body></html>"""

_CONTROL_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Control &mdash; Keepsake</title><style>{{ css }}</style></head>
<body>
<a class="back" href="{{ P }}/">&larr; dashboard</a>
<h1>REMOTE CONTROL</h1>
<p class="sub">{{ now }} &nbsp;&middot;&nbsp; changes take effect within next cycle</p>

<div class="card" style="border-left:2px solid #3a1818;margin-bottom:20px">
  <div class="card-head"><span class="lens-name" style="color:#6a3a3a">Emergency Stop</span></div>
  <p style="font-size:11px;color:#383838;margin-bottom:12px">Halts all 6 lenses. Reversible via individual toggles.</p>
  <form id="estop-form" method="POST" action="{{ P }}/api/emergency_stop">
    <button type="button" id="estop-btn" class="btn btn-danger" onclick="armStop()" style="width:100%;min-height:44px">emergency stop</button>
  </form>
</div>

{% for name in lens_names %}
{% set rs = runtime_states[name] or {} %}
{% set enabled = rs.get('training_enabled', true) %}
{% set budget = rs.get('daily_token_budget', 50) %}
{% set used = token_usage[name] %}
{% set hs = health[name] %}
<div class="card">
  <div class="card-head">
    <span class="lens-name">{{ name.replace('_',' ') }}</span>
    <span class="lens-status {% if hs == 'healthy' %}status-ok{% elif hs == 'warning' %}status-warn{% elif hs == 'disabled' %}status-off{% else %}status-pending{% endif %}">{{ hs }}</span>
  </div>
  <div class="toggle-row">
    <span class="toggle-lbl">auto-training</span>
    <form method="POST" action="{{ P }}/lens/{{ name }}/toggle" style="display:inline">
      <button type="submit" class="btn {% if enabled %}toggle-on{% else %}toggle-off{% endif %}" style="min-height:40px;min-width:60px">{% if enabled %}ON{% else %}OFF{% endif %}</button>
    </form>
  </div>
  <div class="budget-row">
    <span>token budget</span>
    <form method="POST" action="{{ P }}/lens/{{ name }}/budget" style="display:flex;gap:4px;align-items:center;margin-left:8px">
      <button type="submit" name="action" value="minus" class="btn" style="min-height:36px;padding:4px 10px">&minus;5</button>
      <input type="number" name="budget" value="{{ budget }}" min="0" max="500" class="budget-num" readonly>
      <button type="submit" name="action" value="plus" class="btn" style="min-height:36px;padding:4px 10px">+5</button>
    </form>
    <span style="margin-left:10px;color:#333">{{ used }} used today</span>
  </div>
</div>
{% endfor %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js }}{{ estop_js }}
</body></html>"""

# ── routes ────────────────────────────────────────────────────────────────────

def _render(tmpl, **kw):
    return render_template_string(tmpl, css=_CSS, refresh_js=_REFRESH_JS,
                                  P=P, now=_now_local(), **kw)


@app.route(f"{P}/", strict_slashes=False)
def dashboard_home():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    health = {n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n]) for n in LENS_NAMES}
    rel_times = {n: _relative_time(lenses[n].get("training", {}).get("last_training")) for n in LENS_NAMES}
    n_online = sum(1 for d in lenses.values() if not d.get("error"))
    return _render(_DASH_TMPL, lens_names=LENS_NAMES, lenses=lenses,
                   health=health, rel_times=rel_times,
                   n_online=n_online, n_total=len(LENS_NAMES))


@app.route(f"{P}/lens/<lens_name>")
def lens_detail(lens_name: str):
    if lens_name not in PI_HOSTS:
        return "Unknown lens", 404
    d = _fetch_one(lens_name)
    drift_history = _read_drift_history(lens_name)
    decisions = _read_decisions(lens_name)
    pi_id = LENS_NAMES.index(lens_name) + 1
    return _render(_DETAIL_TMPL, name=lens_name, d=d, pi_id=pi_id,
                   drift_history=drift_history,
                   drift_svg=_make_drift_svg(drift_history),
                   decisions=decisions)


@app.route(f"{P}/control/")
@app.route(f"{P}/control")
def control_panel():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    health = {n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n]) for n in LENS_NAMES}
    return _render(_CONTROL_TMPL, lens_names=LENS_NAMES,
                   runtime_states=runtime_states, token_usage=token_usage,
                   health=health, estop_js=_ESTOP_JS)


@app.route(f"{P}/lens/<lens_name>/toggle", methods=["POST"])
def toggle_training(lens_name: str):
    if lens_name not in LENS_NAMES:
        return "Unknown lens", 404
    state = load_runtime_state(lens_name, ARTWORK_ROOT) or {}
    write_runtime_state(lens_name, ARTWORK_ROOT, {"training_enabled": not state.get("training_enabled", True)})
    return redirect(f"{P}/control/")


@app.route(f"{P}/lens/<lens_name>/budget", methods=["POST"])
def set_budget(lens_name: str):
    if lens_name not in LENS_NAMES:
        return "Unknown lens", 404
    state = load_runtime_state(lens_name, ARTWORK_ROOT) or {}
    current = int(state.get("daily_token_budget", 50))
    action = request.form.get("action", "")
    if action == "plus":    new_budget = min(500, current + 5)
    elif action == "minus": new_budget = max(0, current - 5)
    else:
        try:    new_budget = max(0, min(500, int(request.form.get("budget", current))))
        except: new_budget = current
    write_runtime_state(lens_name, ARTWORK_ROOT, {"daily_token_budget": new_budget})
    return redirect(f"{P}/control/")


@app.route(f"{P}/api/emergency_stop", methods=["POST"])
def emergency_stop():
    for name in LENS_NAMES:
        write_runtime_state(name, ARTWORK_ROOT, {"training_enabled": False})
    return redirect(f"{P}/control/")


@app.route(f"{P}/api/status")
def api_status():
    lenses = _fetch_all()
    n_online = sum(1 for d in lenses.values() if not d.get("error"))
    return flask_jsonify({"timestamp": _now_local(), "lenses": lenses,
                          "summary": {"online": n_online, "offline": len(LENS_NAMES) - n_online}})


@app.route(f"{P}/api/health")
def api_health():
    lenses = _fetch_all()
    rs = _all_runtime_states()
    tu = _all_token_usage()
    health = {n: get_health_status(n, lenses[n], rs[n], tu[n]) for n in LENS_NAMES}
    return flask_jsonify({"timestamp": _now_local(), "health": health})


@app.route(f"{P}/api/budget")
def api_budget():
    rs = _all_runtime_states()
    tu = _all_token_usage()
    result = {}
    for n in LENS_NAMES:
        s = rs[n] or {}
        b = s.get("daily_token_budget", 50)
        result[n] = {"daily_budget": b, "used_today": tu[n], "remaining": max(0, b - tu[n])}
    return flask_jsonify({"timestamp": _now_local(), "budgets": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
