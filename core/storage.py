"""
core/storage.py — Persistance SQLite & Agrégations Statistiques Anonymes.
Garantit le zéro-mouchard : anonymisation immédiate par hachage SHA256 journalier.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, os, pathlib, sqlite3
from typing import Any, Dict, List, Optional, Tuple

def compute_anon_hash(ip: str, ua: str, date_str: Optional[str] = None) -> str:
    """Calcule une empreinte éphémère non réversible réinitialisée chaque jour."""
    day = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    salt = "frugal_salt_v1"
    raw = f"{ip}:{ua}:{day}:{salt}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def extract_source(referrer: Optional[str]) -> str:
    """Extrait le domaine source ou 'Direct' si absent."""
    if not referrer or not referrer.strip():
        return "Direct"
    cleaned = referrer.strip().replace("https://", "").replace("http://", "")
    domain = cleaned.split("/")[0].split("?")[0]
    return domain if domain else "Direct"

class AnalyticsStorage:
    """Gestionnaire de persistance SQLite pour Le Registre Frugal."""

    def __init__(self, db_path: str = "data/analytics.db") -> None:
        self.db_path = db_path
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    domain TEXT NOT NULL,
                    path TEXT NOT NULL,
                    source TEXT NOT NULL,
                    anon_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_lookup ON events(domain, timestamp);
            """)

    def record_event(self, domain: str, path: str, referrer: Optional[str], ip: str, ua: str) -> bool:
        """Enregistre un événement de consultation de vitrine."""
        clean_domain = (domain or "default").strip().lower()
        clean_path = ("/" + path.strip().lstrip("/")) if path else "/"
        source = extract_source(referrer)
        anon_hash = compute_anon_hash(ip, ua)
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO events (domain, path, source, anon_hash) VALUES (?, ?, ?, ?)",
                    (clean_domain, clean_path, source, anon_hash)
                )
            return True
        except Exception:
            return False

    def get_stats(self, domain: str = "default", days: int = 7) -> Dict[str, Any]:
        """Agrège les chiffres d'audience de façon rapide et sans profilage."""
        clean_domain = (domain or "default").strip().lower()
        with self._get_conn() as conn:
            # 1. Visiteurs uniques (aujourd'hui)
            r_uniq = conn.execute(
                "SELECT COUNT(DISTINCT anon_hash) FROM events WHERE domain = ? AND DATE(timestamp) = DATE('now')",
                (clean_domain,)
            ).fetchone()
            uniq_today = r_uniq[0] if r_uniq else 0

            # 2. Total pages vues
            r_total = conn.execute(
                "SELECT COUNT(*) FROM events WHERE domain = ?",
                (clean_domain,)
            ).fetchone()
            total_views = r_total[0] if r_total else 0

            # 3. Top pages
            top_pages = [
                {"path": row["path"], "views": row["views"]}
                for row in conn.execute(
                    "SELECT path, COUNT(*) as views FROM events WHERE domain = ? GROUP BY path ORDER BY views DESC LIMIT 10",
                    (clean_domain,)
                )
            ]

            # 4. Top sources
            top_sources = [
                {"source": row["source"], "views": row["views"]}
                for row in conn.execute(
                    "SELECT source, COUNT(*) as views FROM events WHERE domain = ? GROUP BY source ORDER BY views DESC LIMIT 10",
                    (clean_domain,)
                )
            ]

        return {
            "domain": clean_domain,
            "unique_visitors": uniq_today,
            "total_pageviews": total_views,
            "top_pages": top_pages,
            "top_sources": top_sources
        }
