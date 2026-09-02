#!/bin/sh
# gen_licences.sh - inventaire factuel des licences embarquees dans l'image du kit
# Usage (depuis l'hote, session avec acces docker) :
#   cd "<dossier du kit>"
#   docker run -i --rm --network none --user 0 oreoa-ai-tools:1.1.0 sh \
#     < scripts/gen_licences.sh > docs/licences-image.txt
# Executer apres chaque changement de l'image (Dockerfile) et joindre ce fichier
# a tout bundle distribue (regle du profil air-gap).

echo "== Image oreoa-ai-tools - inventaire des licences =="
echo "== Genere dans le conteneur ; source de verite : /usr/share/doc/*/copyright =="
echo

echo "== Inventaire des paquets Debian installes (dpkg-query) =="
dpkg-query -W | sort
echo

echo "== Inventaire des paquets Python installes (pip) =="
pip list --format=freeze 2>/dev/null | sort
echo

echo "== Licences des bibliotheques d'analyse (metadata importlib) =="
python3 - <<'PY'
from importlib.metadata import distribution
for nom in ["plaso", "volatility3", "regipy", "python-evtx", "evtx", "PyYAML"]:
    try:
        d = distribution(nom)
        lic = d.metadata.get("License") or "voir METADATA / classifiers"
        print(f"{d.metadata['Name']} {d.metadata['Version']} - {lic}")
    except Exception as exc:  # noqa: BLE001
        print(f"{nom} - erreur : {exc}")
PY
echo

echo "== Licences des paquets Debian (extraits des fichiers copyright installes) =="
for d in /usr/share/doc/*/ ; do
    p=$(basename "$d")
    f="${d}copyright"
    if [ -f "$f" ]; then
        echo "--- $p ---"
        grep -iE "^(license|copyright)" "$f" | head -4
    fi
done
