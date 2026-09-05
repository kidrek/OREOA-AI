# Catalogue des signaux faibles - Windows

Format de chaque signal : identifiant stable (SF-W-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

## Persistance

### SF-W-001 - Service cree recemment
- artefact : Security.evtx EventID 7045 (System.evtx)
- logique : event 7045 avec ServiceFileName hors `C:\Windows\`
- attaque : T1543.003 (Windows Service)
- severite : elevee
- fiabilite : haute
- faux_positifs : installation logicielle legitime, deploiement GPO
- interpretation : persistance ou execution distante (PsExec cree un service)

### SF-W-002 - Nouvelle cle Run/RunOnce par utilisateur
- artefact : NTUSER.DAT `Software\Microsoft\Windows\CurrentVersion\Run*` (ruche HKCU chargee en session)
- logique : valeur ajoutee post-installation OS, binaire hors `%ProgramFiles%`
- attaque : T1547.001 (Registry Run Keys)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : applications utilisateur legitimes
- interpretation : persistance au niveau session utilisateur

### SF-W-003 - Tache planifiee creee/modifiee
- artefact : Security.evtx 4698/4702, TaskScheduler 106/140
- logique : tache executee sous SYSTEM avec action hors Windows
- attaque : T1053.005 (Scheduled Task)
- severite : elevee
- fiabilite : haute
- faux_positifs : maintenance planifiee, GPO
- interpretation : persistance ou execution periodique malveillante

## Execution

### SF-W-010 - Script PowerShell encodé
- artefact : PowerShell Operational 4104
- logique : `-enc`, `-encodedcommand`, `FromBase64String`, `IEX`/`Invoke-Expression`
- attaque : T1059.001 (PowerShell)
- severite : elevee
- fiabilite : haute
- faux_positifs : scripts d'administration encodes legitimes
- interpretation : execution furtive, telechargement de payload

### SF-W-011 - Executable depuis repertoire temporaire
- artefact : Sysmon 1, Prefetch, Amcache (via NTUSER.DAT/UserAssist pour Explorer)
- logique : chemin contient `\Temp\`, `\AppData\Local\Temp\`, `\Downloads\`
- attaque : T1105 (Ingress Tool Transfer)
- severite : elevee
- fiabilite : haute
- faux_positifs : installateurs utilisateurs legitimes
- interpretation : payload droppé puis execute

## Mouvement lateral

### SF-W-020 - Service cree a distance (PsExec pattern)
- artefact : Security.evtx 7045 + 5140/5145 (SMB) depuis meme source
- logique : service `PSEXESVC` ou nom aleatoire + partage ADMIN$ depuis IP source
- attaque : T1021.002 (SMB/Admin Shares)
- severite : critique
- fiabilite : haute
- faux_positifs : administration legitime documentee
- interpretation : mouvement lateral avec credentials volés

### SF-W-021 - Logon type 3 depuis source inhabituelle
- artefact : Security.evtx 4624 (LogonType 3)
- logique : compte administrateur + logon reseau depuis workstation hors baseline
- attaque : T1021 (Remote Services)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : outils d'administration, scans vulnerabilites
- interpretation : access distant suspect, potentiel mouvement lateral

## Acces aux credentials

### SF-W-030 - Acces memoire de lsass
- artefact : Sysmon 10 (ProcessAccess, TargetImage lsass.exe)
- logique : GrantedAccess `0x1010`, `0x1410`, `0x1fffff` par processus non systeme
- attaque : T1003.001 (LSASS Memory)
- severite : critique
- fiabilite : haute
- faux_positifs : antivirus, EDR legimes
- interpretation : tentative de vol de credentials (Mimikatz et similaires)

### SF-W-031 - Dump via comsvcs.dll
- artefact : Security.evtx 4688 ou Sysmon 1 (CommandLine)
- logique : `rundll32.exe comsvcs.dll MiniDump` + pid lsass
- attaque : T1003.001 (LSASS Memory)
- severite : critique
- fiabilite : haute
- faux_positifs : aucun plausible
- interpretation : dump de LSASS confirme

## Anti-forensique

### SF-W-040 - Journal efface
- artefact : Security.evtx 1102, System.evtx 104
- logique : presence de l'evenement, periode vide subsequente
- attaque : T1070.001 (Clear Windows Event Logs)
- severite : critique
- fiabilite : haute
- faux_positifs : rotation legitime mal configuree
- interpretation : effacement de traces par l'attaquant

## Lien NTUSER.DAT (ruche HKCU)

La ruche `NTUSER.DAT` de chaque utilisateur (`C:\Users\<user>\NTUSER.DAT`, chargee en session) alimente les signaux SF-W-002 (Run/RunOnce), plus :

### SF-W-012 - UserAssist : execution via Explorer
- artefact : NTUSER.DAT `Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist`
- logique : executable inconnu avec compteur d'execution eleve
- attaque : T1204.002 (User Execution)
- severite : moyenne
- fiabilite : moyenne
- faux_positifs : logiciels legitimes
- interpretation : l'utilisateur a lance le programme manuellement (ouverture de piece jointe)

### SF-W-013 - MountPoints2 : peripherique USB inconnu
- artefact : NTUSER.DAT `Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2`
- logique : volume USB non recense dans l'inventaire materiel
- attaque : T1091 (Replication Through Removable Media)
- severite : elevee
- fiabilite : haute
- faux_positifs : cles USB corporates recensees
- interpretation : introduction ou exfiltration par media amovible
