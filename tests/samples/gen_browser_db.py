#!/usr/bin/env python3
"""gen_browser_db.py - synthetic browser databases for kit tests (host side).

Builds deterministic SQLite databases with python stdlib (no browser needed,
no network). Databases are NOT committed to the repo: generated at test time
(same policy as the synthetic disk image).

The Chromium History schema is replicated EXACTLY from the plaso parser
signature (chrome_history, schema 67_3, pinned plaso 20260720): plaso selects
SQLite parsers by schema fingerprint, so the E2E requires the real schema.

Contents (deterministic, markers for E2E assertions):
  chrome History        visits (payload/portal/search/file), download
                        payload.exe (complete), search term KIT-BROWSER-SEARCH
  --firefox places.sqlite   same visits under moz_places/moz_historyvisits
  --cookies Cookies     chromium cookies metadata (3 rows, no values)

Usage:
  python3 tests/samples/gen_browser_db.py <out_dir> [--firefox] [--cookies]
"""
import sqlite3
import sys
from pathlib import Path

# WebKit epoch (1601-01-01) timestamps in microseconds, deterministic
EPOCH_DELTA_US = 11644473600 * 1_000_000
BASE_US = (1768012800 * 1_000_000) + EPOCH_DELTA_US   # 2026-01-10T00:00:00Z

SCHEMA = {
        "downloads": (
            "CREATE TABLE downloads (id INTEGER PRIMARY KEY,guid VARCHAR NOT NULL,current_path LONGVARCHAR NOT NULL,target_path LONGVARCHAR NOT NULL,start_time INTEGER NOT NULL,received_bytes INTEGER NOT NULL,total_bytes INTEGER NOT NULL,state INTEGER NOT NULL,danger_type INTEGER NOT NULL,interrupt_reason INTEGER NOT NULL,hash BLOB NOT NULL,end_time INTEGER NOT NULL,opened INTEGER NOT NULL,last_access_time INTEGER NOT NULL,transient INTEGER NOT NULL,referrer VARCHAR NOT NULL,site_url VARCHAR NOT NULL,tab_url VARCHAR NOT NULL,tab_referrer_url VARCHAR NOT NULL,http_method VARCHAR NOT NULL,by_ext_id VARCHAR NOT NULL,by_ext_name VARCHAR NOT NULL,etag VARCHAR NOT NULL,last_modified VARCHAR NOT NULL,mime_type VARCHAR(255) NOT NULL,original_mime_type VARCHAR(255) NOT NULL)"
        ),
        "downloads_slices": (
            "CREATE TABLE downloads_slices (download_id INTEGER NOT NULL,offset INTEGER NOT NULL,received_bytes INTEGER NOT NULL, finished INTEGER NOT NULL DEFAULT 0,PRIMARY KEY (download_id, offset) )"
        ),
        "downloads_url_chains": (
            "CREATE TABLE downloads_url_chains (id INTEGER NOT NULL,chain_index INTEGER NOT NULL,url LONGVARCHAR NOT NULL, PRIMARY KEY (id, chain_index) )"
        ),
        "keyword_search_terms": (
            "CREATE TABLE keyword_search_terms (keyword_id INTEGER NOT NULL,url_id INTEGER NOT NULL,lower_term LONGVARCHAR NOT NULL,term LONGVARCHAR NOT NULL)"
        ),
        "meta": (
            "CREATE TABLE meta(key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, value LONGVARCHAR)"
        ),
        "segment_usage": (
            "CREATE TABLE segment_usage (id INTEGER PRIMARY KEY,segment_id INTEGER NOT NULL,time_slot INTEGER NOT NULL,visit_count INTEGER DEFAULT 0 NOT NULL)"
        ),
        "segments": (
            "CREATE TABLE segments (id INTEGER PRIMARY KEY,name VARCHAR,url_id INTEGER NON NULL)"
        ),
        "typed_url_sync_metadata": (
            "CREATE TABLE typed_url_sync_metadata (storage_key INTEGER PRIMARY KEY NOT NULL,value BLOB)"
        ),
        "urls": (
            "CREATE TABLE urls(id INTEGER PRIMARY KEY AUTOINCREMENT,url LONGVARCHAR,title LONGVARCHAR,visit_count INTEGER DEFAULT 0 NOT NULL,typed_count INTEGER DEFAULT 0 NOT NULL,last_visit_time INTEGER NOT NULL,hidden INTEGER DEFAULT 0 NOT NULL)"
        ),
        "visit_source": (
            "CREATE TABLE visit_source(id INTEGER PRIMARY KEY,source INTEGER NOT NULL)"
        ),
        "visits": (
            "CREATE TABLE visits(id INTEGER PRIMARY KEY,url INTEGER NOT NULL,visit_time INTEGER NOT NULL,from_visit INTEGER,transition INTEGER DEFAULT 0 NOT NULL,segment_id INTEGER,visit_duration INTEGER DEFAULT 0 NOT NULL)"
        )
}

# (url, titre, [offsets_visites_en_secondes], transition)
URLS = [
    ("https://malware-cdn.invalid/payload.exe", "payload.exe",
     [0, 60, 120], 1),                       # transitions TYPED, 3 visits
    ("https://portail.interne.example/rapports", "Rapports internes",
     [300, 360], 1),
    ("https://recherche.example.invalid/search?q=KIT-BROWSER-SEARCH",
     "KIT-BROWSER-SEARCH - recherche", [600], 1),
    ("file:///etc/passwd", "", [660], 0),     # transition LINK
]
# (chemin_cible, url_source, decalage, octets_recus, octets_total, etat, danger)
DOWNLOAD = ("C:\\Users\\utilisateur\\Downloads\\payload.exe",
            "https://malware-cdn.invalid/payload.exe", 90, 1048576,
            1048576, 1, 0)
