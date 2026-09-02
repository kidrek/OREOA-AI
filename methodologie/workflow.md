# Workflow d'investigation en 7 phases

Chaque affaire progresse dans `cases/<ID>/` selon les phases suivantes. A chaque phase : criteres d'entree, actions, livrable, criteres de sortie.

## Phase 0 -- Import

**Entree** : collections fournies par l'analyste (fichiers, dossiers, images, captures).

**Actions** :
1. Scan de la collection (contenu, taille, structure)
2. Detection du type d'artefact (journal Windows, journal Linux, capture reseau, image memoire, archive)
3. Calcul SHA256 de chaque collection (original integre, copie de traitement distincte)
4. Enregistrement dans `manifest.yaml`

**Livrable** : `manifest.yaml` complet (collections, hashes, descriptions).

**Sortie** : toutes les collections sont inventoriees, types detectes ou marques inconnus.

## Phase 1 -- Triage

**Entree** : manifest.yaml.

**Actions** :
1. Type d'affaire identifie (intrusion, malware, exfiltration, abus interne, inconnu)
2. Collection principale selectionnee (la plus riche pour la question posee)
3. Collections secondaires listees (appui, correlation)
4. Hypotheses de travail formulees (notees comme hypotheses, jamais comme conclusions)

**Livrable** : section triage du rapport (type, principal, secondaires, hypotheses).

## Phase 2 -- Analyse initiale

**Entree** : collection principale.

**Actions** :
1. Lecture des structures principales (journaux, artefacts)
2. Identification des actifs affectes (systemes, comptes, services)
3. Chronologie initiale des evenements cles
4. Signaux faibles detectes (croisement avec le catalogue)

**Livrable** : section analyse initiale du rapport + premier tableau d'evenements.

## Phase 3 -- Correlation

**Entree** : toutes les collections disponibles.

**Actions** :
1. Croisement multi-collections (meme actif vu de plusieurs sources)
2. Consolidation de la timeline (deduplication, ordre, sources multiples)
3. Ecarts identifies (evenement attendu absent, periode muette)
4. Hypotheses raffinees (sources multiples, coherence verifiee)

**Livrable** : timeline consolidee + tableau des ecarts.

## Phase 4 -- Investiguer

**Entree** : hypotheses de travail + timeline consolidee.

**Actions** :
1. Test de chaque hypothesis contre les artefacts
2. Exploration des ecarts (ce qui devrait etre la et ne l'est pas)
3. Croisement avec le catalogue de signaux (correlations decrochees)
4. Hypotheses validees, invalidees ou non conclues (chaque cas documente)

**Livrable** : resume d'investigation (hypotheses, resultats, sources).

## Phase 5 -- Observer

**Entree** : resultats d'investigation.

**Actions** :
1. Extraction des observables (IP, comptes, fichiers, haches, domaines)
2. Qualification de chaque observable (type, contexte, source, confiance)
3. Tableau final des observables (IOC)

**Livrable** : `02_analysis/ioc/ioc.md` + section observables du rapport.

## Phase 6 -- Rapport

**Entree** : tous les produits d'analyse.

**Actions** :
1. Redaction du rapport selon le template `templates/rapport.md`
2. Verification : chaque conclusion sourcee, chaque collection hashée, chaque phase journalisée
3. Produit final : `02_analysis/report/rapport.md`

**Livrable** : rapport final (complet, executive ou technique selon commande).

## Criteres de sortie d'affaire

Une affaire est close quand :

1. Toutes les phases 0-6 sont completées ou documentées comme bloquées
2. Le rapport final est produit et source
3. La chaine de conservation est complete (toutes collections hashées, tous exports tracés)
4. Le journal d'actions est complet et horodaté
