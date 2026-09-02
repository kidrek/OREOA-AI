# Skill ingestion - Import de collections

## Mission

Importer les collections de donnees dans le dossier d'affaire : scan, detection de type, calcul d'empreintes, mise a jour du manifest.

## Regles

1. **Originals intouches** : les fichiers importes dans `00_evidence/originals/` ne sont jamais modifies. Toute transformation produit un fichier dans `00_evidence/exports/`.
2. **Empreinte systematique** : chaque collection recoit un SHA256 calcule a l'import, avant tout traitement.
3. **Typage declare** : chaque collection recoit un type (journal Windows, journal Linux, capture reseau, image memoire, archive, inconnu).

## Procedure

1. Copier la collection dans `00_evidence/originals/` (original, jamais modifie)
2. Calculer le SHA256 de la collection importee
3. Determinter les structures presentes (journaux, formats, periodes couvertes)
4. Enregistrer dans le manifest : nom, type, chemin, empreinte, description
5. Journaliser l'import dans `journal.md` (section Phase 0)

## Verifications de sortie

- [ ] Collection copiee integrale dans `00_evidence/originals/`
- [ ] SHA256 calcule et consigne
- [ ] Type detecte ou marque inconnu
- [ ] Structures presentes identifiees
- [ ] Journal mis a jour

## Types d'artefacts reconnus

| Extension | Description | Collection |
|-----------|-------------|-----------|
| `.evtx` | journal evenements Windows | windows |
| `.evtx.json` | journal evenements Windows (JSON) | windows |
| `.reg` | ruche registre exportee | windows |
| `.pcap` / `.pcapng` | capture reseau | reseau |
| `.log` | journal texte | linux |
| `.json` | journal ou export JSON | linux |
| `.zip` / `.tar.gz` | archive | divers |
