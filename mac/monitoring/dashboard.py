#!/usr/bin/env python3
"""
Keepsake Control Panel — lightweight status proxy server.
Uses stdlib only (no pip installs needed).  Port 8080.
"""
import json, os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.error import URLError

SERVICES = [
    {"id": "ar",  "name": "drift · ar",  "port": 8000},
    {"id": "en",  "name": "drift · en",  "port": 8001},
    {"id": "gr",  "name": "drift · gr",  "port": 8002},
    {"id": "br",  "name": "drift · br",  "port": 8003},
    {"id": "px",  "name": "parallax",    "port": 8765},
]

HERE = os.path.dirname(os.path.abspath(__file__))

def check(port):
    try:
        with urlopen(f"http://localhost:{port}/", timeout=2) as r:
            return r.status
    except Exception:
        return 0

def status_all():
    results = {}
    threads = []
    def worker(svc):
        results[svc["port"]] = check(svc["port"])
    for svc in SERVICES:
        t = threading.Thread(target=worker, args=(svc,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=3)
    return results

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress access logs

    def send(self, code, ctype, body):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/status":
            self.send(200, "application/json", json.dumps(status_all()))

        elif path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                body = f.read()
            self.send(200, "text/html; charset=utf-8", body)

        else:
            self.send(404, "text/plain", "Not found")

if __name__ == "__main__":
    port = 8080
    print(f"Keepsake Control Panel → http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
