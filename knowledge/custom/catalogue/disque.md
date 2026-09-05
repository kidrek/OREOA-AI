# Catalogue des signaux faibles - Disque

Format de chaque signal : identifiant stable (SF-D-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

Pre-requis : image disque (raw, dd, E01) importee et hash (type disk ; AFF4 en ecart documente), exploitation The Sleuth Kit + plaso selon `connaissances/disque/exploitation-tsk.md` et `connaissances/disque/exploitation-plaso.md`. Le perimetre v2.0 couvre les systemes de fichiers NTFS et ext ; volumes composites (LVM/RAID), VSS multiples et chiffrement hors perimetre (ecarts documentes).

## Chronologie et systeme de fichiers

### SF-D-001 - Timestomping (ecarts d'horodatages NTFS)
- artefact : $MFT (plaso super-timeline ou export cible)
- logique : ecart marquant entre $STANDARD_INFORMATION et $FILE_NAME sur un meme fichier (> 1 an sur la creation, ou modification anterieure a la creation) sur un fichier d'interet
- attaque : T1070.006 (Timestomp)
- severite : elevee
- fiabilite : haute
- faux_positifs : outils d'installation qui fixent les dates d'archive, copies depuis des medias conservant les dates
- interpretation : manipulation d'horodatage sur un fichier d'interet ; documenter les quatre dates et chercher l'outil ou le processus source

### SF-D-002 - Executions visibles en Prefetch
- artefact : Windows/Prefetch/*.pf (plaso)
- logique : executable non reference du parc, ou binaire lance depuis un chemin utilisateur/temp, avec compteur d'execution et volumes de pages charges
- attaque : T1204 (User Execution), evidences d'execution
- severite : moyenne (elevee si chemin suspect)
- fiabilite : moyenne
- faux_positifs : logiciels legitimes peu frequents, defragmentation automatique
- interpretation : preuve d'execution meme si le binaire a ensuite ete supprime ; croiser avec SF-D-005 (chemin) et le registre (SF-D-009)

### SF-D-003 - Persistance dans le registre (extraits)
- artefact : ruches SOFTWARE/SYSTEM/NTUSER.DAT extraites (SF/SOFTWARE/Microsoft/Windows/CurrentVersion/Run, services, taches planifiees)
- logique : valeur Run/RunOnce, service ImagePath ou tache planifiee pointant vers un chemin non reference, utilisateur, ou temp
- attaque : T1547.001 (Registry Run Keys), T1543.003 (Windows Service), T1053.005 (Scheduled Task)
- severite : critique
- fiabilite : haute
- faux_positifs : logiciels deployes par GPO non inventories, mises a jour de l'editeur
- interpretation : persistance ; correler l'executable avec SF-D-002 (execution) et SF-D-005 (chemin de depot)

### SF-D-004 - Fichiers supprimes d'interet
- artefact : listing fls (entrees marquees deleted) + extraction icat
- logique : suppression recente d'executables, d'archives ou de journaux dans la fenetre suspecte, notamment dans les chemins de depot habituels
- attaque : T1070.004 (File Deletion)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : nettoyage automatique, fichiers temporaires d'applications
- interpretation : tentative d'effacement ; le contenu recupere (icat) peut etre analyse (yara, chaines) - toute reconstruction est empreintee et journalisee

### SF-D-005 - Executable depose dans un chemin utilisateur
- artefact : super-timeline + listing (Temp, AppData, Public, raccourcis LNK recents)
- logique : binaire cree ou modifie dans un chemin non systeme avec execution subsequente (Prefetch, registre, eventuel service)
- attaque : T1204.002 (Malicious File), T1105 (Ingress Tool Transfer)
- severite : elevee
- fiabilite : haute
- faux_positifs : installateurs utilisateur legitimes
- interpretation : chaine d'infection classique ; remonter a l'entree (piece jointe, telechargement : SF-W-012, SF-R-005)

## Registre et peripheriques

### SF-D-006 - Flux de donnees alternatifs (ADS)
- artefact : listing TSK NTFS (types d'attribut), extraction icat par attribut
- logique : ADS non standard sur un executable ou un document (Zone.Identifier attendu, autres ADS suspects), ou ADS de volume eleve
- attaque : T1564.004 (NTFS File Attributes)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : Zone.Identifier systematique, flux d'applications documentes
- interpretation : dissimulation de contenu ou marqueur de provenance ; extraire l'ADS (icat par inode attribut) et analyser le contenu

### SF-D-007 - Comptes et services locaux modifiees
- artefact : ruches SAM et SYSTEM extraites (comptes locaux, services installes)
- logique : compte local cree ou active hors baseline, service ajoute avec binaire non reference, clef de verrouillage modifiee
- attaque : T1136.001 (Local Account), T1543.003 (Windows Service)
- severite : critique
- fiabilite : haute
- faux_positifs : gestion de parc, compte de service documente
- interpretation : installation ou escalation sur l'hote ; croiser avec l'evenementiel (SF-W-002/SF-W-003) et les reussites d'acces (SF-L-002, SF-W-020)

### SF-D-008 - Historique USB et peripheriques
- artefact : ruche SYSTEM (MountedDevices, USBSTOR, enum Usb), setupapi.dev.log extrait
- logique : peripherique de stockage amovible installe dans la fenetre suspecte, sans declaration ; serial non inventorie
- attaque : T1091 (Replication Through Removable Media), T1052 (Exfiltration Over Physical Medium)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : clavier/souris USB, peripheriques du parc inventories
- interpretation : introduction ou exfiltration physique ; croiser SF-W-013 (USB registre) et les volumes de fichiers crees sur partage reseau

### SF-D-009 - UserAssist et ShellBags (interaction utilisateur)
- artefact : NTUSER.DAT extrait (UserAssist, ShellBags, LNK recents)
- logique : execution d'application graphique, ouverture de dossiers inhabituels (partages reseau, dossiers de depot) par le compte compromis
- attaque : evidences d'interaction utilisateur (T1204)
- severite : faible a moyenne
- fiabilite : moyenne
- faux_positifs : navigation legitime de l'utilisateur
- interpretation : reconstruction du comportement utilisateur ; utile pour patient zero et reponse aux questions DFIQ d'acces initial

### SF-D-010 - Perte de visibilite sur le volume
- artefact : $UsnJrnl (plaso), journaux du volume, trous dans la super-timeline
- logique : purge massive d'entrees USN, effacement de journaux (SF-W-040) accompagne d'ecrasements de fichiers, fenetre temporelle muette
- attaque : T1070 (Indicator Removal), T1562 (Impair Defenses)
- severite : critique
- fiabilite : haute
- faux_positifs : rotation legitime des journaux, nettoyage planifie documente
- interpretation : l'attaquant a reduit la visibilite ; basculer sur les sources hors machine (SIEM, sauvegardes, captures reseau) et documenter la fenetre perdue

## Rattachement aux referentiels amont

- Les signaux SF-D se rapprochent des definitions ForensicArtifacts (WindowsPrefetchFiles, WindowsRegistryFiles, SAM hive, UsbStor...) : mapping maintenu dans `catalogue/artefacts.md`, chemins resolus par `referentiels.py artifacts paths` pour l'extraction ciblee
- Les questions DFIQ d'acces initial, de persistance et d'executions (S1007, S1008, facets Qxxx) structurent l'enquete : mapping `catalogue/dfiq.md`
- Toute conclusion cite : signal SF-D + artefact referentiel + image (hash) + inode/chemin
