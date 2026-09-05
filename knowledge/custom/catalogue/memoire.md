# Catalogue des signaux faibles - Memoire volatile

Format de chaque signal : identifiant stable (SF-M-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

Pre-requis : dump RAM importe et hash (type memoire), symboles disponibles pour la version de systeme capturee (voir `connaissances/memoire/exploitation-volatility.md`). Les signaux memoire confirment ou prolongent les chaines evenementielles ; un signal memoire isole declenche la verification des chaines, jamais une conclusion immediate.

## Processus

### SF-M-001 - Processus masque (ecart pslist/psscan)
- artefact : volatility3 windows.pslist + windows.psscan (dump RAM)
- logique : processus present dans psscan absent de pslist/pstree (liaison EPROCESS deconnectee)
- attaque : T1014 (Rootkit)
- severite : critique
- fiabilite : haute
- faux_positifs : processus termines recemment (psscan liste aussi les processus termines : verifier ExitTime)
- interpretation : masquage de processus, croiser avec handles et vadinfo du PID

### SF-M-002 - Code injecte dans un processus
- artefact : volatility3 windows.malfind (VAD RWX, marqueur MZ hors image chargee)
- logique : region memoire RWX contenant un entete PE non rattachee a un module legitime
- attaque : T1055 (Process Injection)
- severite : critique
- fiabilite : haute
- faux_positifs : runtimes auto-modifiables (JIT .NET, Java) - confirmer par contexte et handles
- interpretation : injection de code dans un processus vivant au moment de la capture

### SF-M-003 - Masquage d'execution (process hollowing)
- artefact : volatility3 windows.cmdline + windows.dlllist + windows.vadinfo (image mappee hors chemin affiche)
- logique : ligne de commande etant un binaire systeme mais image mapee ou modules hors `%SystemRoot%`
- attaque : T1055.012 (Process Hollowing)
- severite : critique
- fiabilite : moyenne
- faux_positifs : binaires legitimes deplaces par politique interne
- interpretation : execution masquee sous l'identite d'un processus legitime

## Execution

### SF-M-004 - Ligne de commande anormale en RAM
- artefact : volatility3 windows.cmdline (PEB des processus vivants)
- logique : interpreteur systeme (cmd, powershell, rundll32, regsvr32) avec arguments d'execution distante, encodage ou telechargement
- attaque : T1059 (Command and Scripting Interpreter)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : administration legitime
- interpretation : execution furtive absente des journaux (completer SF-W-010/SF-W-011 si 4688 absent)

### SF-M-005 - Historique console en RAM
- artefact : volatility3 windows.consoles (memoire des conhost)
- logique : commandes executees dans les sessions console, dont reconnaissance, creation de compte, exfiltration
- attaque : T1059.003 (Windows Command Shell)
- severite : elevee
- fiabilite : haute
- faux_positifs : sessions d'administration documentees
- interpretation : actions de l'operateur reconstruites meme apres effacement des journaux (croise R-05)

## Reseau

### SF-M-006 - Connexion externe active non journalisee
- artefact : volatility3 windows.netscan (structures TCP/IP du noyau)
- logique : socket externe hors baseline, possedee par un processus suspect ou non rattachee a un service documente
- attaque : T1071 (Application Layer Protocol)
- severite : critique
- fiabilite : moyenne
- faux_positifs : flux legitimes (cloud, MDM) - verifier le PID proprietaire
- interpretation : canal C2 ou exfiltration vivant au moment de la capture ; completer avec la capture reseau quand disponible (v1.2)

## Credentials

### SF-M-007 - Outil de vol de credentials identifie en RAM
- artefact : windows.pslist + windows.cmdline + regions memoire (malfind/strings) du processus
- logique : processus ou ligne de commande caracteristique d'un outil de dumping (acces lsass, MiniDump comsvcs, mimikatz et derives)
- attaque : T1003 (OS Credential Dumping)
- severite : critique
- fiabilite : haute
- faux_positifs : outils de sauvegarde/EDR legitimes documentes
- interpretation : confirmation en RAM des signaux SF-W-030/SF-W-031 ; considerer tous les actifs partageant ces credentials comme exposes

## Persistance

### SF-M-008 - Service vivant inconnu
- artefact : volatility3 windows.svcscan (services actifs a la capture)
- logique : service actif dont le binaire est hors `C:\Windows\` et non rattache a une installation documentee
- attaque : T1543.003 (Windows Service)
- severite : elevee
- fiabilite : haute
- faux_positifs : services legimes peu documentes - verifier la signature du binaire
- interpretation : confirmation en RAM des signaux SF-W-001 (evenement 7045)

## Linux

### SF-M-020 - Module noyau suspect (Linux)
- artefact : volatility3 linux.lsmod (liste des modules charges dans le dump)
- logique : module hors liste blanche du parc, ou incoherence entre modules declares et structures noyau
- attaque : T1014 (Rootkit)
- severite : critique
- fiabilite : moyenne
- faux_positifs : drivers materiels legimes, modules de securite (apparmor, selinux)
- interpretation : rootkit LKM potentiel ; conditionne aux symboles noyau du dump (ecart documente sinon)

### SF-M-021 - Processus masque (Linux)
- artefact : volatility3 linux.pslist vs linux.pstree (liaison PID et parente)
- logique : PID visible dans un inventaire, absent de l'autre, ou parente impossible
- attaque : T1014 (Rootkit)
- severite : critique
- fiabilite : moyenne
- faux_positifs : processus courts termines pendant la capture
- interpretation : masquage de processus en espace noyau ; croiser avec la chaine C-L-01
