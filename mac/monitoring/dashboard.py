#!/usr/bin/env python3
"""
Keepsake Control Panel — status + transparent reverse proxy.
Strips X-Frame-Options / CSP frame-ancestors so admin pages embed
in iframes. Rewrites relative URLs and intercepts fetch/XHR inside
the proxied HTML so all sub-requests route through /proxy/<port>/.
Uses stdlib only. Port 8080.
"""
import json, os, re, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

SERVICES = [
    {"id": "ar",  "port": 8000},
    {"id": "en",  "port": 8001},
    {"id": "gr",  "port": 8002},
    {"id": "br",  "port": 8003},
    {"id": "px",  "port": 8765},
]

HERE = os.path.dirname(os.path.abspath(__file__))

STRIP_RESP_HEADERS = {
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
}
SKIP_COPY_HEADERS = STRIP_RESP_HEADERS | {
    "content-length", "transfer-encoding", "connection",
}

# Injected before any other script in proxied HTML pages.
# Rewrites absolute-path fetch/XHR so they stay within the proxy.
INTERCEPT = """<script>
(function(pfx){
  var F=window.fetch;
  window.fetch=function(u,o){
    if(typeof u==='string'&&u.startsWith('/')&&!u.startsWith('/proxy/'))u=pfx+u;
    return F.call(this,u,o);
  };
  var X=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(m,u){
    if(typeof u==='string'&&u.startsWith('/')&&!u.startsWith('/proxy/'))u=pfx+u;
    return X.apply(this,arguments);
  };
})('__PFX__');
</script>"""


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


def do_proxy(port, subpath, method, body, req_headers):
    url = f"http://localhost:{port}{subpath}"
    fwd = {}
    for h in ("content-type", "accept", "accept-encoding", "cookie", "authorization"):
        if h in req_headers: fwd[h] = req_headers[h]
    # Avoid compressed responses so we can rewrite HTML without decompressing
    fwd.pop("accept-encoding", None)
    try:
        req = Request(url, data=body, headers=fwd, method=method)
        with urlopen(req, timeout=15) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except URLError:
        return 502, {}, b"<h1>502 Bad Gateway</h1><p>Service may be down.</p>"
    except Exception as e:
        return 500, {}, str(e).encode()


def inject_proxy(html_bytes, port):
    """Strip frame headers from inline CSP, inject fetch intercept, rewrite URLs."""
    pfx = f"/proxy/{port}"
    html = html_bytes.decode("utf-8", errors="replace")

    # Remove frame-ancestors directives inside meta CSP tags
    html = re.sub(r"frame-ancestors\s+[^;\"']*[;\"']", "", html)

    # Inject intercept script as first child of <head>
    script = INTERCEPT.replace("__PFX__", pfx)
    if re.search(r"<head", html, re.I):
        html = re.sub(r"(<head[^>]*>)", r"\1" + script, html, count=1, flags=re.I)
    else:
        html = script + html

    # Rewrite href/src/action attributes with absolute paths
    def rewrite(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith("/") and not url.startswith("/proxy/"):
            url = pfx + url
        return f'{attr}="{url}"'
    html = re.sub(r'(href|src|action)="(/[^"]*)"', rewrite, html)

    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def reply(self, code, ctype, body, extra=None):
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):  self.dispatch("GET")
    def do_POST(self): self.dispatch("POST")

    def dispatch(self, method):
        raw  = self.path
        sep  = raw.find("?")
        path = raw if sep < 0 else raw[:sep]
        qs   = "" if sep < 0 else raw[sep:]

        # ── /api/status ──────────────────────────────────────────────
        if path == "/api/status":
            self.reply(200, "application/json", json.dumps(status_all()))
            return

        # ── /proxy/<port>/<subpath> ───────────────────────────────────
        m = re.match(r"^/proxy/(\d+)(/.+)$", path)
        if m:
            port    = int(m.group(1))
            subpath = m.group(2) + qs
            body    = None
            if method == "POST":
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n) if n else b""
            hdrs = {k.lower(): v for k, v in self.headers.items()}
            status, resp_hdrs, resp_body = do_proxy(port, subpath, method, body, hdrs)

            ctype = resp_hdrs.get("Content-Type", "application/octet-stream")
            if "text/html" in ctype:
                resp_body = inject_proxy(resp_body, port)
                ctype     = "text/html; charset=utf-8"

            self.send_response(status)
            for k, v in resp_hdrs.items():
                if k.lower() not in SKIP_COPY_HEADERS:
                    self.send_header(k, v)
            self.send_header("Content-Length", len(resp_body))
            self.send_header("X-Frame-Options", "ALLOWALL")
            self.end_headers()
            self.wfile.write(resp_body)
            return

        # ── / or /index.html ──────────────────────────────────────────
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.reply(200, "text/html; charset=utf-8", f.read())
            return

        self.reply(404, "text/plain", "Not found")


if __name__ == "__main__":
    print("Keepsake Control Panel → http://localhost:8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
