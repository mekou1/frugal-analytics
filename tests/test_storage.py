"""
tests/test_storage.py — Tests oracles stricts pour AnalyticsStorage (TICKET-01).
Vérifie : persistance SQLite, hash anonyme SHA256 sans cookie, agrégation exacte.
"""
import os, pathlib, pytest
from core.storage import AnalyticsStorage, compute_anon_hash, extract_source

def test_extract_source_variations():
    assert extract_source(None) == "Direct"
    assert extract_source("") == "Direct"
    assert extract_source("https://google.com/search?q=boutique") == "google.com"
    assert extract_source("http://t.co/xyz123") == "t.co"

def test_compute_anon_hash_deterministic_and_daily():
    h1 = compute_anon_hash("192.168.1.50", "Mozilla/5.0", "2026-09-25")
    h2 = compute_anon_hash("192.168.1.50", "Mozilla/5.0", "2026-09-25")
    h_next_day = compute_anon_hash("192.168.1.50", "Mozilla/5.0", "2026-09-26")

    assert h1 == h2
    assert len(h1) == 16
    assert h1 != h_next_day  # Anonymat garanti au changement de journée

def test_record_and_aggregate_stats(tmp_path):
    db_file = str(tmp_path / "test_analytics.db")
    store = AnalyticsStorage(db_file)

    # 1. Enregistre 3 événements : 2 par le même visiteur, 1 par un autre
    assert store.record_event("monresto.fr", "/accueil", "https://google.com", "1.1.1.1", "Chrome")
    assert store.record_event("monresto.fr", "/carte", "https://google.com", "1.1.1.1", "Chrome")
    assert store.record_event("monresto.fr", "/accueil", None, "2.2.2.2", "Safari")

    stats = store.get_stats("monresto.fr")

    # Assertions strictes sur les données réelles
    assert stats["domain"] == "monresto.fr"
    assert stats["unique_visitors"] == 2  # 2 passants uniques
    assert stats["total_pageviews"] == 3   # 3 vitrines vues au total

    # Vérification top pages
    paths = {p["path"]: p["views"] for p in stats["top_pages"]}
    assert paths["/accueil"] == 2
    assert paths["/carte"] == 1

    # Vérification top sources
    sources = {s["source"]: s["views"] for s in stats["top_sources"]}
    assert sources["google.com"] == 2
    assert sources["Direct"] == 1
