# Arbres de decision par type d'affaire

Ces arbres guident l'agent dans le choix des collections a exploiter et l'ordre d'analyse, selon le type d'affaire posee au triage.

## Principe general

```
Question posee
    |
    v
Type d'affaire ? ---- intrusion -----> arbre intrusion
    |                 |
    |                 +-- malware --------> arbre malware
    |                 |
    |                 +-- exfiltration ---> arbre exfiltration
    |                 |
    |                 +-- abus interne ---> arbre abus interne
    |                 |
    |                 +-- inconnu --------> collection principale la plus riche, puis type raffine
    v
```

## Arbre intrusion

```
Intrusion suspectee
    |
    +-- Quel actif ? ---- Windows ------> journaux Security + Sysmon, persistent
    |                 +-- Linux --------> auth.log, wtmp/btmp, cron, ssh
    |
    +-- Mode d'entree ?
    |       +-- service expose -> journaux du service (web, ssh, rdp)
    |       +-- credential     -> comptes, journaux d'authentification
    |       +-- phishing       -> artefacts utilisateur, execution
    |
    +-- Signaux : nouveau compte, service cree, tache planifiee,
    |             lateral movement, elevation
    v
Timeline consolidee : entree -> exploration -> persistence -> impact
```

## Arbre malware

```
Malware suspecte
    |
    +-- Première detection ? ---- fichier, processus, reseau, journal
    |
    +-- Comment executé ? ------> utilisateur, service, tache planifiee, exploitation
    |
    +-- Communication ? ---------> C2, exfiltration, lateral movement
    v
Collections : fichiers (quarantaine, temp, persist), process (lign de commande),
              reseau (connexions, DNS), journaux d'execution
```

## Arbre exfiltration

```
Exfiltration suspectee
    |
    +-- Volume transfere ? ------> reseau (connexions, DNS, volumes)
    +-- Destination ? ------------> cloud, service de transfert, media amovible
    +-- Comptes utilises ? ------> comptes de service, comptes utilisateurs
    v
Sources : journaux reseau, journaux d'application, artefacts de service
```

## Arbre abus interne

```
Abus interne suspecte
    |
    +-- Quel compte ? -----------> journaux d'authentification, sessions
    +-- Quel actif ? ------------> fichiers, bases, messagerie, impression
    +-- Quelle periode ? --------> timeline des actions du compte
    v
Sources : journaux d'acces, journaux d'application, artefacts utilisateur
```

## Arbre memoire volatile

Applique quand un dump RAM fait partie des collections (type memoire au manifest) :

```
Dump RAM disponible (hash au manifest)
    |
    +-- Symboles disponibles ? --- non ----> ecart documente, exploitation suspendue
    |                           +-- oui ---> sequencement windows.* ou linux.*
    |
    +-- Inventaire : pslist + psscan (ecart = SF-M-001, processus masque)
    +-- Execution : cmdline, consoles (SF-M-004, SF-M-005)
    +-- Injection : malfind, vadinfo, dlllist (SF-M-002, SF-M-003)
    +-- Reseau : netscan (SF-M-006) - croiser avec les journaux de la machine
    +-- Persistance : svcscan (SF-M-008) - croiser avec SF-W-001
    +-- Credentials : artefacts d'outils de vol (SF-M-007) - croiser avec SF-W-030/031
    v
Conclusions sourcees : hash du dump + plugin + sortie ; chaines C-M-01, R-04, R-05
```

Regles : la RAM est une collection de confirmation et de reconstruction, elle ne remplace jamais l'evenementiel ; les ecarts (symboles absents, dump partiel) sont documentes, jamais combles.

## Arbre image disque

Applique quand une image disque (raw, dd, E01) fait partie des collections (type disk au manifest, `size_bytes` consigne) :

```
Image disque disponible (hash au manifest)
    |
    +-- disk.py info : format, partitions, filesystems, barriere 3x
    +-- disk.py verify : integrite (+ metadonnees E01 si EWF)
    |
    +-- AFF4 ? -----------------------------------> ecart documente (hors perimetre v2.0)
    +-- Composite (LVM/RAID) ou chiffre ? ---------> ecart documente, jamais contourne
    |
    +-- Super-timeline : log2timeline sur image (partitions auto) puis psort filtre
    |       +-- executions (Prefetch, SF-D-002), persistance (registre, SF-D-003)
    |       +-- timestomping ($MFT, SF-D-001), perte de visibilite (USN, SF-D-010)
    |
    +-- Listing : disk.py listing (fichiers supprimes SF-D-004, depots SF-D-005, ADS SF-D-006)
    |
    +-- Extraction ciblee : referentiels.py artifacts paths -> disk.py extract
    |       +-- ruches -> regipy (comptes/services SF-D-007, USB SF-D-008, UserAssist SF-D-009)
    |       +-- executables/documents -> yara + analyse de contenu
    v
Conclusions sourcees : hash de l'image + chemin + inode + sha256 extrait ; chaine C-D-01
```

Regles : exploitation sans montage (jamais de root, jamais de mount) ; barriere 3x avant super-timeline ; les extraits sont empreintes et journalises ; AFF4 et volumes hors perimetre restent en attente dans le manifest.

## Regles de priorite multi-collections

1. **Collection principale d'abord** : la collection identifiee au triage comme principale est traitee en premier
2. **Croisement ensuite** : les autres collections servent a confirmer ou infirmer
3. **Ecart documenté** : tout ecart (source absente, periode muette) est documenté, jamais comblé par speculation
4. **Timeline consolidee** : fusion horodatee de toutes les collections, chaque evenement sourcé
5. **Hypotheses testables** : chaque hypothesis doit pouvoir etre validee ou invalidee par un artefact

## Mode guidance

En mode guidance, l'agent ne pilote pas les outils : il fournit a l'analyste les actions a executer, dans l'ordre de la methodologie, et verifie les resultats retournes. Le workflow est le meme, seuls les acteurs changent.

Voir `skills/guidance.md` pour les regles detaillees du mode guidance.
