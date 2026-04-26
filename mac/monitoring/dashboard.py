#!/usr/bin/env python3
"""Keepsake Control Panel — serves the dashboard + health status endpoint.
Uses stdlib only. Port 8080.
"""
import json, os, glob, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

SERVICES = [
    {"id": "ar",  "port": 8000},
    {"id": "en",  "port": 8001},
    {"id": "gr",  "port": 8002},
    {"id": "br",  "port": 8003},
    {"id": "px",  "port": 8765},
]

LENS_NAMES = [
    "human_time",
    "infrastructure_time",
    "environmental_time",
    "digital_time",
    "liminal_time",
    "more_than_human_time",
]

PI_HOSTS = {
    "human_time":           "pi1.local",
    "infrastructure_time":  "pi2.local",
    "environmental_time":   "pi3.local",
    "digital_time":         "pi4.local",
    "liminal_time":         "pi5.local",
    "more_than_human_time": "pi6.local",
}

HERE     = os.path.dirname(os.path.abspath(__file__))
MAC_ROOT = os.path.dirname(HERE)

STATUS_PATH = {8765: "/admin"}


def check(port):
    path    = STATUS_PATH.get(port, "/")
    timeout = 5 if port == 8765 else 2
    try:
        with urlopen(f"http://localhost:{port}{path}", timeout=timeout) as r:
            return r.status
    except Exception:
        return 0


def status_all():
    results, threads = {}, []
    def worker(svc):
        results[svc["port"]] = check(svc["port"])
    for svc in SERVICES:
        t = threading.Thread(target=worker, args=(svc,), daemon=True)
        t.start(); threads.append(t)
    for t in threads: t.join(timeout=3)
    return results


def training_status():
    mac_stats = {}
    try:
        import psutil
        mac_stats = {
            "cpu_pct":  psutil.cpu_percent(interval=0.1),
            "ram_pct":  psutil.virtual_memory().percent,
            "disk_pct": psutil.disk_usage("/").percent,
        }
    except ImportError:
        pass

    lenses = {}
    for lens in LENS_NAMES:
        corpus_dir  = os.path.join(MAC_ROOT, "corpus", "processed", lens)
        chunk_count = len(glob.glob(os.path.join(corpus_dir, "*.txt"))) if os.path.isdir(corpus_dir) else 0

        training_enabled = True
        last_training_at = None
        state_file = os.path.join(MAC_ROOT, "runtime_state", f"{lens}.json")
        try:
            with open(state_file) as f:
                state = json.load(f)
            training_enabled = state.get("training_enabled", True)
            last_training_at = state.get("last_training_at")
        except Exception:
            pass

        adapter_version = None
        current_file = os.path.join(MAC_ROOT, "adapters", lens, "current.json")
        try:
            with open(current_file) as f:
                adapter_version = json.load(f).get("checkpoint")
        except Exception:
            pass

        pi_data = {}
        try:
            with urlopen(f"http://{PI_HOSTS[lens]}:5000/status", timeout=2) as r:
                pi_data = json.loads(r.read().decode())
        except Exception:
            pass

        lenses[lens] = {
            "corpus_chunks":    chunk_count,
            "training_enabled": training_enabled,
            "last_training_at": last_training_at,
            "adapter_version":  adapter_version,
            "pi_online":        bool(pi_data),
            "pi_temp":          pi_data.get("temp_c"),
            "pi_cpu_pct":       pi_data.get("cpu_pct"),
            "pi_ram_pct":       pi_data.get("ram_pct"),
            "pi_disk_pct":      pi_data.get("disk_pct"),
            "pi_model_loaded":  pi_data.get("model_loaded"),
        }

    return {"mac": mac_stats, "lenses": lenses}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def reply(self, code, ctype, body):
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/status":
            self.reply(200, "application/json", json.dumps(status_all()))

        elif path == "/api/training-status":
            self.reply(200, "application/json", json.dumps(training_status()))

        elif path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.reply(200, "text/html; charset=utf-8", f.read())

        elif path in ("/monitor", "/monitor/"):
            with open(os.path.join(HERE, "monitor.html"), "rb") as f:
                self.reply(200, "text/html; charset=utf-8", f.read())

        else:
            self.reply(404, "text/plain", "Not found")


if __name__ == "__main__":
    print("Keepsake Control Panel → http://localhost:8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
