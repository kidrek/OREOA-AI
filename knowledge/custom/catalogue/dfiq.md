# Referentiel DFIQ (Digital Forensics Investigation Questions)

Referentiel amont (Google DFIQ, Apache-2.0) telecharge et bake dans l'image a chaque
build (`doctor fix`). Corpus : hierarchie scenario -> facet -> question, avec approches
executables quand le corpus en fournit (19 au bake courant) ; tags MITRE ATT&CK sur
les scenarios. Corpus jeune : toute question sans approche se traite par le catalogue
SF et les skills, l'ecart est documente (jamais de speculation).

## Usage (execution conteneurisee via dt)

```
dt python3 /work/scripts/referentiels.py dfiq arbre S1008   # arbre scenario -> questions
dt python3 /work/scripts/referentiels.py dfiq plan Q1020    # plan de reponse + resolution artefacts
dt python3 /work/scripts/referentiels.py dfiq index /work/catalogue/dfiq.md  # regen index
dt python3 /work/scripts/referentiels.py dfiq check          # integrite + coherence
```

## Rattachement aux types d'affaire du triage

| Scenario DFIQ | Type d'affaire (triage) | Signaux/correlations du kit |
|---------------|--------------------------|------------------------------|
| S1001 Data Exfiltration | exfiltration de donnees | SF-R-003/004/009, chaine C-R-01 |
| S1002 Data Infiltration (Insider) | menace interne | SF-W-012/013, SF-L-011, historiques |
| S1003 Suspicious DNS Query (Network, Malware) | C2 / DNS suspect | SF-R-002/003, SF-M-006 |
| S1005 Cloud Project Compromise | hors perimetre v1.x - cadre v2.4 | - |
| S1007 Host Persistence Audit (TA0003) | persistance | SF-W-001/002/003, SF-L-020, SF-M-008 |
| S1008 Lateral Movement (TA0008, Windows) | mouvement lateral | SF-W-020/021, SF-R-007 |

## Regles

1. Le scenario est choisi au triage (skills/triage.md) a partir du type d'affaire et du
   contexte analyste ; les facets servent de checklist d'axes, les questions structurent
   la phase 4 (skills/investigation.md)
2. Chaque question repondue cite sa source (collection + artefact + hash) ; sans donnees
   => ecart documente dans le rapport (section 5)
3. Les approches de type `ForensicArtifact` se resolvent via le referentiel d'artefacts
   (moteur commun : scripts/referentiels.py) - chainage DFIQ -> artefact -> chemins -> dt
