# Skill analyse - Phases 2 a 5

## Mission

Analyser les collections, identifier les actifs affectes, consolider la timeline, tester les hypotheses et produire les observables.

## Phases couvertes

| Phase | Nom | Produit |
|-------|-----|---------|
| 2 | Analyse initiale | actifs affectes, chronologie initiale |
| 3 | Correlation | croisement multi-collections, timeline consolidee |
| 4 | Investiguer | hypotheses testees, ecarts explores |
| 5 | Observer | tableau des observables (IOC) |

## Regles

1. Toute analyse s'effectue sur des copies, jamais sur les originals
2. Chaque evenement de la timeline cite sa source (collection, artefact, empreinte)
3. Chaque conclusion est sourcee : collection + artefact + empreinte
4. Les hypotheses non validees sont presentees comme hypotheses, jamais comme conclusions
5. Les ecarts (periodes muettes, evenements attendus absents) sont documentes

## Produits attendus

1. **Timeline consolidee** : evenements horodates, sourcés, ordonnés
2. **Actifs affectes** : systemes, comptes, services identifies
3. **Hypotheses** : formulees, testees, validees, invalidees ou non conclues
4. **Observables** : tableau final (type, valeur, contexte, source, confiance)

## Fichiers produits

| Fichier | Contenu |
|---------|---------|
| `02_analysis/timeline/timeline.md` | timeline consolidee |
| `02_analysis/ioc/ioc.md` | tableau des observables |
| `02_analysis/logs/analyse.md` | journal d'analyse |

## Lien avec le catalogue

Les signaux faibles detects lors de l'analyse sont croises avec `catalogue/` :

- `catalogue/windows.md` -- signaux Windows
- `catalogue/linux.md` -- signaux Linux
- `catalogue/memoire.md` -- signaux memoire volatile (SF-M)
- `catalogue/reseau.md` -- signaux reseau (SF-R)
- `catalogue/correlation.md` -- regles de correlation multi-signaux (chaines C-W, C-L, C-M, C-R)

## Exploitation memoire volatile (v1.1)

Lorsqu'un dump RAM est present dans l'affaire (type memoire au manifest) :

1. Suivre le sequencement de `connaissances/memoire/exploitation-volatility.md` (`windows.info` puis inventaire processus, execution, injection, reseau, persistance)
2. Executer via le wrapper : `dt -c <CASE_ID> vol -q -f 00_evidence/originals/<dump> windows.<plugin> > 01_work/memoire/<plugin>.txt`
3. Sorties brutes dans `01_work/memoire/`, extractions d'artefacts dans `00_evidence/exports/` avec SHA256
4. Croiser les signaux detectes avec `catalogue/memoire.md` (SF-M) et les chaines C-M-01 / R-04 / R-05 de `catalogue/correlation.md`
5. Chaque conclusion cite : hash du dump + plugin + fichier de sortie ; symboles absents = ecart documente, jamais de speculation

## Exploitation reseau (v1.2)

Lorsqu'une capture (pcap/pcapng) est presente dans l'affaire (type reseau au manifest) :

1. Suivre le sequencement de `connaissances/reseau/exploitation-capture.md` : vue d'ensemble (conversations), detection suricata (eve.json), extractions tshark ciblees (DNS, HTTP, TLS, SMB), periodicite
2. Executer via le wrapper : `dt -c <CASE_ID> tshark -r 00_evidence/originals/<capture> ... > 01_work/reseau/<extraction>.txt` ; `dt -c <CASE_ID> suricata -r 00_evidence/originals/<capture> -l 01_work/reseau/suricata`
3. Sorties dans `01_work/reseau/`, objets extraits dans `00_evidence/exports/` avec SHA256
4. Croiser avec `catalogue/reseau.md` (SF-R), la chaine C-R-01 et les croisements R-07/R-08/R-09 de `catalogue/correlation.md`
5. Chaque alerte est verifiee par suivi de flux avant d'entrer aux observables ; trafic chiffre = metadonnees seules ; la periode couverte est celle de la capture

## Exploitation des images disque (v2.0)

Lorsqu'une image disque (raw, dd, E01) est presente dans l'affaire (type disk au manifest, `size_bytes` consigne) :

1. Verifier l'espace disponible (regle : 3x la taille de la plus grande image) puis suivre `connaissances/disque/exploitation-tsk.md` : `disk.py info` (format, partitions, filesystems), `disk.py verify` (integrite, metadonnees E01)
2. Super-timeline en premier passe : `dt -c <CASE_ID> log2timeline --storage-file 02_analysis/timeline/disk.plaso 00_evidence/originals/<image>` puis `psort` (cf. `connaissances/disque/exploitation-plaso.md`)
3. Extraction ciblee par artefacts : `referentiels.py artifacts paths <Nom>` -> `disk.py extract` (rapport TSV, SHA256 par fichier) ; analyses specialises sur extraits (regipy pour les ruches, yara pour les signatures)
4. Sorties dans `01_work/disque/`, extraits empreintes ; croiser avec `catalogue/disque.md` (SF-D), la chaine C-D-01 et les croisements R-10 a R-12 de `catalogue/correlation.md`
5. Limites v2.0 documentees : AFF4 en attente, LVM/RAID/VSS et chiffrement hors perimetre - `disk.py info` documente ce qui est detecte, jamais de speculation

## Exploitation des referentiels amont (v1.3)

Le manifest porte le rapprochement automatique des collections avec le referentiel
ForensicArtifacts (champ `artefacts`) et les versions utilisees (champ `referentiels`) :

1. Citer les noms d'artefacts standard dans chaque source d'evenement (timeline, observables, conclusions)
2. Resoudre un artefact en chemins et outils : `dt ... referentiels.py artifacts expand <NomArtefact>` (competence `skills/artefacts.md`)
3. Structurer la phase 4 par les questions DFIQ du scenario choisi au triage : `dt ... referentiels.py dfiq plan <Q-id>` (competence `skills/investigation.md`)
4. Les mappings signal <-> artefact et scenario <-> type d'affaire sont dans `catalogue/artefacts.md` et `catalogue/dfiq.md`
