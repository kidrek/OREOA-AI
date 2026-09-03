---
description: Ouvrir, switcher ou lister les affaires d'investigation
---
Gestion de l'affaire : $ARGUMENTS

## Comportement selon l'argument

### A. Nom ou identifiant fourni (`/case "Incident serveur web"` ou `/case CASE-2026-0042`)

**Recherche d'affaire existante** (par id exact, sinon par nom) :
- une seule correspondance -> **switch** : charge l'etat complet de l'affaire
  (`manifest.yaml` : statut, collections + artefacts, contexte ; `journal.md` :
  dernieres entrees ; phase courante selon `methodologie/workflow.md` ; produits
  dans `02_analysis/`) et presente un **resume de reprise** : id, nom, statut,
  ce qui a ete fait, phase en cours, prochaine etape. L'affaire devient
  **l'affaire courante de la session** (ancre logique : les commandes suivantes -
  ingest, dt, analyses - s'appliquent a elle, executees depuis la racine du kit
  avec son ID explicite ; jamais de `cd` physique dans le dossier d'affaire)
- plusieurs correspondances -> tableau des candidats (id + nom + statut) et demande laquelle
- aucune -> **creation** (ci-dessous), avec confirmation si l'argument ressemble
  a autre chose qu'un nom (chemin, question...)

**Creation** : scaffold l'affaire sans aucun script, exactement ainsi :
1. `ID` = CASE-<annee>-<numero libre a 4 chiffres> (scanner `cases/`)
2. `mkdir -p "cases/<ID>"/{00_evidence/{originals,exports,images},01_work/tmp,02_analysis/{logs,ioc,report}}`
3. Ecrire `cases/<ID>/manifest.yaml` :

```yaml
affaire:
  id: "<ID>"
  nom: "<nom>"
  date_creation: "<date du jour>"
  statut: ouverte

contexte:
  description: ""
  declarant: ""
  date_signalement: ""
  systemes_concernes: []
  periode_suspecte: { debut: "", fin: "" }
  mesures_deja_prises: []
  contraintes: []

collections: []
```

4. Ecrire `cases/<ID>/journal.md` : titre `# Journal - <ID>`, affaire + date, section
   `## Phase 0 - Import` avec l'entree de creation horodatee
5. Raporter clairement l'ID attribue. L'affaire creee devient l'affaire courante de la session

### B. Apres creation ou switch (dans les deux cas)

1. **Intake de contexte** (uniquement si `contexte` non renseigne) : demande a l'analyste
   s'il a du contexte a partager sur l'incident - question ouverte, relances ciblees si
   apport (description, declarant, periode, systemes concernes, mesures deja prises,
   contraintes), non bloquant si rien (journalise "aucun contexte fourni"). Consigne
   dans la section `contexte` du manifest + entree journal
2. **Detection des depots** : liste le contenu de `00_evidence/originals/` :
   - fichiers presents non encore enregistres au manifest -> demande la **provenance**
     (une ligne : d'ou viennent ces collectes, qui les a copiees) puis propose
     `python3 scripts/ingest.py cases/<ID> --scan --provenance "<source declaree>"`
   - deja enregistres -> rappelle qu'ils sont integres (le scan reverifie leur integrite)
3. Cloture du tour : etat de l'affaire + LA commande pour investiguer quand les collectes
   sont deposees : `/analyse` (ou `/analyse <chemin>` pour une collection hors affaire)

### C. Sans argument (`/case`)

**Panorama des affaires** : tableau lu depuis `cases/*/manifest.yaml`
(id, nom, statut, date, nombre de collections, contexte renseigne ou non)
puis propose : switcher sur l'une (son choix -> comportement A-switch) ou en creer une nouvelle.
Si `cases/` est vide : presente le guide de demarrage `docs/DEMARRAGE-RAPIDE.md` et propose
la creation de la premiere affaire.

## Regles

- Une seule affaire courante par session ; le switch se fait a tout moment par un nouveau `/case`
- Jamais d'ecriture dans `00_evidence/originals/` par l'agent (les depots viennent de l'analyste)
- Toute creation/switch/scan est journalisee dans `journal.md` (append-only, horodate)
