#!/usr/bin/env bash
# agent.sh - lanceur du kit OREOA-AI
# Usage :
#   ./agent.sh [--profil airgap]
# Sequence :
#   1. Preflight connexion LLM (hors agent : sans LLM, l'agent ne peut pas parler)
#      - cloud : identifiants opencode (auth.json non vide)
#      - air-gap : endpoint local joignable (Ollama 11434, vLLM 8000)
#   2. Lancement de l'agent avec un message initial genere selon l'etat reel
#      du kit (scripts/bootstrap_prompt.py) : autotest des outils, puis
#      guidage de deploiement ou accueil avec commande d'analyse.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$KIT_DIR"

PROFIL="online"
if [[ "${1:-}" == "--profil" && "${2:-}" == "airgap" ]]; then
  PROFIL="airgap"
fi

# Endpoint local joignable (python3 urllib, pas de dependance curl)
endpoint_ok() {
  python3 - <<'PY' 2>/dev/null
import sys, urllib.request
for url in ("http://localhost:11434/v1/models", "http://localhost:8000/v1/models"):
    try:
        urllib.request.urlopen(url, timeout=3)
        sys.exit(0)
    except Exception:
        pass
sys.exit(1)
PY
}

# Identifiants cloud opencode presents (auth.json non vide)
auth_ok() {
  local auth="$HOME/.local/share/opencode/auth.json"
  [[ -s "$auth" ]] || return 1
  python3 -c "
import json, sys
try:
    sys.exit(0 if json.load(open(sys.argv[1])) else 1)
except Exception:
    sys.exit(1)
" "$auth" 2>/dev/null
}

llm_connecte() {
  auth_ok && return 0
  endpoint_ok && return 0
  return 1
}

# --- 1. Preflight LLM ---
if ! llm_connecte; then
  echo "Aucun LLM connecte - l'agent ne peut pas demarrer sans modele."
  echo
  echo "Deux options :"
  echo "  1. Cloud (reseau requis) : opencode auth login   # suivre le flux"
  echo "  2. Local / air-gap       : demarrer le serveur (Ollama : ollama serve,"
  echo "     vLLM : vllm serve <modele>) puis configurer le provider -"
  echo "     exemple : config/profiles/opencode-airgap.example.json (voir docs/DEPLOY.md section 5)"
  echo
  echo "Guide complet : docs/DEPLOY.md"
  if command -v opencode >/dev/null 2>&1; then
    rep=""
    read -r -p "Lancer la connexion cloud maintenant ? [o/N] " rep || rep=""
    if [[ "$rep" =~ ^[oO] ]]; then
      opencode auth login || true
      if llm_connecte; then
        echo "Connexion detectee - lancement du kit."
      else
        echo "Connexion non detectee. Connecte un LLM puis relance : ./agent.sh"
        exit 1
      fi
    else
      echo "Relance ./agent.sh une fois le LLM connecte."
      exit 1
    fi
  else
    echo "opencode introuvable : installe un runtime agent (https://opencode.ai) ou utilise claude."
    exit 1
  fi
fi

# --- 2. Lancement avec message initial genere selon l'etat reel ---
PROMPT="$(python3 scripts/bootstrap_prompt.py --profil "$PROFIL")"

if command -v opencode >/dev/null 2>&1; then
  exec opencode tui --prompt "$PROMPT"
elif command -v claude >/dev/null 2>&1; then
  exec claude "$PROMPT"
else
  echo "Ni opencode ni claude trouves : installe un runtime agent (https://opencode.ai)."
  exit 1
fi
