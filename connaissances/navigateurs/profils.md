# Profils navigateurs : emplacements et formats de bases

## Principe

Chaque navigateur enregistre activites (visites, telechargements, recherches, cookies) dans des bases locales appartenant au profil utilisateur. Ces fichiers sont des collections d'affaire comme les autres : deposes dans `00_evidence/originals/` (profils isoles) ou extraits d'une image disque (`referentiels.py artifacts paths` + `disk.py extract`, cf. v2.0).

L'outil du kit : `scripts/browsers.py` (in-image via `dt`, sqlite stdlib, lecture seule). plaso parse aussi ces bases (super-timeline : `sqlite/chrome_27_history`, `firefox_history`, `safari`, `msiecf`...).

## Emplacements des bases (par navigateur et OS)

Les chemins resous du referentiel ForensicArtifacts (`ChromiumBasedBrowsersHistoryDatabaseFile`, `FirefoxHistory`, ...) restent la source canonique ; table de reference :

| Base | Navigateur | Windows | Linux | macOS |
|------|-----------|---------|-------|-------|
| History | Chrome/Chromium/Edge/Brave/Opera | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\History` (+ `Profile *`) | `~/.config/google-chrome/Default/History` | `~/Library/Application Support/Google/Chrome/Default/History` |
| Cookies | idem Chromium | idem `User Data\Default\Network\Cookies` (Chrome 96+) ou `...\Default\Cookies` | `~/.config/google-chrome/Default/Cookies` | idem macOS |
| Login Data | idem Chromium | `User Data\Default\Login Data` | `~/.config/google-chrome/Default/Login Data` | idem macOS |
| Web Data | idem Chromium (autofill) | `User Data\Default\Web Data` | idem | idem |
| places.sqlite | Firefox | `%APPDATA%\Mozilla\Firefox\Profiles\<profil>\places.sqlite` | `~/.mozilla/firefox/<profil>/places.sqlite` | `~/Library/Application Support/Firefox/Profiles/<profil>/places.sqlite` |
| cookies.sqlite | Firefox | idem dossier profil | idem | idem |
| History.db | Safari | - | - | `~/Library/Safari/History.db` |
| index.dat | IE legacy | `%LOCALAPPDATA%\Microsoft\Windows\INetCache\IE\...` et `\History\...` | - | - |

Regles de depot : conserver l'ensemble du dossier profil quand c'est possible (Preferences, Secure Preferences, Local State comptent pour l'analyse) ; conserver `History-wal`/`-shm` avec la base si la collecte a chaud (cf. limites).

## Formats de bases (exploites par browsers.py)

| Base | Type | Tables cles | Horodatage |
|------|------|-------------|-----------|
| History (Chromium) | SQLite | `urls`, `visits`, `downloads`, `downloads_url_chains`, `keyword_search_terms` | microsecondes depuis 1601-01-01 (WebKit) |
| Cookies (Chromium) | SQLite | `cookies` (valeur chiffree - jamais lue) | microsecondes depuis 1601 |
| places.sqlite (Firefox) | SQLite | `moz_places`, `moz_historyvisits`, `moz_bookmarks` | PRTime : microsecondes depuis epoch Unix |
| cookies.sqlite (Firefox) | SQLite | `moz_cookies` (valeurs en clair mais lecture metadata seulement) | PRTime |
| History.db (Safari) | SQLite | `history_items`, `history_visits` | secondes depuis epoch Unix |
| index.dat (IE) | binaire MSIECF | - | plaso `msiecf` (pas browsers.py) |

Identification automatique : `browsers.py info` reconnait la base par ses tables (pas par le nom de fichier) - un `History` renomme reste identifie.

## Perimetre v2.1 et ecarts

- **Coeur outille** : visites, downloads (Chromium), termes de recherche (Chromium), cookies en metadonnees
- **Ecarts documentes (jamais tente)** : valeurs de cookies chiffrees (AES-256-GCM, cle DPAPI - Chrome 80+ ; App Bound Encryption - Edge 127+), `Login Data` (credentials chiffres), caches binaires (chrome_cache/firefox_cache via plaso), `IndexedDB`/`LocalStorage` (LevelDB), sessions (`Sessions/`, `Session Storage`)
- **Firefox downloads** modernes : annotations places (`moz_annos`, attribut `downloads/sourceURL`) - via plaso ou lecture manuelle ; `downloads.sqlite` obsolete couvert par plaso `firefox_downloads`
- **Firefox verrou** : une base collectee avec Firefox ouvert peut etre en WAL non pointe - collecter `-wal`/`-shm` avec, ou copie avec checkpoint ; `browsers.py` retente en mode `immutable` si la base resiste

## Regles d'evidence

1. La base importee recoit son SHA256 a l'ingestion (regle kit) - les fichiers WAL/SHM attaches sont aussi empreintes
2. Toute extraction depuis image disque passe par `disk.py extract` (rapport TSV avec SHA256 par fichier)
3. Les CSV produits (`browsers.py --out`) vont dans `01_work/navigateurs/` et sont journalises
4. Chaque conclusion cite : base (hash) + table + ligne (URL/horodatage) - une visite sans horodatage source n'est pas une preuve
