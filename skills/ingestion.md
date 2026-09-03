# Skill ingestion - Import de collections

## Mission

Integrer les collectes de l'analyste dans le dossier d'affaire : depot, detection de
type, calcul d'empreintes, provenance, rapprochement artefacts, mise a jour du manifest.

## Deux voies d'entree (elles convergent)

1. **Depot manuel (voie normale)** : l'analyste copie ses collectes dans
   `00_evidence/originals/`. L'agent detecte les depots (`/case` ou `/analyse`),
   demande la **provenance** (une ligne : origine des collectes, qui les a copiees),
   puis `python3 scripts/ingest.py cases/<ID> --scan --provenance "<source>"`
2. **Import externe** : collection encore hors de l'affaire -
   `python3 scripts/ingest.py cases/<ID> <chemin>` (copie vers originals/, empreinte,
   manifest). Utile pour un partage reseau ou un dossier de telechargement

## Regles

1. **Originals = depot de l'analyste, immuable apres import** : l'agent n'y ecrit jamais
   ; chaque scan reverifie les empreintes enregistrees - toute derivation est une
   **ALERTE INTEGRITE** (code retour 2) : arret, journal, decision analyste
2. **Empreinte systematique** : chaque collection recoit un SHA256 calcule a l'import,
   avant tout traitement. Un artefact non hash n'est pas une preuve exploitable.
3. **Provenance declaree** : le champ `chemin_original` conserve la source (chemin reel
   en import externe, provenance declaree en depot manuel) - element de chaine de
   conservation (ISO 27037)
4. **Typage declare** : chaque collection recoit un type (journal Windows, journal
   Linux, capture reseau, image memoire, image disque, archive, inconnu)
5. **Rapprochement artefacts automatique** : apres tout import, le champ `artefacts`
   par collection et le champ `referentiels` (versions) sont mis a jour via
   `scripts/referentiels.py` (non bloquant si image absente)

## Procedure (mode scan)

1. Lister `00_evidence/originals/` et identifier les depots non enregistres
2. Demander la provenance a l'analyste si non fournie
3. Executer le scan : empreinte des nouveaux depots, verification d'integrite des
   enregistres, mise a jour du manifest, rapprochement artefacts
4. En cas d'ALERTE INTEGRITE : arret, journalisation, decision de l'analyste
5. Journaliser dans `journal.md` (section Phase 0 : depots, provenance, empreintes)

## Verifications de sortie

- [ ] Depots importes (ou aucun nouveau depot)
- [ ] Provenance declaree et consignee
- [ ] SHA256 calcules et consignes
- [ ] Types detectes (ou marques inconnus)
- [ ] Integrite des enregistres verifiee (zero alerte, ou alertes traitees)
- [ ] Rapprochement artefacts effectue (ou ecart journalise)
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
| `.raw` / `.lime` / `.mem` / `.dmp` | dump memoire | memoire |
| `.raw` (magic disque) / `.dd` / `.img` | image disque brute (MBR/GPT/ext detecte) | disk |
| `.E01` | image disque EnCase (EWF) | disk |
| `.aff4` | image AFF4 - **ecart documente** (hors perimetre v2.0, consigne en attente) | disk |

Cas `.raw` ambigu (memoire vs disque) : l'ingestion sonde les magic bytes (MBR `55 AA`, GPT `EFI PART`, superblock ext `53 EF`) ; en cas de doute, demander a l'analyste et corriger le type du manifest explicitement. Les collections famille `disk` recoivent en plus `size_bytes` (barriere d'espace disque : 3x la plus grande image avant super-timeline, cf. `connaissances/disque/acquisition.md`).
