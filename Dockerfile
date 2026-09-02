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
 && apt-get purge -y build-essential python3-dev pkg-config \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Utilisateur non root - les fichiers produits appartiennent a l'analyste
RUN useradd -m -u 1000 analyste
USER analyste
WORKDIR /work

# Les volumes d'affaire sont montes a l'execution (00_evidence en ro)
# Pas de reseau par defaut : docker run --network none
LABEL name="oreoa-ai-tools" \
      version="1.0.0" \
      description="Chaine d'outils forensiques du kit OREOA-AI - execution hors ligne" \
      license="AGPL-3.0 (kit) - licences tierces : voir NOTICE"
