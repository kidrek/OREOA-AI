# Profil de deploiement - air-gap

Application quand le laptop est isole du reseau. Tout le necessaire est apporte par media amovible.

## Contenu du bundle (prepare sur une machine connectee)

```bash
# Image d'outils
docker build -t dfir-tools:1.0.0 .
docker save dfir-tools:1.0.0 | gzip > dfir-tools-1.0.0.tar.gz

# Modele LLM (exemple Ollama)
ollama pull <modele>
# les blobs sont dans /usr/share/ollama/.ollama/models (a copier)
```

## Installation sur le laptop isole

```bash
docker load < dfir-tools-1.0.0.tar.gz
# importer les modeles Ollama depuis le media
python3 scripts/doctor.py check && python3 scripts/doctor.py test
```

## Regles

1. Aucun reseau configure pendant l'investigation
2. Les conteneurs s'executent avec `--network none` (regle par defaut du kit)
3. Les echanges d'affaires s'effectuent par media amovible, avec empreintes SHA256 verifiees a l'import
4. Le bundle outils est reconstruit a chaque montee de version du kit, jamais patche a la main
