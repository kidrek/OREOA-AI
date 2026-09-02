# Template chaine-conservation.md - chaine de conservation des preuves

# Chaine de conservation - <ID>

Affaire : <nom>

## Registre des collections

| # | Collection | Date de reception | Empreinte SHA256 | Emplacement | Commentaire |
|---|-----------|-------------------|------------------|-------------|-------------|
| 1 | <nom> | <date> | <hash> | <emplacement> | <commentaire> |

## Registre des manipulations

| # | Date | Action | Outil (version) | Cible (empreinte) | Operateur | Resultat |
|---|------|--------|-----------------|-------------------|-----------|----------|
| 1 | <date> | <action> | <outil> | <cible> | <operateur> | <resultat> |

---

## Regles

1. **Registre complet** : chaque collection est enregistree des sa reception, avec son empreinte
2. **Manipulations tracees** : chaque action sur une preuve est journalisee (outil, version, cible, operateur)
3. **Original inaltéré** : la preuve originale n'est jamais modifiee ; toute manipulation s'effectue sur copie
4. **Registre append-only** : la chaine de conservation s'ecrit uniquement en ajout
