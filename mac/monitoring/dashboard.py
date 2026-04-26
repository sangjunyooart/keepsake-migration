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


def _dir_bytes(path: str) -> int:
    total = 0
    if os.path.isdir(path):
        for f in glob.glob(os.path.join(path, "**", "*"), recursive=True):
            if os.path.isfile(f):
                total += os.path.getsize(f)
    return total


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

        sys_info = pi_data.get("system", {})
        corpus_bytes = (
            _dir_bytes(os.path.join(MAC_ROOT, "corpus", "raw", lens)) +
            _dir_bytes(os.path.join(MAC_ROOT, "corpus", "processed", lens))
        )

        lenses[lens] = {
            "corpus_chunks":    chunk_count,
            "corpus_bytes":     corpus_bytes,
            "training_enabled": training_enabled,
            "last_training_at": last_training_at,
            "adapter_version":  adapter_version,
            "pi_online":        bool(pi_data),
            "pi_temp":          sys_info.get("cpu_temp"),
            "pi_cpu_pct":       sys_info.get("cpu_percent"),
            "pi_ram_pct":       sys_info.get("memory_percent"),
            "pi_disk_pct":      sys_info.get("disk_percent"),
            "pi_model_loaded":  pi_data.get("inference_ready"),
        }

    return {"mac": mac_stats, "lenses": lenses}


def lens_detail(lens: str) -> dict:
    raw_dir     = os.path.join(MAC_ROOT, "corpus", "raw", lens)
    adapter_dir = os.path.join(MAC_ROOT, "adapters", lens)

    # Corpus sources — actual ingested JSON files, newest first, up to 40
    sources = []
    if os.path.isdir(raw_dir):
        files = sorted(glob.glob(os.path.join(raw_dir, "*.json")),
                       key=os.path.getmtime, reverse=True)[:40]
        for f in files:
            try:
                item = json.loads(open(f).read())
                text  = item.get("text", "")
                title = item.get("title", "") or text.split("\n")[0][:80]
                # First non-empty line after title as preview
                lines  = [l.strip() for l in text.split("\n") if l.strip()]
                preview = lines[1] if len(lines) > 1 else lines[0] if lines else ""
                src = item.get("source", "")
                sources.append({
                    "title":    title,
                    "source":   src,
                    "kind":     "seed" if "wikipedia:" in src else "active" if src else "manual",
                    "preview":  preview[:200],
                    "saved_at": item.get("saved_at", ""),
                })
            except Exception:
                pass

    # Training history — one entry per checkpoint with version.json
    history = []
    if os.path.isdir(adapter_dir):
        for ckpt in sorted(glob.glob(os.path.join(adapter_dir, "checkpoint_*"))):
            ver = os.path.join(ckpt, "version.json")
            if os.path.exists(ver):
                try:
                    d = json.loads(open(ver).read())
                    history.append({
                        "checkpoint": d.get("checkpoint", os.path.basename(ckpt)),
                        "created_at": d.get("created_at", ""),
                    })
                except Exception:
                    pass

    # Adapter checkpoint sizes
    for entry in history:
        ckpt_path = os.path.join(adapter_dir, entry["checkpoint"])
        entry["size_bytes"] = _dir_bytes(ckpt_path)

    history.sort(key=lambda x: x["created_at"], reverse=True)

    corpus_raw_bytes       = _dir_bytes(os.path.join(MAC_ROOT, "corpus", "raw",       lens))
    corpus_processed_bytes = _dir_bytes(os.path.join(MAC_ROOT, "corpus", "processed", lens))

    return {
        "lens":                   lens,
        "sources":                sources,
        "history":                history,
        "corpus_raw_bytes":       corpus_raw_bytes,
        "corpus_processed_bytes": corpus_processed_bytes,
    }


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

        elif path.startswith("/api/lens-detail/"):
            lens = path.split("/")[-1]
            if lens in LENS_NAMES:
                self.reply(200, "application/json", json.dumps(lens_detail(lens)))
            else:
                self.reply(404, "text/plain", "Unknown lens")

        elif path in ("/monitor", "/monitor/"):
            with open(os.path.join(HERE, "monitor.html"), "rb") as f:
                self.reply(200, "text/html; charset=utf-8", f.read())

        else:
            self.reply(404, "text/plain", "Not found")


if __name__ == "__main__":
    print("Keepsake Control Panel → http://localhost:8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
