#!/usr/bin/env python3
"""browsers.py - browser database tooling (sqlite stdlib, read-only).

Runs INSIDE the container (via dt): browser profile databases collected as
case collections (or extracted from disk images via disk.py) are parsed
read-only. Encrypted values (cookie contents, Login Data credentials) are
NEVER read - metadata only (documented gap, v2.1 perimeter).

Supported databases:
  chromium history   History (urls, visits, downloads, keyword_search_terms)
  chromium cookies   Cookies (metadata only)
  firefox places     places.sqlite (moz_places, moz_historyvisits)
  firefox cookies    cookies.sqlite (moz_cookies, metadata only)
  safari history     History.db (history_items, history_visits)

Downloads: chromium only in this tool (Firefox modern downloads live in
places annotations - use plaso firefox_downloads / knowledge doc; Safari
downloads via plaso plist). IE legacy: plaso msiecf (index.dat).

Usage:
  browsers.py info <db>                      identify database, counts, time range
  browsers.py visits <db> [--out <file>]     visits (url, title, count, time, transition)
  browsers.py downloads <db> [--out <file>]  downloads (chromium only)
  browsers.py searches <db> [--out <file>]   search engine terms (chromium only)
  browsers.py cookies <db> [--out <file>]    cookies metadata (chromium, firefox)
"""
import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Chrome transition core masks (content::PageTransition)
TRANSITIONS = {
    0: "LINK", 1: "TYPED", 2: "AUTO_BOOKMARK", 3: "AUTO_SUBFRAME",
    4: "MANUAL_SUBFRAME", 5: "GENERATED", 6: "START_PAGE", 7: "FORM_SUBMIT",
    8: "RELOAD", 9: "KEYWORD", 10: "KEYWORD_GENERATED",
}
CHROME_STATES = {0: "in-progress", 1: "complete", 2: "cancelled",
                 3: "interrupted", 4: "interrupted"}
# Firefox visit types (nsINavHistoryService)
FIREFOX_TYPES = {
    1: "LINK", 2: "TYPED", 3: "BOOKMARK", 4: "EMBED", 5: "REDIRECT_PERM",
    6: "REDIRECT_TEMP", 7: "DOWNLOAD", 8: "FRAMED", 9: "CHART",
}


def connect_ro(chemin: Path) -> sqlite3.Connection:
    """Read-only connection; WAL-database fallback to immutable snapshot."""
    uri = f"file:{chemin}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True, timeout=10)
    except sqlite3.OperationalError:
        return sqlite3.connect(f"file:{chemin}?mode=ro&immutable=1", uri=True,
                               timeout=10)


def tables(conn: sqlite3.Connection) -> set:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")
    return {r[0] for r in cur.fetchall()}


def identifier(conn: sqlite3.Connection) -> dict:
    t = tables(conn)
    if {"urls", "visits"} <= t:
        return {"kind": "chromium-history", "family": "chromium"}
    if "cookies" in t and "host_key" in colonnes(conn, "cookies"):
        return {"kind": "chromium-cookies", "family": "chromium"}
    if {"moz_places", "moz_historyvisits"} <= t:
        return {"kind": "firefox-places", "family": "firefox"}
    if "moz_cookies" in t:
        return {"kind": "firefox-cookies", "family": "firefox"}
    if {"history_items", "history_visits"} <= t:
        return {"kind": "safari-history", "family": "safari"}
    return {"kind": "unknown", "family": "unknown"}


def colonnes(conn: sqlite3.Connection, table: str) -> list:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def webkit_vers_iso(us: int) -> str:
    """Chrome/Chromium: microseconds since 1601-01-01."""
    if not us:
        return ""
    secondes = us / 1_000_000 - 11644473600
    return datetime.fromtimestamp(secondes, tz=timezone.utc).isoformat()


def prtime_vers_iso(us: int) -> str:
    """Firefox PRTime: microseconds since Unix epoch."""
    if not us:
        return ""
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).isoformat()


def epoch_vers_iso(s: float) -> str:
    """Safari History.db: seconds since Unix epoch."""
    if not s:
        return ""
    return datetime.fromtimestamp(s, tz=timezone.utc).isoformat()


def ecrire_csv(chemin_sortie, entete, lignes):
    ecrivain = csv.writer(chemin_sortie)
    ecrivain.writerow(entete)
    ecrivain.writerows(lignes)


