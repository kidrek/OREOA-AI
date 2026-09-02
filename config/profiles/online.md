# Profil de deploiement - en-ligne

Application quand le laptop a acces a Internet (directement ou par proxy).

**Procedure complete de deploiement (prerequis, provisioning, LLM, recette) : [docs/DEPLOY.md](../docs/DEPLOY.md). L'agent peut te guider pas a pas (competence `skills/deploiement.md`).**

## Configuration LLM

- Provider : endpoint compatible OpenAI (OpenAI, Azure OpenAI, OpenRouter, ou proxy interne)
- Configuration dans opencode.json : `provider`, `apiKey` (variable d'environnement), `baseURL`

## Acquisition de l'image d'outils

```bash
docker build -t dfir-tools:1.0.0 .
# ou via registre interne si disponible
docker pull <registre-interne>/dfir-tools:1.0.0
```

## Verification

```bash
python3 scripts/doctor.py check && python3 scripts/doctor.py test
```