4. Question/aspect non couvert par le corpus amont = approche ou question custom dans
   `referentiels-kit/dfiq/` (prefixe d'id `SK`), candidat a contribution amont

<!-- genere:dfiq:debut -->
Index generated from the baked corpus (6 scenarios, 30 facets, 90 questions, 19 approaches) - do not edit this section.

## S1001 - Data Exfiltration [-]
Facets: 7; questions: 33
### F1007 - Are there any indications of anti-forensic efforts?
- Q1024: Was an Incognito/Private browser session used? (approaches: 1)
- Q1028: Was there specialized "anti-forensic" (or "privacy") software on a computer?
 (approaches: 0)
- Q1029: Were any encryption programs used on a computer? (approaches: 0)
- Q1030: Were any security or monitoring agents tampered with or disabled? (approaches: 0)
- Q1032: What actions were taken in an Incognito (or "private") browser session?
 (approaches: 0)
- Q1033: Was shell history cleared? (approaches: 0)
- Q1074: Were any system event logs cleared? (approaches: 2)
### F1008 - Are there signs of staging data for future exfiltration?
- Q1001: What files were downloaded using a web browser? (approaches: 4)
- Q1004: What screenshots were taken on a computer? (approaches: 0)
- Q1005: What files have ever been on a computer? (approaches: 0)
- Q1006: What files are present on a computer? (approaches: 0)
- Q1017: Were any files collected into a container? (approaches: 0)
- Q1034: Was content copied from a file? (approaches: 0)
- Q1035: Were any copies made of sensitive files? (approaches: 0)
- Q1077: Were there bulk downloads from Google Drive? (approaches: 0)
### F1009 - Was any sensitive data sent externally via email?
- Q1016: What files were sent externally via email attachments? (approaches: 0)
- Q1075: Is the recipient account controlled by the sender? (approaches: 0)
- Q1076: Were the files screenshots? (approaches: 0)
- Q1078: Were the files copies? (approaches: 0)
- Q1079: Is there a history of communication with the recipients? (approaches: 0)
- Q1080: How many external recipients does the email have? (approaches: 0)
### F1010 - Was any sensitive data exfiltrated via a physical medium?
- Q1003: What files were copied from a computer to a USB device? (approaches: 0)
- Q1010: What was printed from a computer? (approaches: 0)
### F1011 - Was any sensitive data exfiltrated via a web service?
- Q1007: What files were synced or backed-up to external services? (approaches: 0)
- Q1009: What interactions with external cloud storage sites did the actor have using their web browser?
 (approaches: 0)
- Q1011: What files were sent or received by a chat application? (approaches: 0)
- Q1025: What external accounts has the actor used in their web browser? (approaches: 0)
- Q1038: Were any files sent via CLI utilities? (approaches: 0)
- Q1084: What data was uploaded to a website via a web browser? (approaches: 0)
### F1012 - System Information
- Q1008: What programs are installed on a computer? (approaches: 0)
- Q1081: Does the user have a recently provisioned host? (approaches: 0)
### F1026 - Were any files sent via other network media?
- Q1082: Were any files sent via AirDrop? (approaches: 0)
- Q1083: Were any files sent via Bluetooth? (approaches: 0)

## S1002 - Data Infiltration [Insider]
Facets: 5; questions: 22
### F1001 - Are any ExternalCompany-related files on the actor's assigned Company assets?

- Q1005: What files have ever been on a computer? (approaches: 0)
- Q1006: What files are present on a computer? (approaches: 0)
- Q1014: What files did the actor open on their computer? (approaches: 0)
- Q1027: Are there any sudden changes in the number of files on a device? (approaches: 0)
### F1002 - Has the actor introduced any ExternalCompany files to Company assets via downloading?

- Q1001: What files were downloaded using a web browser? (approaches: 4)
- Q1008: What programs are installed on a computer? (approaches: 0)
- Q1009: What interactions with external cloud storage sites did the actor have using their web browser?
 (approaches: 0)
- Q1015: What syncing activities did external "cloud storage" applications do on a computer?
 (approaches: 0)
- Q1025: What external accounts has the actor used in their web browser? (approaches: 0)
- Q1026: What files were downloaded from messaging apps? (approaches: 0)
- Q1031: How much network traffic was there to/from a machine? (approaches: 0)
### F1003 - Has the actor introduced any ExternalCompany files to Company assets via removable storage devices?

- Q1002: What USB devices were attached to a computer? (approaches: 0)
- Q1012: What files were copied from a USB device to a computer? (approaches: 0)
- Q1013: What files are present on a USB device? (approaches: 0)
### F1029 - Are there any indications of communication with ExternalCompany?
- Q1020: What pages did web browsers visit? (approaches: 2)
- Q1084: What data was uploaded to a website via a web browser? (approaches: 0)
- Q1085: What DNS requests have been made from a system? (approaches: 0)
- Q1086: What web-based email messages were viewed in a web browser? (approaches: 0)
### F1030 - Has the actor connected to any ExternalCompany systems?

- Q1087: Did the user access any common PaaS/SaaS services? (approaches: 0)
- Q1088: Did the user connect to any non-Company systems using the command line?
 (approaches: 0)
- Q1089: Did the user download any Citrix configuration (.ica) files? (approaches: 0)
- Q1090: Did the user interact with any git repositories? (approaches: 0)

## S1003 - Suspicious DNS Query [Network, Malware, Triage]
Facets: 3; questions: 9
### F1004 - What application was responsible for the DNS query?
- Q1018: What process made the DNS query? (approaches: 4)
- Q1073: Have there been any modifications to the "hosts" file? (approaches: 0)
### F1005 - Was a user's web browsing the cause of a given DNS query?
- Q1019: What web browsers were running at a given time? (approaches: 1)
- Q1020: What pages did web browsers visit? (approaches: 2)
- Q1024: Was an Incognito/Private browser session used? (approaches: 1)
- Q1072: Did Chrome's DNS Prefetching cause a DNS query? (approaches: 0)
### F1006 - Was a browser extension responsible for a DNS query?
- Q1021: What Chrome extensions are installed? (approaches: 0)
- Q1022: What actions did a Chrome extension perform? (approaches: 0)
- Q1023: Is a given Chrome extension associated with a given domain? (approaches: 0)

## S1005 - Cloud Project Compromise Assessment [Cloud]
Facets: 6; questions: 14
### F1013 - Has an attacker gained access to the cloud project? (Initial Access)

- Q1039: Are there any detections of exposed service account credentials? (approaches: 0)
- Q1040: Are there any interaction with the cloud project resources from an unknown external IP address (including Tor Exit nodes, C2 tagged addresses)?
 (approaches: 0)
- Q1041: Are there any unexpected successful API calls from an unknown external IP address (including Tor Exit nodes, C2 tagged addresses)?
 (approaches: 0)
### F1014 - Are there any signs of an attacker trying to maintain access to the cloud project? (Persistence)

- Q1042: Are there any APIs recently enabled? (approaches: 0)
- Q1043: Are there any role bindings to cluster admin for anonymous users? (approaches: 0)
- Q1044: Are there any unexpected resources created under the cloud project?
 (approaches: 0)
- Q1045: Are there any unknown accounts created? (approaches: 0)
- Q1046: Are there any unknown role bindings created? (approaches: 0)
### F1015 - Are there any signs of interference with cloud project protective measures? (Defense Evasion)

- Q1047: Are there any suspicious modifications to the cloud project firewall rules/policies?
 (approaches: 0)
- Q1048: Are there any suspicious modifications to the cloud project logging configuration?
 (approaches: 0)
### F1016 - Are there indications of an attacker moving between resources?
- Q1049: Is there an unusual increase of traffic between resource in the cloud project?
 (approaches: 0)
### F1017 - Are there any signs of data exfiltration from resources inside the cloud project? (Data Exfil)

- Q1050: Are there any GCS buckets within the cloud project shared externally?
 (approaches: 0)
- Q1051: Are there any signs of data within the cloud project being transferred externally?
 (approaches: 0)
### F1018 - Are there any detections of potentially suspicious activity related to the cloud project from detection tools?

- Q1039: Are there any detections of exposed service account credentials? (approaches: 0)

## S1007 - Host Persistence Audit [TA0003]
Facets: 7; questions: 21
### F1019 - Was a browser extension used to maintain a foothold?
- Q1021: What Chrome extensions are installed? (approaches: 0)
- Q1052: What browser extensions (non-Chrome) are installed? (approaches: 0)
### F1020 - Are there any interesting logon or boot initialization scripts?
- Q1053: What Launch Agents are configured? (approaches: 0)
- Q1054: What Launch Daemons are configured? (approaches: 0)
- Q1055: What Windows logon scripts are configured? (approaches: 0)
- Q1056: What login hooks are configured? (approaches: 0)
- Q1057: What network logon scripts are configured? (approaches: 0)
### F1021 - Are there any new accounts that have been created?
- Q1058: What domain accounts have been created? (approaches: 0)
- Q1059: What local accounts have been created? (approaches: 0)
### F1022 - Are there any scheduled/automated tasks that ran?
- Q1060: What AT jobs are configured? (approaches: 0)
- Q1061: What Scheduled Tasks are configured? (approaches: 0)
- Q1062: What cron jobs are configured? (approaches: 0)
- Q1063: What periodic scripts are configured? (approaches: 0)
- Q1064: What systemd timers are configured? (approaches: 0)
### F1023 - Are there any suspicious files running at system boot or login autoruns?

- Q1065: What files are referenced in Registry "Run" keys? (approaches: 0)
- Q1066: What items are in startup folders? (approaches: 0)
### F1024 - Has a system process been created or modified?
- Q1067: What system services are installed? (approaches: 0)
- Q1068: When were system services last modified? (approaches: 0)
### F1025 - Are there any indications of hijacking execution flows?
- Q1069: Are there any indications of dylib hijacking? (approaches: 0)
- Q1070: Are there any indications of dylib proxying? (approaches: 0)
- Q1071: Are there any indications of dynamic linker hijacking? (approaches: 0)

## S1008 - Lateral Movement [TA0008, Windows]
Facets: 3; questions: 4
### F1021 - Are there any new accounts that have been created?
- Q1058: What domain accounts have been created? (approaches: 0)
- Q1059: What local accounts have been created? (approaches: 0)
### F1027 - Are the indications of an attacker moving FROM this host to another?

- Q1036: Have there been any executions of PsExec? (approaches: 2)
### F1028 - Are the indications of an attacker moving TO this host?
- Q1037: Have there been any executions of PsExeSrv? (approaches: 3)

<!-- genere:dfiq:fin -->

