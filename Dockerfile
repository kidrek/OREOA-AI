# Dockerfile - image oreoa-ai-tools du kit OREOA-AI
# Tous les outils d'analyse sont pinnes dans cette image.
# L'hote n'installe rien : il execute les outils via les wrappers (dt).
# Note : le LABEL est place en fin de fichier pour preserver le cache des
# couches apt/pip lors des changements de metadonnees.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

# Couche unique : outils systeme pinnes + compilation pip des dependances
# natives de plaso (libewf, libbde...) puis purge de la chaine de build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tshark=4.4.18-0+deb13u1 \
    sleuthkit=4.12.1+dfsg-3 \
    yara=4.5.2-1 \
    suricata=1:7.0.10-1+deb13u4 \
    hashdeep \
    lzip \
    ca-certificates \
    build-essential \
    python3-dev \
    pkg-config \
 && pip install --no-cache-dir \
    "plaso==20260720" \
    "volatility3==2.28.0" \
    "regipy==6.3.0" \
    "python-evtx==0.8.1" \
    "pyyaml==6.0.2" \
    "evtx==0.12.1" \
    "suricata-update==1.3.3" \
 && apt-get purge -y build-essential python3-dev pkg-config \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Configuration et regles suricata du kit (avant le LABEL final : cache preserve)
COPY config/suricata/threshold.config /etc/suricata/threshold.config
COPY config/suricata/ /etc/suricata/kit/

# Regles suricata : ET Open (snapshot pris au build, triage kit applique) + regles kit.
# Le snapshot est date et son empreinte bakes dans /etc/suricata/kit/regles-trace.txt ;
# la reproductibilite stricte passe par le bundle air-gap (docker save de l'image construite).
RUN suricata-update update --no-test \
      --disable-conf /etc/suricata/kit/disable.conf \
 && cat /etc/suricata/kit/regles-kit.rules >> /var/lib/suricata/rules/suricata.rules \
 && sed -i 's|^# threshold-file: /etc/suricata/threshold.config|threshold-file: /etc/suricata/threshold.config|' /etc/suricata/suricata.yaml \
 && chmod 755 /var/lib/suricata/rules \
 && chmod 644 /var/lib/suricata/rules/* \
 && sh -c 'echo "source: ET Open (snapshot pris au build) + regles kit (sids 1000001+)" > /etc/suricata/kit/regles-trace.txt \
    && echo "sha256: $(sha256sum /var/lib/suricata/rules/suricata.rules | cut -d" " -f1)" >> /etc/suricata/kit/regles-trace.txt \
    && echo "nombre_regles: $(grep -cE "^(alert|drop|pass|reject) " /var/lib/suricata/rules/suricata.rules)" >> /etc/suricata/kit/regles-trace.txt \
    && echo "date_build: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /etc/suricata/kit/regles-trace.txt'

# Utilisateur non root - les fichiers produits appartiennent a l'analyste
RUN useradd -m -u 1000 analyste
USER analyste
WORKDIR /work

# Les volumes d'affaire sont montes a l'execution (00_evidence en ro)
# Pas de reseau par defaut : docker run --network none
LABEL name="oreoa-ai-tools" \
      version="1.1.0" \
      description="Chaine d'outils forensiques du kit OREOA-AI - execution hors ligne" \
      license="AGPL-3.0 (kit) - licences tierces : voir NOTICE"
