"""
tests/test_server.py — Tests oracles du serveur HTTP d'ingestion (TICKET-02).
"""
import json, threading, time, urllib.request
from core.server import HTTPServer, AnalyticsHandler, AnalyticsStorage

def test_tracker_js_size_and_content(tmp_path):
    port = 8097
    db_file = str(tmp_path / "test_server.db")
    AnalyticsHandler.storage = AnalyticsStorage(db_file)
    httpd = HTTPServer(("127.0.0.1", port), AnalyticsHandler)

    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    time.sleep(0.05)

    try:
        # 1. Tracker JS < 500 octets
        req = urllib.request.Request(f"http://127.0.0.1:{port}/tracker.js")
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            assert resp.status == 200
            assert len(content) < 500
            assert b"navigator.sendBeacon" in content
            assert b"document.cookie" not in content  # Zéro cookie

        # 2. Ingestion /api/event (POST 202)
        payload = json.dumps({"domain": "test.fr", "path": "/catalogue", "referrer": "https://bing.com"}).encode()
        post_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/event",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "PyTestAgent/1.0"}
        )
        with urllib.request.urlopen(post_req) as resp:
            assert resp.status == 202
            body = json.loads(resp.read().decode())
            assert body["status"] == "accepted"

        # 3. Vérification /api/stats
        stats_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/stats?domain=test.fr")
        with urllib.request.urlopen(stats_req) as resp:
            assert resp.status == 200
            stats = json.loads(resp.read().decode())
            assert stats["unique_visitors"] == 1
            assert stats["total_pageviews"] == 1
            assert stats["top_pages"][0]["path"] == "/catalogue"
            assert stats["top_sources"][0]["source"] == "bing.com"
    finally:
        httpd.shutdown()
        httpd.server_close()
