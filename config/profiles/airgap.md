# Profil de deploiement - air-gap

Application quand le laptop est isole du reseau. Tout le necessaire est apporte par media amovible.

**Procedure complete de deploiement (preparation du bundle, import, LLM local, recette) : [docs/DEPLOY.md](../docs/DEPLOY.md). L'agent peut te guider pas a pas (competence `skills/deploiement.md`).**

## Contenu du bundle (prepare sur une machine connectee)

```bash
# Image d'outils
docker build -t oreoa-ai-tools:1.1.0 .
mkdir -p tools
docker save oreoa-ai-tools:1.1.0 | gzip > tools/oreoa-ai-tools-1.1.0.tar.gz

# Modele LLM (exemple Ollama)
ollama pull <modele>
# les blobs sont dans /usr/share/ollama/.ollama/models (a copier)
```

## Installation sur le laptop isole

```bash
docker load < tools/oreoa-ai-tools-1.1.0.tar.gz
# importer les modeles Ollama depuis le media
python3 scripts/doctor.py check && python3 scripts/doctor.py test
```

Le chemin `tools/oreoa-ai-tools-<tag>.tar.gz` est la convention attendue par `doctor.py fix` (provisioning autonome) - il detecte le bundle et charge l'image sans reseau, apres verification de la barriere d'espace disque.

## Regles

1. Aucun reseau configure pendant l'investigation
2. Les conteneurs s'executent avec `--network none` (regle par defaut du kit)
3. Les echanges d'affaires s'effectuent par media amovible, avec empreintes SHA256 verifiees a l'import
4. Le bundle outils est reconstruit a chaque montee de version du kit, jamais patche a la main
5. **Tout bundle distribue (media amovible, partage) doit etre accompagne de `docs/NOTICE` et `docs/licences-image.txt`** - distribution binaire = obligation de mention des licences tierces embarquees
