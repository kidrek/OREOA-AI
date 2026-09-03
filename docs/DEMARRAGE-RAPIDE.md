# Demarrage rapide - kit OREOA-AI

Bienvenue dans ton kit d'investigation numerique. Un agent conduit l'investigation,
tu fournis les preuves et valides chaque etape. Trois gestes suffisent :

## 1. Ouvrir une affaire

```text
/case "Nom de ton affaire"
```

L'agent cree l'arborescence, te demande le contexte de l'incident (ce qui s'est passe,
qui a signale, periode, systemes concernes) et te donne l'identifiant de l'affaire.

## 2. Deposer tes collectes

Copie tes collections (journaux, captures, dumps...) dans le dossier de l'affaire :

```text
cases/<ID>/00_evidence/originals/
```

Signale a l'agent d'ou elles viennent (une ligne suffit) : il les empreinte (SHA256),
les rattache au referentiel d'artefacts et journalise l'import.

## 3. Lancer l'investigation

```text
/analyse
```

L'agent conduit le workflow complet (triage, analyse, correlation, investigation,
observables, rapport) et s'arrete a chaque etape cle pour ta validation. Le rapport
final est sourcee : chaque conclusion cite sa collection, son artefact et son empreinte.

## Utile aussi

- `/case` seul : panorama de tes affaires (reprendre une affaire, en ouvrir une autre)
- `/analyse <chemin>` : importer une collection encore hors de l'affaire
- `/deploy` : deployer le kit sur un autre laptop (en-ligne ou air-gap)
- Mode guidance : capture RAM, acquisition disque, live response - l'agent te guide
  pas a pas quand l'action se fait sur une machine vivante

La sante du kit est verifiee automatiquement a chaque session (doctor). Si quelque
choque manque, l'agent te guide pour corriger avant toute investigation.