def cmd_info(chemin_db: Path) -> int:
    if not chemin_db.is_file():
        print(f"Error: database not found: {chemin_db}", file=sys.stderr)
        return 1
    conn = connect_ro(chemin_db)
    ident = identifier(conn)
    print(f"database: {chemin_db.name}")
    print(f"kind: {ident['kind']}")
    print(f"family: {ident['family']}")
    try:
        if ident["kind"] == "chromium-history":
            n_urls = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
            n_visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
            n_dl = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
            lo, hi = conn.execute(
                "SELECT MIN(visit_time), MAX(visit_time) FROM visits").fetchone()
            print(f"counts: urls={n_urls}, visits={n_visits}, downloads={n_dl}")
            print(f"period: {webkit_vers_iso(lo or 0)} -> {webkit_vers_iso(hi or 0)}")
        elif ident["kind"] == "firefox-places":
            n_places = conn.execute("SELECT COUNT(*) FROM moz_places").fetchone()[0]
            n_visits = conn.execute(
                "SELECT COUNT(*) FROM moz_historyvisits").fetchone()[0]
            lo, hi = conn.execute(
                "SELECT MIN(visit_date), MAX(visit_date) "
                "FROM moz_historyvisits").fetchone()
            print(f"counts: places={n_places}, visits={n_visits}")
            print(f"period: {prtime_vers_iso(lo or 0)} -> {prtime_vers_iso(hi or 0)}")
        elif ident["kind"] == "safari-history":
            n_items = conn.execute(
                "SELECT COUNT(*) FROM history_items").fetchone()[0]
            n_visits = conn.execute(
                "SELECT COUNT(*) FROM history_visits").fetchone()[0]
            lo, hi = conn.execute(
                "SELECT MIN(visit_time), MAX(visit_time) "
                "FROM history_visits").fetchone()
            print(f"counts: items={n_items}, visits={n_visits}")
            print(f"period: {epoch_vers_iso(lo or 0)} -> {epoch_vers_iso(hi or 0)}")
        elif ident["kind"] in ("chromium-cookies", "firefox-cookies"):
            table = "cookies" if ident["kind"] == "chromium-cookies" else "moz_cookies"
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"counts: cookies={n} (metadata only - values encrypted, never read)")
        else:
            print("counts: unknown schema - refer to connaissances/navigateurs/")
    except sqlite3.DatabaseError as exc:
        print(f"[warn] schema probing failed: {exc}")
    conn.close()
    return 0


def cmd_visits(chemin_db: Path, sortie) -> int:
    conn = connect_ro(chemin_db)
    ident = identifier(conn)
    lignes = []
    if ident["kind"] == "chromium-history":
        cur = conn.execute(
            "SELECT visits.visit_time, urls.url, urls.title, urls.visit_count, "
            "visits.transition FROM visits JOIN urls ON urls.id = visits.url "
            "ORDER BY visits.visit_time")
        for t, url, titre, compte, transition in cur:
            label = TRANSITIONS.get(transition & 0xFF, str(transition & 0xFF))
            lignes.append([webkit_vers_iso(t), url, titre or "", compte, label])
        entete = ["time_utc", "url", "title", "visit_count", "transition"]
    elif ident["kind"] == "firefox-places":
        cur = conn.execute(
            "SELECT v.visit_date, p.url, p.title, p.visit_count, v.visit_type "
            "FROM moz_historyvisits v JOIN moz_places p ON p.id = v.place_id "
            "ORDER BY v.visit_date")
        for t, url, titre, compte, vtype in cur:
            label = FIREFOX_TYPES.get(vtype, str(vtype))
            lignes.append([prtime_vers_iso(t), url, titre or "", compte, label])
        entete = ["time_utc", "url", "title", "visit_count", "transition"]
    elif ident["kind"] == "safari-history":
        cur = conn.execute(
            "SELECT v.visit_time, i.url, i.title, i.visit_count "
            "FROM history_visits v JOIN history_items i "
            "ON i.id = v.history_item ORDER BY v.visit_time")
        for t, url, titre, compte in cur:
            lignes.append([epoch_vers_iso(t), url, titre or "", compte, ""])
        entete = ["time_utc", "url", "title", "visit_count", "transition"]
    else:
        print(f"Error: visits not supported for kind: {ident['kind']}",
              file=sys.stderr)
        return 1
    ecrire_csv(sortie, entete, lignes)
    print(f"[visits] {len(lignes)} row(s) exported (kind {ident['kind']})")
    return 0


