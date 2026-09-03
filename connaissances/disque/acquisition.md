# Acquisition des images disque (formats et chaine de conservation)

## Principe

L'image disque est une collection d'affaire deposee par l'analyste dans `00_evidence/images/` (ou importee depuis un chemin externe). Le kit ne collecte pas lui-meme : il exploite des images deja acquises par les outils de l'analyste. L'acquisition sort du perimetre d'execution du kit (outils amont documentes ici, guidage en mode guidance via `skills/guidance.md`).

## Formats supportes (v2.0)

| Format | Extensions | Exploitation kit | Notes |
|--------|-----------|------------------|-------|
| raw / dd | `.raw`, `.dd`, `.img` | directe (TSK, plaso) | image brute secteur par secteur, eventuellement partitionnee (MBR/GPT) |
| EWF / E01 | `.E01`, `.e01` | directe (TSK via libewf, plaso via libewf-python) | conteneur EnCase : compression, segments, metadonnees d'acquisition, digest MD5 embarque |
| AFF4 | `.aff4` | **ecart documente** | reconnu a l'ingestion, consigne en attente dans le manifest, jamais exploite en speculation |

Cas particulier `.raw` : l'extension sert aussi aux dumps memoire. L'ingestion desambigue par magic bytes (signature MBR `55 AA`, entete GPT `EFI PART`, superblock ext `53 EF`) ; en cas de doute, l'analyste tranche et le type du manifest est corrige explicitement (`memory` vs `disk`).

## Outils d'acquisition amont (hors kit, documentes)

| Outil | Plateforme | Sortie | Remarques |
|-------|-----------|--------|-----------|
| dd / dc3dd / dcfldd | Linux | raw | dc3dd journalise le hash a la volee ; prevoir l'espace destination |
| ewfacquire (libewf) | Linux | E01 | compression, segments, MD5 embarque ; outil de reference EWF |
| FTK Imager | Windows | E01, raw | acquisition a chaud possible ; les images a chaud sont documentees comme telles |
| X-Ways / Magnet Axiom | Windows | E01, AFF4 | licence commerciale ; sortie E01 exploitable par le kit |

Regle d'or : l'acquisition se fait sur le systeme eteint (ou disque detache) quand c'est possible ; une acquisition a chaud est documentee dans le journal (contexte, horodatage, outil, coherence attendue avec les autres collections).

## Chaine de conservation (ISO 27037)

1. **Hash a l'ingestion** : `ingest.py` calcule le SHA256 de l'image et le consigne au manifest ; chaque re-scan reverifie l'empreinte (alerte d'integrite si derivation)
2. **E01 : integrite embarquee** : `disk.py verify` lit la taille media, les entetes d'acquisition (case/evidence number, examiner, date) et le digest MD5 embarque par libewf ; le MD5 embarque est un controle secondaire (le SHA256 du fichier reste la reference du kit)
3. **Original immuable** : l'image reste dans `00_evidence/originals/` (ou `00_evidence/images/` pour les gros volumes montes en ro) ; toute manipulation se fait par lecture directe (TSK sans montage) - jamais de modification
4. **Journalisation** : provenance declaree (qui a collecte, avec quel outil, quand), commande exacte et verdict de chaque exploitation
5. **Barriere d'espace disque** : la super-timeline et les extractions doivent tenir a cote de l'image - regle kit : 3x la taille de la plus grande image libres (`seuil_disque_multiplicateur` de `config/tools.yaml`, verifie par `disk.py bodyfile` avant plaso)

## Ingestion en affaire

```bash
# depot dans 00_evidence/originals/ (ou images/ pour les gros volumes), puis
python3 scripts/ingest.py cases/CASE-2026-0042 --scan --provenance "forensic image - FTK Imager 7.x, poste SI-014"
```

Champs manifest ajoutes pour la famille `disk` : `size_bytes` (taille du fichier image), `notes` (ecarts : AFF4 hors perimetre). Le rapprochement artefacts fonctionne aussi sur les images disque (nom de fichier ; l'exploitation ciblee passe par `referentiels.py artifacts paths`, cf. `exploitation-tsk.md`).

## Limites

- **AFF4** : reconnu, consigne, non exploite (v2.0) - ecart documente, jamais exploite en speculation
- **Volumes composites** (LVM, RAID, VSS multiples) : detection possible mais exploitation hors perimetre v2.0 - ecarts documentes au cas par cas
- **Chiffrement** (BitLocker, LUKS) : hors perimetre - le chiffrement est documente (presence detectee), jamais contourne
- **Acquisition logique** (copies de fichiers, exports) : ce ne sont pas des images disque - les traiter comme collections classiques (logs, fichiers)
