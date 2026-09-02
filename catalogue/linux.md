# Catalogue des signaux faibles - Linux

Format de chaque signal : identifiant stable (SF-L-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

## Authentification

### SF-L-001 - Burst d'echecs d'authentification SSH
- artefact : auth.log (`Failed password for`)
- logique : >= 10 echecs en 5 min pour un meme compte ou depuis une meme IP
- attaque : T1110 (Brute Force)
- severite : elevee
- fiabilite : haute
- faux_positifs : service mal configure, erreur de saisie, scan automate banal
- interpretation : tentative de force brute ou password spray

### SF-L-002 - Succes SSH immediatement apres burst d'echecs
- artefact : auth.log (`Failed password` puis `Accepted password`/`Accepted publickey`)
- logique : sequence echecs multiples puis succes du meme compte/IP dans 10 min
- attaque : T1110 (Brute Force reussi)
- severite : critique
- fiabilite : haute
- faux_positifs : utilisateur qui retrouve son mot de passe
- interpretation : compromission probable du compte

### SF-L-003 - Connexion SSH directe en root
- artefact : auth.log (`Accepted ... for root`)
- logique : `PermitRootLogin` actif + connexion directe depuis IP externe
- attaque : T1078 (Valid Accounts)
- severite : elevee
- fiabilite : haute
- faux_positifs : procedure d'administration legitime (rare)
- interpretation : mauvaise pratique exploitable, usage suspect si externe

### SF-L-004 - Nouvelle cle authorized_keys
- artefact : auditd (`watch /home/*/.ssh/authorized_keys`), ou mtime du fichier
- logique : creation/modification de `authorized_keys` hors provisioning
- attaque : T1098.004 (SSH Authorized Keys)
- severite : critique
- fiabilite : haute
- faux_positifs : rotation de cles documentee
- interpretation : persistance par cle SSH

## Execution

### SF-L-010 - Commandes sudo inhabituelles
- artefact : auth.log (`sudo: USER : COMMAND=...`)
- logique : commande sudo jamais observee dans la baseline (curl, wget, base64, chmod 777, useradd)
- attaque : T1548.003 (Sudo and Sudo Caching)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : operations legitimes hors baseline recente
- interpretation : elevation de privilèges, preparation de persistance

### SF-L-011 - Telechargement et execution chaines
- artefact : auth.log, syslog, history
- logique : `curl|wget` pipe vers `bash|sh`, ou download puis chmod +x puis execution
- attaque : T1059.004 (Unix Shell), T1105 (Ingress Tool Transfer)
- severite : critique
- fiabilite : haute
- faux_positifs : deploiement legitime (Ansible, scripts ops documentes)
- interpretation : installation de malware, stager

### SF-L-012 - Execution depuis /tmp ou /dev/shm
- artefact : auditd execve, syslog, EDR si present
- logique : binaire execute depuis repertoire temporaire non-executable
- attaque : T1059.004 (Unix Shell)
- severite : elevee
- fiabilite : haute
- faux_positifs : rares sur serveur bien configure
- interpretation : payload en memoire, evasion

## Persistance

### SF-L-020 - Nouvelle entree crontab
- artefact : `/var/log/cron`, syslog (`CRON`), auditd
- logique : job cron ajoute hors fenetre de maintenance, vers repertoire non standard
- attaque : T1053.003 (Cron)
- severite : elevee
- fiabilite : haute
- faux_positifs : jobs ops legitimes
- interpretation : persistance ou execution periodique malveillante

### SF-L-021 - Nouveau compte utilisateur
- artefact : auth.log (`useradd`, `adduser`), `/etc/passwd` mtime
- logique : creation de compte avec UID 0, ou compte shell sans justification
- attaque : T1136.001 (Local Account)
- severite : critique
- fiabilite : haute
- faux_positifs : onboarding documente
- interpretation : creation de porte d'entree persistante

## Anti-forensique

### SF-L-030 - Purge de journaux
- artefact : espace journalier vide, syslog `logrotate` hors norme, inodes supprimes (lsof +L1)
- logique : `/var/log/*` tronque (`> /var/log/auth.log`), journalctl vacuum brutal
- attaque : T1070.002 (Clear Linux or Mac Logs)
- severite : critique
- fiabilite : haute
- faux_positifs : rotation legitime
- interpretation : effacement de traces par l'attaquant