def cmd_downloads(chemin_db: Path, sortie) -> int:
    conn = connect_ro(chemin_db)
    ident = identifier(conn)
    if ident["kind"] != "chromium-history":
        print("Error: downloads supported for chromium history only "
              "(firefox: plaso firefox_downloads / annotations ; "
              "safari: plaso safari_downloads plist ; ie: msiecf)",
              file=sys.stderr)
        return 1
    lignes = []
    cur = conn.execute(
        "SELECT d.id, d.target_path, d.start_time, d.received_bytes, "
        "d.total_bytes, d.state, d.danger_type, d.mime_type, c.url "
        "FROM downloads d LEFT JOIN downloads_url_chains c "
        "ON c.id = d.id AND c.chain_index = 0 ORDER BY d.start_time")
    for identifiant, cible, t, recus, total, etat, danger, mime, url in cur:
        lignes.append([webkit_vers_iso(t), url or "", cible or "", recus or 0,
                       total or 0, CHROME_STATES.get(etat, str(etat)),
                       danger or 0, mime or ""])
    ecrire_csv(sortie, ["time_utc", "source_url", "target_path", "received_bytes",
                        "total_bytes", "state", "danger_type", "mime_type"], lignes)
    print(f"[downloads] {len(lignes)} row(s) exported")
    return 0


def cmd_searches(chemin_db: Path, sortie) -> int:
    conn = connect_ro(chemin_db)
    ident = identifier(conn)
    if ident["kind"] != "chromium-history":
        print("Error: keyword_search_terms is a chromium feature "
              "(firefox/safari: typed searches appear as visits)",
              file=sys.stderr)
        return 1
    lignes = []
    cur = conn.execute(
        "SELECT k.term, k.lower_term, u.url, u.title, u.last_visit_time "
        "FROM keyword_search_terms k JOIN urls u ON u.id = k.url_id "
        "ORDER BY u.last_visit_time")
    for terme, normalise, url, titre, t in cur:
        lignes.append([webkit_vers_iso(t), terme, normalise or "", url, titre or ""])
    ecrire_csv(sortie, ["last_visit_utc", "term", "lower_term", "url", "title"],
               lignes)
    print(f"[searches] {len(lignes)} row(s) exported")
    return 0


def cmd_cookies(chemin_db: Path, sortie) -> int:
    conn = connect_ro(chemin_db)
    ident = identifier(conn)
    lignes = []
    if ident["kind"] == "chromium-cookies":
        cur = conn.execute(
            "SELECT creation_utc, host_key, name, path, expires_utc, "
            "last_access_utc, is_secure, is_httponly FROM cookies "
            "ORDER BY creation_utc")
        for creation, hote, nom, chemin, expire, acces, secure, httponly in cur:
            lignes.append([webkit_vers_iso(creation), hote, nom, chemin,
                           webkit_vers_iso(expire), webkit_vers_iso(acces),
                           "yes" if secure else "no", "yes" if httponly else "no"])
        entete = ["created_utc", "host", "name", "path", "expires_utc",
                  "last_access_utc", "secure", "httponly"]
    elif ident["kind"] == "firefox-cookies":
        cur = conn.execute(
            "SELECT creationTime, host, name, path, expiry, lastAccessed, "
            "isSecure, isHttpOnly FROM moz_cookies ORDER BY creationTime")
        for creation, hote, nom, chemin, expire, acces, secure, httponly in cur:
            lignes.append([prtime_vers_iso(creation), hote, nom, chemin,
                           prtime_vers_iso(expire), prtime_vers_iso(acces),
                           "yes" if secure else "no", "yes" if httponly else "no"])
        entete = ["created_utc", "host", "name", "path", "expires_utc",
                  "last_access_utc", "secure", "httponly"]
    else:
        print("Error: cookies supported for chromium/firefox sqlite databases "
              "(safari: plaso safari_cookies binarycookies)", file=sys.stderr)
        return 1
    ecrire_csv(sortie, entete, lignes)
    print(f"[cookies] {len(lignes)} row(s) exported (metadata only, "
          "values encrypted - never read)")
    return 0


def main():
    arguments = sys.argv[1:]
    if len(arguments) < 2:
        print(__doc__)
        return 2
    action, chemin_db = arguments[0], Path(arguments[1])
    sortie = sys.stdout
    if "--out" in arguments:
        i = arguments.index("--out")
        if i + 1 < len(arguments):
            chemin_sortie = Path(arguments[i + 1])
            chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
            sortie = chemin_sortie.open("w", newline="")
    actions = {"info": cmd_info, "visits": cmd_visits, "downloads": cmd_downloads,
               "searches": cmd_searches, "cookies": cmd_cookies}
    if action not in actions:
        print(__doc__)
        return 2
    try:
        return actions[action](chemin_db, sortie) if action != "info" \
            else cmd_info(chemin_db)
    finally:
        if sortie is not sys.stdout:
            sortie.close()


if __name__ == "__main__":
    sys.exit(main())
