#!/usr/bin/env python3
"""
Keepsake Control Panel — serves the dashboard + health status endpoint.
Uses stdlib only. Port 8080.
"""
import json, os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

SERVICES = [
    {"id": "ar",  "port": 8000},
    {"id": "en",  "port": 8001},
    {"id": "gr",  "port": 8002},
    {"id": "br",  "port": 8003},
    {"id": "px",  "port": 8765},
]

HERE = os.path.dirname(os.path.abspath(__file__))


def check(port):
    try:
        with urlopen(f"http://localhost:{port}/", timeout=2) as r:
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

        elif path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.reply(200, "text/html; charset=utf-8", f.read())

        else:
            self.reply(404, "text/plain", "Not found")


if __name__ == "__main__":
    print("Keepsake Control Panel → http://localhost:8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