SEARCH_TERM = ("KIT-BROWSER-SEARCH", "kit browser search")


def creer_chrome_history(chemin: Path):
    conn = sqlite3.connect(chemin)
    cur = conn.cursor()
    for create in SCHEMA.values():
        cur.execute(create)
    visit_id = 0
    for url, titre, offsets, transition in URLS:
        cur.execute(
            "INSERT INTO urls (url, title, visit_count, typed_count, "
            "last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, 0)",
            (url, titre, len(offsets), transition, BASE_US + offsets[-1] * 1_000_000))
        url_id = cur.lastrowid
        for decalage in offsets:
            visit_id += 1
            cur.execute(
                "INSERT INTO visits (id, url, visit_time, from_visit, transition, "
                "segment_id, visit_duration) VALUES (?, ?, ?, NULL, ?, NULL, 0)",
                (visit_id, url_id, BASE_US + decalage * 1_000_000, transition))
    chemin_cible, url_source, decalage, recus, total, etat, danger = DOWNLOAD
    debut = BASE_US + decalage * 1_000_000
    cur.execute(
        "INSERT INTO downloads (guid, current_path, target_path, start_time, "
        "received_bytes, total_bytes, state, danger_type, interrupt_reason, hash, "
        "end_time, opened, last_access_time, transient, referrer, site_url, "
        "tab_url, tab_referrer_url, http_method, by_ext_id, by_ext_name, etag, "
        "last_modified, mime_type, original_mime_type) "
        "VALUES ('kit-test-guid', ?, ?, ?, ?, ?, ?, ?, 0, X'', 0, 0, 0, 0, "
        "'', '', '', '', '', '', '', '', '', '', '')",
        (chemin_cible, chemin_cible, debut, recus, total, etat, danger))
    cur.execute("INSERT INTO downloads_url_chains (id, chain_index, url) "
                "VALUES (1, 0, ?)", (url_source,))
    cur.execute("INSERT INTO keyword_search_terms (keyword_id, url_id, "
                "lower_term, term) VALUES (1, 3, ?, ?)",
                (SEARCH_TERM[1], SEARCH_TERM[0]))
    cur.execute("INSERT INTO meta (key, value) VALUES ('version', '67')")
    conn.commit()
    conn.close()


def creer_firefox_places(chemin: Path):
    conn = sqlite3.connect(chemin)
    cur = conn.cursor()
    cur.executescript(
        "CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url LONGVARCHAR, "
        "title LONGVARCHAR, rev_host LONGVARCHAR, visit_count INTEGER DEFAULT 0, "
        "hidden INTEGER DEFAULT 0, typed INTEGER DEFAULT 0, "
        "last_visit_date INTEGER DEFAULT 0);"
        "CREATE TABLE moz_historyvisits (id INTEGER PRIMARY KEY, from_visit "
        "INTEGER, place_id INTEGER, visit_date INTEGER, visit_type INTEGER);")
    # PRTime : microsecondes depuis l'epoch Unix
    for url, titre, offsets, _ in URLS:
        cur.execute("INSERT INTO moz_places (url, title, visit_count, "
                    "last_visit_date) VALUES (?, ?, ?, ?)",
                    (url, titre, len(offsets),
                     (1768012800 + offsets[-1]) * 1_000_000))
        place_id = cur.lastrowid
        for decalage in offsets:
            cur.execute("INSERT INTO moz_historyvisits (place_id, visit_date, "
                        "visit_type) VALUES (?, ?, ?)",
                        (place_id, (1768012800 + decalage) * 1_000_000, 1))
    conn.commit()
    conn.close()


def creer_chrome_cookies(chemin: Path):
    conn = sqlite3.connect(chemin)
    cur = conn.cursor()
    cur.executescript(
        "CREATE TABLE cookies (creation_utc INTEGER NOT NULL, host_key VARCHAR "
        "NOT NULL, name VARCHAR NOT NULL, value VARCHAR NOT NULL, path VARCHAR, "
        "expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, "
        "last_access_utc INTEGER);")
    for hote, nom in (("portail.interne.example", "session"),
                      ("recherche.example.invalid", "pref"),
                      ("malware-cdn.invalid", "tracker")):
        cur.execute("INSERT INTO cookies (creation_utc, host_key, name, value, "
                    "path, expires_utc, last_access_utc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (BASE_US, hote, nom, "", "/", BASE_US + 86400 * 1_000_000,
                     BASE_US))
    conn.commit()
    conn.close()


def main():
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(arguments) != 1:
        print(__doc__)
        return 2
    sortie_dir = Path(arguments[0]).resolve()
    sortie_dir.mkdir(parents=True, exist_ok=True)
    for fichier in ("History", "places.sqlite", "Cookies"):
        (sortie_dir / fichier).unlink(missing_ok=True)
    creer_chrome_history(sortie_dir / "History")
    if "--firefox" in sys.argv:
        creer_firefox_places(sortie_dir / "places.sqlite")
    if "--cookies" in sys.argv:
        creer_chrome_cookies(sortie_dir / "Cookies")
    print(f"synthetic browser databases written: {sortie_dir} "
          "(markers: KIT-BROWSER-VISIT, KIT-BROWSER-SEARCH)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
