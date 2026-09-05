# Catalogue des signaux faibles - Reseau

Format de chaque signal : identifiant stable (SF-R-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

Pre-requis : capture (pcap/pcapng) importee et hash (type reseau), exploitation tshark + suricata offline selon `connaissances/reseau/exploitation-capture.md`. Une capture ne montre que la periode couverte : l'absence d'evenement hors periode n'est jamais une conclusion.

## Commande et controle

### SF-R-001 - Beaconing periodique
- artefact : capture reseau (connexions repetees, meme destine, intervalles quasi constants)
- logique : n connexions vers la meme IP/domaine avec ecart-type des intervalles faible (< 10 % de la moyenne) et payload HTTP/DNS analogue a chaque cycle
- attaque : T1071.001 (Web Protocols), T1071.004 (DNS)
- severite : critique
- fiabilite : haute
- faux_positifs : supervision (polling), synchronisation mail, mises a jour periodiques legitimes
- interpretation : canal C2 ou exfiltration cadencee ; croiser le domaine avec SF-R-002 et le processus via SF-M-006

### SF-R-002 - Requete DNS vers domaine suspect
- artefact : capture reseau (dns.qry.name, requetes sortantes)
- logique : domaine non connu du parc, recent, a labels aleatoires (longueur/entropie elevee) ou vers un TLD a risque, resolue par une machine qui n'y accedait jamais
- attaque : T1071.004 (DNS), T1568 (Dynamic Resolution)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : CDN/SaaS legitimes non inventories, domaines de campagne marketing
- interpretation : resolution de C2 ; completer par la ou les connexions qui ont suivi

### SF-R-003 - Exfiltration via DNS
- artefact : capture reseau (requetes TXT/NULL, sous-domaines longs encodes)
- logique : requetes vers un meme domaine avec sous-domaines de grande longueur (base32/base64), type TXT/NULL, volume sortant uniquement
- attaque : T1048.003 (Exfiltration Over Unencrypted Non-C2 Protocol: DNS)
- severite : critique
- fiabilite : haute
- faux_positifs : service de télémétrie legitime utilisant des requetes TXT documentees
- interpretation : exfiltration de donnees dans les requetes DNS ; estimer le volume encode

## Transfert et exfiltration HTTP

### SF-R-004 - Echange HTTP clair a caractere exfiltratoire
- artefact : capture reseau (http.host, http.request.uri, volumes POST)
- logique : POST vers service de transfert/stockage public ou domaine non reference, avec volume sortant eleve et contenu hors baseline
- attaque : T1048 (Exfiltration Over Alternative Protocol), T1567 (Exfiltration Over Web Service)
- severite : critique
- fiabilite : moyenne
- faux_positifs : sauvegardes cloud et partages legitimes documentes
- interpretation : exfiltration en clair ; reconstruire le flux et qualifier le contenu si possible

### SF-R-005 - Telechargement d'executable depuis le web
- artefact : capture reseau (fichier transfer, content-type application/*executable*, URI de type depot)
- logique : objet binaire telecharge depuis un domaine non reference, suivi d'une connexion sortante du meme hote (C2)
- attaque : T1105 (Ingress Tool Transfer)
- severite : elevee
- fiabilite : haute
- faux_positifs : installateurs et mises a jour legitimes
- interpretation : ingress d'outil ; croiser avec SF-W-011 (execution depuis temp) et le hash de l'objet si extrait

## Reconnaissance et mouvement lateral

### SF-R-006 - Scan horizontal interne
- artefact : capture reseau (une source, nombreux ports/destines internes, SYN sans etablissement)
- logique : machine touchant un grand nombre de ports ou d'hot internes en fenetre courte, majoritairement sans reponse
- attaque : T1046 (Network Service Discovery)
- severite : elevee
- fiabilite : haute
- faux_positifs : scans de vulnerabilites planifies, supervision reseaux
- interpretation : reconnaissance post-compromission ; identifier le processus local via SF-M-006 si dump RAM disponible

### SF-R-007 - Sessions SMB de mouvement lateral
- artefact : capture reseau (smb2 tree connect vers ADMIN$/C$, ouverture de session NTLM hors baseline)
- logique : acces aux partages d'administration depuis une workstation vers un serveur, hors heures ou hors baseline
- attaque : T1021.002 (SMB/Admin Shares)
- severite : critique
- fiabilite : haute
- faux_positifs : administration legitime documentee
- interpretation : mouvement lateral ; croiser avec SF-W-020 (7045 PSEXESVC) sur la machine destination

## Chiffrement et anonymisation

### SF-R-008 - Canal TLS vers destine inhabituelle
- artefact : capture reseau (tls.handshake.extensions_server_name, volumes, timings)
- logique : SNI non connu du parc, session longue ou volumineuse vers cet SNI, empreinte client (JA3 si disponible) inconnue
- attaque : T1071 (Application Layer Protocol), T1090 (Proxy)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : SaaS legitimes non inventories, mises a jour de navigateurs
- interpretation : canal chiffre potentiel de C2 ; la capture ne livre pas le contenu : les metadonnees (volumes, periodicite, SNI) portent l'analyse

### SF-R-009 - Volume sortant anormal
- artefact : capture reseau (conversations et volumes, `tshark -z conv,tcp`)
- logique : flux sortant vers une destine externe depassant largement la baseline de la machine (volume total, asymetrie sortante)
- attaque : T1041 (Exfiltration Over C2 Channel), T1567 (Exfiltration Over Web Service)
- severite : elevee
- fiabilite : haute
- faux_positifs : sauvegardes cloud, envois de logs centralises, mises a jour massives
- interpretation : exfiltration volumique ; identifier le contenu et le processus local de la source

## Detection par signatures

### SF-R-010 - Alerte suricata (ET Open ou regles kit)
- artefact : eve.json (event_type alert, signature_id, severity, 5-uplet)
- logique : alerte d'une signature de haute severite, verifiee dans la capture par suivi de flux
- attaque : variable (la signature cite son mapping)
- severite : selon la signature (elevee a critique)
- fiabilite : moyenne (depend du triage ET Open et de la verification)
- faux_positifs : propres a chaque signature - le triage (config/suricata/) limite le bruit, la verification par flux est obligatoire
- interpretation : point d'entree analytique ; une alerte n'est pas une preuve, c'est un fil a tirer vers les autres collections
