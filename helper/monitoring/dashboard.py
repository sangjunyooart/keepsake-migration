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
MAC_ROOT = _FILE_DIR.parent.parent / "mac"
CUSTODIAN_STATE = _FILE_DIR.parent / "custodian" / "state"

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


def _load_agent_states() -> dict:
    """Read mac/runtime_state/agent_{lens}.json for all lenses."""
    states = {}
    for lens_name in LENS_NAMES:
        state_path = MAC_ROOT / "runtime_state" / f"agent_{lens_name}.json"
        if state_path.exists():
            try:
                states[lens_name] = json.loads(state_path.read_text())
            except Exception:
                states[lens_name] = {"status": "error", "lens_name": lens_name}
        else:
            states[lens_name] = {"status": "idle", "lens_name": lens_name}
    return states


def _agent_overall_status(states: dict) -> str:
    statuses = [v.get("status", "idle") for v in states.values()]
    if "running" in statuses:
        return "running"
    if "error" in statuses:
        return "error"
    if all(s == "idle" for s in statuses):
        return "idle"
    return "active"


def _load_custodian_state() -> dict | None:
    state_file = CUSTODIAN_STATE / "current.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text())
    except Exception:
        return None


def _count_incidents_today() -> int:
    incidents_file = CUSTODIAN_STATE / "incidents.jsonl"
    if not incidents_file.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    try:
        with incidents_file.open() as f:
            for line in f:
                if today in line:
                    count += 1
    except OSError:
        pass
    return count


