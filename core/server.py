"""
core/server.py — Serveur HTTP Frugal & Ingestion d'Audience Sans Cookie.
Point d'entrée autonome (stdlib http.server) : zéro npm, démarrage < 20ms.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, pathlib, urllib.parse
from typing import Any, Dict, Optional
from core.storage import AnalyticsStorage

TRACKER_JS = (
    "(function(){var d=(document.currentScript&&document.currentScript.getAttribute('data-domain'))||location.hostname;"
    "function t(){var b=JSON.stringify({domain:d,path:location.pathname,referrer:document.referrer});"
    "if(navigator.sendBeacon){navigator.sendBeacon('/api/event',b);}else{"
    "var x=new XMLHttpRequest();x.open('POST','/api/event',true);"
    "x.setRequestHeader('Content-Type','application/json');x.send(b);}}"
    "if(document.readyState==='complete')t();else window.addEventListener('load',t);})();"
).encode("utf-8")

class AnalyticsHandler(BaseHTTPRequestHandler):
    storage = AnalyticsStorage()
    public_dir = pathlib.Path(__file__).parent.parent / "public"

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/tracker.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=86400")
            self._send_cors()
            self.end_headers()
            self.wfile.write(TRACKER_JS)
            return

        if path == "/api/stats":
            qs = urllib.parse.parse_qs(parsed.query)
            domain = qs.get("domain", ["default"])[0]
            stats = self.storage.get_stats(domain)
            payload = json.dumps(stats, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors()
            self.end_headers()
            self.wfile.write(payload)
            return

        # Interface dashboard
        index_file = self.public_dir / "index.html"
        if path in ("/", "/index.html") and index_file.exists():
            content = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/event":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            data = {}

        domain = str(data.get("domain", "default"))
        path = str(data.get("path", "/"))
        referrer = data.get("referrer")
        ip = self.headers.get("X-Forwarded-For", self.client_address[0])
        ua = self.headers.get("User-Agent", "Unknown")

        self.storage.record_event(domain, path, referrer, ip, ua)

        resp = json.dumps({"status": "accepted", "domain": domain}).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors()
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Zéro bavardage sur stdout (style Karpathy)

def run_server(port: int = 8092, db_path: str = "data/analytics.db") -> None:
    AnalyticsHandler.storage = AnalyticsStorage(db_path)
    server = HTTPServer(("0.0.0.0", port), AnalyticsHandler)
    print(f"🚀 [LE REGISTRE FRUGAL] Comptoir actif sur http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    run_server()
