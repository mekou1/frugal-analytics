"""
tests/test_dashboard_e2e.py — Validation fonctionnelle de bout en bout (TICKET-03).
Vérifie : chargement du dashboard web, présence des sélecteurs testid, ingestion et affichage.
"""
import json, threading, time, urllib.request
from core.server import HTTPServer, AnalyticsHandler, AnalyticsStorage

def test_dashboard_serving_and_dom_elements(tmp_path):
    port = 8098
    db_file = str(tmp_path / "test_e2e.db")
    AnalyticsHandler.storage = AnalyticsStorage(db_file)
    httpd = HTTPServer(("127.0.0.1", port), AnalyticsHandler)

    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    time.sleep(0.05)

    try:
        # 1. Requête GET / (dashboard)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "Le Registre Frugal" in html
            assert 'data-testid="visitors-unique"' in html
            assert 'data-testid="pageviews"' in html
            assert 'data-testid="active-pages"' in html
            assert 'data-testid="sources-count"' in html

        # 2. Ingestion de 5 événements
        events = [
            {"domain": "artisan.bio", "path": "/savons", "referrer": "https://instagram.com"},
            {"domain": "artisan.bio", "path": "/savons", "referrer": "https://instagram.com"},
            {"domain": "artisan.bio", "path": "/huiles", "referrer": "https://google.fr"},
            {"domain": "artisan.bio", "path": "/accueil", "referrer": ""},
            {"domain": "artisan.bio", "path": "/accueil", "referrer": "https://instagram.com"},
        ]
        for ev in events:
            p_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/event",
                data=json.dumps(ev).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(p_req) as post_resp:
                assert post_resp.status == 202

        # 3. Vérification des données agrégées
        stats_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/stats?domain=artisan.bio")
        with urllib.request.urlopen(stats_req) as s_resp:
            assert s_resp.status == 200
            stats = json.loads(s_resp.read().decode())
            assert stats["total_pageviews"] == 5
            assert len(stats["top_pages"]) == 3
            assert len(stats["top_sources"]) == 3
    finally:
        httpd.shutdown()
        httpd.server_close()