def _load_quarantine_items() -> list[dict]:
    quarantine_root = MAC_ROOT / "corpus" / "quarantine"
    if not quarantine_root.exists():
        return []
    items = []
    for qdir in sorted(quarantine_root.iterdir(), reverse=True):
        if not qdir.is_dir():
            continue
        for meta_file in qdir.glob("*.meta.json"):
            try:
                meta = json.loads(meta_file.read_text())
                chunk_file = qdir / meta_file.name.replace(".meta.json", "")
                preview = ""
                if chunk_file.exists():
                    try:
                        preview = chunk_file.read_text(errors="replace")[:300]
                    except OSError:
                        pass
                items.append({
                    "qid": qdir.name,
                    "filename": chunk_file.name,
                    "lens": meta.get("lens", ""),
                    "quarantined_at": meta.get("quarantined_at", ""),
                    "reason": meta.get("reason", ""),
                    "preview": preview,
                    "chunk_exists": chunk_file.exists(),
                })
            except Exception:
                continue
    return items

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
.agent-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;flex-shrink:0}
.agent-dot.idle{background:#222}.agent-dot.running{background:#4a7a8a;animation:pulse 1s infinite}
.agent-dot.complete{background:#2a5a2a}.agent-dot.error{background:#6a2020}.agent-dot.no_corpus{background:#3a2a00}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.agent-row{display:flex;align-items:center;font-size:11px;padding:5px 0;border-bottom:1px solid #111;gap:6px}
.agent-lens{color:#3a5a7a;width:140px;flex-shrink:0;text-transform:uppercase;font-size:10px;letter-spacing:.04em}
.agent-summary{color:#3a3a3a;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.agent-time{color:#2a2a2a;font-size:10px;flex-shrink:0}
.agent-queries{margin-top:4px}
.agent-query-pill{display:inline-block;background:#0a1020;border:1px solid #1a2a3a;color:#2a4a6a;font-size:10px;padding:2px 7px;border-radius:2px;margin:2px}
.cust-pill{display:inline-block;padding:3px 8px;border-radius:2px;font-size:10px;margin:2px;letter-spacing:.04em;text-transform:uppercase}
.cust-pill.info{background:#0a140a;border:1px solid #1a3a1a;color:#3a7a3a}
.cust-pill.warning{background:#14100a;border:1px solid #3a2800;color:#8a6010}
.cust-pill.critical{background:#140000;border:1px solid #4a0000;color:#aa2020}
.cust-pill.unknown{background:#0e0e0e;border:1px solid #1c1c1c;color:#333}
.cust-overall-info{color:#3a7a3a}.cust-overall-warn{color:#8a6010}.cust-overall-crit{color:#aa2020}
.qitem{background:#0a0a0a;border:1px solid #1a1a1a;border-radius:2px;padding:12px;margin-bottom:8px}
.qitem-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.qactions{display:flex;gap:6px}
.btn-restore{border-color:#2a4a2a;color:#4a7a5a}
.btn-restore:hover{border-color:#3a6a3a;color:#6aaa6a}
.incident-row{display:flex;gap:8px;font-size:11px;padding:6px 0;border-bottom:1px solid #111;align-items:flex-start}
.inc-sev-warning{color:#8a6010}.inc-sev-critical{color:#aa2020}.inc-sev-info{color:#3a7a3a}
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
<title>Keepsake Migration — Monitor</title><style>{{ css | safe }}</style></head>
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

<div class="card" style="margin-top:20px;border-color:#0e1a2a">
  <div class="card-head">
    <span style="font-size:11px;color:#2a3a4a;letter-spacing:.1em;text-transform:uppercase">Agent Curation</span>
    <a href="{{ P }}/agents/" style="font-size:10px;color:#2a3a4a">details &rarr;</a>
  </div>
  {% set overall = agent_overall %}
  <div class="row" style="margin-bottom:8px">
    <span class="lbl">model</span>
    <span class="val" style="color:#2a3a4a">{{ agent_model }}</span>
  </div>
  {% for lens_name in lens_names %}
  {% set ag = agent_states[lens_name] %}
  <div class="agent-row">
    <span class="agent-dot {{ ag.status }}"></span>
    <span class="agent-lens">{{ lens_name.replace('_',' ') }}</span>
    <span class="agent-summary" title="{{ ag.get('assessment','') }}">
      {%- if ag.status == 'complete' %}{{ ag.get('assessment','')[:70] }}
      {%- elif ag.status == 'running' %}running...
      {%- elif ag.status == 'no_corpus' %}no corpus yet
      {%- elif ag.status == 'error' %}{{ ag.get('error','error')[:50] }}
      {%- else %}idle{%- endif %}
    </span>
    <span class="agent-time">
      {%- if ag.get('timestamp') %}{{ rel_times_agent[lens_name] }}{%- endif %}
    </span>
  </div>
  {% endfor %}
</div>

<div class="card" style="margin-top:8px;border-color:#1a1a1a">
  <div class="card-head">
    <span style="font-size:11px;color:#3a3a3a;letter-spacing:.1em;text-transform:uppercase">Custodian</span>
    <a href="{{ P }}/custodian/" style="font-size:10px;color:#2a2a2a">details &rarr;</a>
  </div>
  {% if custodian_state %}
  <div style="margin-bottom:10px">
    {% for check_name, r in custodian_state.checks.items() %}
    <a href="{{ P }}/custodian/" style="text-decoration:none">
    <span class="cust-pill {{ r.severity }}" title="{{ r.summary }}">{{ check_name.replace('_',' ') }}</span>
    </a>
    {% endfor %}
  </div>
  <div class="row">
    <span class="lbl">overall</span>
    <span class="val cust-overall-{{ custodian_state.overall_severity[:4] }}">{{ custodian_state.overall_severity }}</span>
  </div>
  <div class="row">
    <span class="lbl">last check</span>
    <span class="val">{{ cust_rel_time }}</span>
  </div>
  {% if cust_incidents_today > 0 %}
  <div class="row">
    <span class="lbl">incidents today</span>
    <span class="val status-warn">{{ cust_incidents_today }}</span>
  </div>
  {% endif %}
  {% else %}
  <p style="font-size:11px;color:#2a2a2a">Not running &mdash; start com.keepsake.custodian</p>
  {% endif %}
</div>

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js | safe }}
</body></html>"""

_DETAIL_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ name.replace('_',' ') }} &mdash; Keepsake</title><style>{{ css | safe }}</style></head>
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
  {{ drift_svg | safe }}
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
{{ refresh_js | safe }}
</body></html>"""

_CONTROL_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Control &mdash; Keepsake</title><style>{{ css | safe }}</style></head>
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
{{ refresh_js | safe }}{{ estop_js | safe }}
</body></html>"""

# ── routes ────────────────────────────────────────────────────────────────────

def _render(tmpl, **kw):
    return render_template_string(tmpl, css=_CSS, refresh_js=_REFRESH_JS,
                                  P=P, now=_now_local(), **kw)


def _system_agent_config() -> dict:
    try:
        import yaml as _yaml
        cfg = _yaml.safe_load((MAC_ROOT / "config" / "system_config.yaml").read_text())
        return cfg.get("system", {}).get("agent_curation", {})
    except Exception:
        return {}


@app.route(f"{P}/", strict_slashes=False)
def dashboard_home():
    lenses = _fetch_all()
    runtime_states = _all_runtime_states()
    token_usage = _all_token_usage()
    health = {n: get_health_status(n, lenses[n], runtime_states[n], token_usage[n]) for n in LENS_NAMES}
    rel_times = {n: _relative_time(lenses[n].get("training", {}).get("last_training")) for n in LENS_NAMES}
    n_online = sum(1 for d in lenses.values() if not d.get("error"))
    custodian_state = _load_custodian_state()
    cust_rel_time = _relative_time(custodian_state["timestamp"]) if custodian_state else ""
    cust_incidents_today = _count_incidents_today()
    agent_states = _load_agent_states()
    agent_cfg = _system_agent_config()
    rel_times_agent = {
        n: _relative_time(agent_states[n].get("timestamp", "")) for n in LENS_NAMES
    }
    return _render(_DASH_TMPL, lens_names=LENS_NAMES, lenses=lenses,
                   health=health, rel_times=rel_times,
                   n_online=n_online, n_total=len(LENS_NAMES),
                   custodian_state=custodian_state,
                   cust_rel_time=cust_rel_time,
                   cust_incidents_today=cust_incidents_today,
                   agent_states=agent_states,
                   agent_overall=_agent_overall_status(agent_states),
                   agent_model=agent_cfg.get("model", "qwen2.5:14b-instruct-q4_K_M"),
                   rel_times_agent=rel_times_agent)


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


@app.route(f"{P}/api/agent-status")
def api_agent_status():
    return flask_jsonify({
        "timestamp": _now_local(),
        "config": _system_agent_config(),
        "states": _load_agent_states(),
    })


_AGENTS_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Agents &mdash; Keepsake</title><style>{{ css | safe }}</style></head>
<body>
<a class="back" href="{{ P }}/">&larr; dashboard</a>
<div class="topbar">
  <div><h1>AGENT CURATION</h1>
  <p class="sub">{{ now }} &nbsp;&middot;&nbsp; model: {{ cfg.model }} &nbsp;&middot;&nbsp;
  {% if cfg.enabled %}<span class="status-ok">enabled</span>{% else %}<span class="status-err">disabled</span>{% endif %}
  </p></div>
</div>

{% for lens_name in lens_names %}
{% set ag = states[lens_name] %}
<h2>{{ lens_name.replace('_',' ') }}</h2>
<div class="card" style="border-left:2px solid
  {%- if ag.status == 'complete' %} #1a3a1a
  {%- elif ag.status == 'running' %} #1a2a3a
  {%- elif ag.status == 'error' %}   #3a1a1a
  {%- else %} #1a1a1a{%- endif %}">
  <div class="card-head">
    <span style="display:flex;align-items:center">
      <span class="agent-dot {{ ag.status }}"></span>
      <span class="lens-status
        {%- if ag.status == 'complete' %} status-ok
        {%- elif ag.status == 'running' %} status-warn
        {%- elif ag.status == 'error' %} status-err
        {%- else %} status-off{%- endif %}">{{ ag.status }}</span>
    </span>
    {% if ag.get('timestamp') %}<span style="font-size:10px;color:#2a2a2a">{{ ag.timestamp[:19] }}</span>{% endif %}
  </div>

  {% if ag.status == 'complete' %}
  {% if ag.get('assessment') %}
  <p style="font-size:12px;color:#666;margin-bottom:10px">{{ ag.assessment }}</p>
  {% endif %}

  {% if ag.get('gaps') %}
  <div style="margin-bottom:8px">
    <div class="row"><span class="lbl" style="color:#2a3a2a">gaps identified</span></div>
    {% for gap in ag.gaps %}
    <div style="font-size:11px;color:#3a5a3a;padding:2px 0 2px 8px;border-left:1px solid #1a3a1a">{{ gap }}</div>
    {% endfor %}
  </div>
  {% endif %}

  {% if ag.get('queries') %}
  <div>
    <div class="row"><span class="lbl" style="color:#1a2a4a">search queries generated</span></div>
    <div class="agent-queries">
      {% for q in ag.queries %}
      <span class="agent-query-pill">{{ q }}</span>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <div class="metrics" style="margin-top:12px">
    {% if ag.get('duration_s') %}<div class="metric"><div class="metric-label">duration</div><div class="metric-value">{{ ag.duration_s }}s</div></div>{% endif %}
    {% if ag.get('texts_added') is not none %}<div class="metric"><div class="metric-label">texts added</div><div class="metric-value">{{ ag.get('texts_added',0) }}</div></div>{% endif %}
    {% if ag.get('model') %}<div class="metric"><div class="metric-label">model</div><div class="metric-value" style="font-size:10px">{{ ag.model }}</div></div>{% endif %}
  </div>
  {% elif ag.status == 'error' %}
  <p style="font-size:11px;color:#6a3030">{{ ag.get('error','unknown error') }}</p>
  {% elif ag.status == 'no_corpus' %}
  <p style="font-size:11px;color:#3a3a00">No corpus available yet. Run seed_corpus.py first.</p>
  {% elif ag.status == 'idle' %}
  <p style="font-size:11px;color:#2a2a2a">Not yet run. Waiting for next training cycle.</p>
  {% endif %}
</div>
{% endfor %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js | safe }}
</body></html>"""


@app.route(f"{P}/agents/")
@app.route(f"{P}/agents", strict_slashes=False)
def agents_overview():
    states = _load_agent_states()
    cfg = _system_agent_config()
    return _render(_AGENTS_TMPL, lens_names=LENS_NAMES, states=states, cfg=cfg)


@app.route(f"{P}/api/custodian")
def api_custodian():
    state = _load_custodian_state()
    if not state:
        return flask_jsonify({"running": False}), 200
    return flask_jsonify({"running": True, **state})


# ── Custodian pages ───────────────────────────────────────────────────────────

_CUSTODIAN_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Custodian &mdash; Keepsake</title><style>{{ css | safe }}</style></head>
<body>
<a class="back" href="{{ P }}/">&larr; dashboard</a>
<div class="topbar">
  <div><h1>CUSTODIAN</h1><p class="sub">{{ now }} &nbsp;&middot;&nbsp; stewarding agent</p></div>
  <div class="topbar-right">
    <a href="{{ P }}/custodian/incidents" class="btn">incidents</a>
    <a href="{{ P }}/custodian/quarantine" class="btn">quarantine</a>
  </div>
</div>

{% if not state %}
<div class="card offline">
  <p style="font-size:12px;color:#444">Custodian is not running.<br>
  Start with: <code>python -m helper.custodian.runner</code><br>
  Or install launchd: <code>mac/launchd/com.keepsake.custodian.plist</code></p>
</div>
{% else %}
<div class="card" style="border-left:2px solid {% if state.overall_severity == 'info' %}#1a3a1a{% elif state.overall_severity == 'warning' %}#3a2800{% else %}#4a0000{% endif %}">
  <div class="row"><span class="lbl">overall</span><span class="val cust-overall-{{ state.overall_severity[:4] }}">{{ state.overall_severity }}</span></div>
  <div class="row"><span class="lbl">last check</span><span class="val">{{ state.timestamp }}</span></div>
</div>

{% for check_name, r in state.checks.items() %}
<h2>{{ check_name.replace('_', ' ') }}</h2>
<div class="card {% if r.severity == 'info' %}online{% elif r.severity == 'warning' %}{% else %}offline{% endif %}"
     style="border-left:2px solid {% if r.severity == 'info' %}#1a3a1a{% elif r.severity == 'warning' %}#3a2800{% else %}#4a0000{% endif %}">
  <div class="card-head">
    <span class="lens-status {% if r.severity == 'info' %}status-ok{% elif r.severity == 'warning' %}status-warn{% else %}status-err{% endif %}">{{ r.severity }}</span>
    <span style="font-size:10px;color:#333">{{ r.timestamp[:19] }}</span>
  </div>
  <p style="font-size:12px;color:#888;margin-bottom:8px">{{ r.summary }}</p>
  {% if r.auto_action %}
  <p style="font-size:11px;color:#6a3a00;margin-bottom:8px">→ {{ r.auto_action }}</p>
  {% endif %}
  {% if r.details %}
  <div style="font-size:10px;color:#333;font-family:monospace;white-space:pre-wrap;max-height:120px;overflow:auto">{{ r.details | tojson(indent=2) }}</div>
  {% endif %}
</div>
{% endfor %}
{% endif %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
{{ refresh_js | safe }}
</body></html>"""

_INCIDENTS_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Incidents &mdash; Keepsake Custodian</title><style>{{ css | safe }}</style></head>
<body>
<a class="back" href="{{ P }}/custodian/">&larr; custodian</a>
<h1>INCIDENTS</h1>
<p class="sub">Last 7 days &mdash; warnings and criticals only</p>

{% if not incidents %}
<div class="card"><p style="font-size:11px;color:#333">No incidents in last 7 days.</p></div>
{% else %}
{% for inc in incidents %}
<div class="incident-row">
  <span class="inc-sev-{{ inc.severity }}">{{ inc.severity[:4].upper() }}</span>
  <span style="color:#333;flex:0 0 120px">{{ inc.timestamp[:16] }}</span>
  <span style="color:#555;flex:0 0 140px">{{ inc.check_name.replace('_',' ') }}</span>
  <span style="color:#444;flex:1">{{ inc.summary }}</span>
</div>
{% endfor %}
{% endif %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
</body></html>"""

_QUARANTINE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Quarantine &mdash; Keepsake Custodian</title><style>{{ css | safe }}</style></head>
<body>
<a class="back" href="{{ P }}/custodian/">&larr; custodian</a>
<h1>QUARANTINE REVIEW</h1>
<p class="sub">Auto-quarantined chunks requiring artist review</p>

{% if not items %}
<div class="card"><p style="font-size:11px;color:#333">No quarantined items.</p></div>
{% else %}
{% for item in items %}
<div class="qitem">
  <div class="qitem-head">
    <div>
      <span style="font-size:12px;color:#8a4040">{{ item.filename }}</span>
      <span style="font-size:10px;color:#333;margin-left:8px">{{ item.lens }} &middot; {{ item.quarantined_at[:19] }}</span>
    </div>
    {% if item.chunk_exists %}
    <div class="qactions">
      <form method="POST" action="{{ P }}/custodian/quarantine/{{ item.qid }}/restore" style="display:inline">
        <button type="submit" class="btn btn-restore" style="min-height:32px;padding:4px 10px">restore</button>
      </form>
      <form method="POST" action="{{ P }}/custodian/quarantine/{{ item.qid }}/delete"
            onsubmit="return confirm('Permanently delete this chunk?')">
        <button type="submit" class="btn btn-danger" style="min-height:32px;padding:4px 10px">delete</button>
      </form>
    </div>
    {% else %}
    <span style="font-size:10px;color:#333">already removed</span>
    {% endif %}
  </div>
  <div style="font-size:10px;color:#3a2a2a;margin-bottom:6px">reason: {{ item.reason }}</div>
  {% if item.preview %}
  <pre style="font-size:10px;color:#333;background:#080808;padding:8px;overflow-x:auto;max-height:80px;border:1px solid #1a1a1a">{{ item.preview }}</pre>
  {% endif %}
</div>
{% endfor %}
{% endif %}

<p class="footer">Sangjun Yoo &mdash; Keepsake in Every Hair ~ Migration, 2026</p>
</body></html>"""


@app.route(f"{P}/custodian/")
@app.route(f"{P}/custodian", strict_slashes=False)
def custodian_overview():
    state = _load_custodian_state()
    return _render(_CUSTODIAN_TMPL, state=state)


@app.route(f"{P}/custodian/incidents")
def custodian_incidents():
    from datetime import timedelta
    incidents_file = CUSTODIAN_STATE / "incidents.jsonl"
    incidents = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    if incidents_file.exists():
        try:
            with incidents_file.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("timestamp", "") >= cutoff[:19]:
                            incidents.append(rec)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    incidents.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return _render(_INCIDENTS_TMPL, incidents=incidents)


@app.route(f"{P}/custodian/quarantine")
def custodian_quarantine():
    items = _load_quarantine_items()
    return _render(_QUARANTINE_TMPL, items=items)


@app.route(f"{P}/custodian/quarantine/<qid>/restore", methods=["POST"])
def quarantine_restore(qid: str):
    quarantine_dir = MAC_ROOT / "corpus" / "quarantine" / qid
    if not quarantine_dir.exists():
        return "Quarantine dir not found", 404

    restored = []
    for meta_file in quarantine_dir.glob("*.meta.json"):
        try:
            meta = json.loads(meta_file.read_text())
            lens = meta.get("lens", "")
            chunk_file = quarantine_dir / meta_file.name.replace(".meta.json", "")
            if not chunk_file.exists():
                continue
            dest_dir = MAC_ROOT / "corpus" / "processed" / lens
            dest_dir.mkdir(parents=True, exist_ok=True)
            chunk_file.rename(dest_dir / chunk_file.name)
            meta_file.unlink(missing_ok=True)
            restored.append(lens)

            # Re-enable training if paused_by custodian
            runtime_path = MAC_ROOT / "runtime_state" / f"{lens}.json"
            if runtime_path.exists():
                state = json.loads(runtime_path.read_text())
                if state.get("paused_by") == "custodian":
                    state["training_enabled"] = True
                    state.pop("paused_by", None)
                    state.pop("paused_reason", None)
                    state.pop("paused_at", None)
                    runtime_path.write_text(json.dumps(state, indent=2))
        except Exception:
            pass

    try:
        quarantine_dir.rmdir()  # only removes if empty
    except OSError:
        pass

    return redirect(f"{P}/custodian/quarantine")


@app.route(f"{P}/custodian/quarantine/<qid>/delete", methods=["POST"])
def quarantine_delete(qid: str):
    import shutil
    quarantine_dir = MAC_ROOT / "corpus" / "quarantine" / qid
    if quarantine_dir.exists():
        shutil.rmtree(quarantine_dir)
    return redirect(f"{P}/custodian/quarantine")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
