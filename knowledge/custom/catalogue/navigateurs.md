# Catalogue des signaux faibles - Navigateurs

Format de chaque signal : identifiant stable (SF-B-NNN), severite, confiance, artefact source, logique de detection implementable, mapping MITRE ATT&CK, faux positifs, interpretation enquete.

Pre-requis : base de profil importee et hash (cf. `connaissances/navigateurs/profils.md`), exploitation `browsers.py` + plaso selon `connaissances/navigateurs/exploitation-navigateurs.md`. Perimetre v2.1 : Chromium (Chrome/Edge/Brave/Opera), Firefox, Safari (sqlite), IE legacy via plaso ; valeurs chiffrees (cookies, Login Data) hors perimetre - metadonnees seules.

## Transfert et execution par navigateur

### SF-B-001 - Telechargement d'executable par le navigateur
- artefact : History Chromium (table `downloads` + `downloads_url_chains`), Firefox via annotations/plaso
- logique : telechargement complete d'un fichier executable ou script (`target_path` .exe/.msi/.scr/.ps1/.bat/.vbs ou mime application/*) depuis un domaine non reference, suivi ou precede d'une execution (SF-D-002, SF-W-011)
- attaque : T1105 (Ingress Tool Transfer), T1204.002 (Malicious File)
- severite : elevee
- fiabilite : haute
- faux_positifs : installateurs et mises a jour legitimes, documents Office
- interpretation : chaine d'infection classique ; croiser chemin telecharge et Prefetch/registre (SF-D-002/SF-D-003) et l'entree reseau (SF-R-005)

### SF-B-002 - Recherche web a caractere operationnel
- artefact : History Chromium (`keyword_search_terms`), requetes dans les URLs (Firefox/Safari)
- logique : recherche de technique, d'outil, ou de cible (noms d'outils offensive, requetes type "how to disable", enumeration de noms internes) par un compte dont ce n'est pas le profil
- attaque : T1596 (Search Open Technical Databases), preparation d'attaque
- severite : moyenne
- fiabilite : faible a moyenne
- faux_positifs : recherche technique legitime de l'utilisateur, helpdesk
- interpretation : intention a qualifier par le contexte (compte, horaire, suite des actions) - jamais concluante seule

### SF-B-003 - Acces a ressources internes via navigateur
- artefact : visites (toutes bases) : schemas `file://`, UNC convertis, portails et partages internes inhabituels
- logique : visite de `file:///...`, de chemins reseau, ou de services internes jamais touches par ce profil, notamment apres une compromission
- attaque : T1218 (System Binary Proxy Execution via browser), reconnaissance interne
- severite : elevee
- fiabilite : moyenne
- faux_positifs : portails du parc documentes, raccourcis utilisateur habituels
- interpretation : reconnaissance ou pivot par le poste ; croiser avec les journaux d'acces (SF-W-020, SF-L-001)

### SF-B-004 - Sequence phishing (visite puis telechargement immediat)
- artefact : History Chromium (visits + downloads rapproches), eventuellement capture reseau (SF-R-005)
- logique : premiere visite d'un domaine inconnu suivie a moins de 5 minutes d'un telechargement depuis le meme domaine ou un redirecteur
- attaque : T1566.002 (Phishing: Spearphishing Link), T1204.002
- severite : critique
- fiabilite : haute
- faux_positifs : telechargement legitime lors d'une premiere visite (portail documente)
- interpretation : vecteur d'acces initial fort ; remonter l'email (BEC/phishing) et l'execution subsequente (SF-D-005)

## Commande et controle via navigateur

### SF-B-005 - Visite periodique d'une meme URL
- artefact : visites (toutes bases)
- logique : n visites d'une meme URL a intervalles quasi constants (ecart-type faible) vers un domaine non reference, sans interaction utilisateur visible
- attaque : T1071.001 (Web Protocols), T1104 (Multi-Stage Channels)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : webmail, supervision par page, onglet laisse ouvert avec auto-refresh
- interpretation : beaconing navigateur (C2 ou exfiltration via formulaires) ; croiser avec la capture reseau (SF-R-001)

### SF-B-006 - Cookies de session de services sensibles
- artefact : Cookies Chromium/Firefox (metadonnees : hote, nom, duree de vie)
- logique : cookie de session longue duree sur un service d'authentification sensible (SSO, cloud, admin), alors que le service n'apparait pas dans l'usage normal du profil
- attaque : T1539 (Steal Web Session Cookie), T1185 (Browser Session Hijacking)
- severite : elevee
- fiabilite : moyenne
- faux_positifs : sessions legitimes de l'utilisateur, SSO du parc
- interpretation : presence d'une session exploitable (vol par infostealer) - recommander invalidation de session ; valeurs chiffrees non exploitees (ecart)

## Persistance et dissimulation

### SF-B-007 - Extension installee ou activee recemment
- artefact : referentiel `ChromiumBasedBrowsersExtensions` (fichiers), plaso `chrome_extension_activity`, Preferences
- logique : extension non inventoriee installee dans la fenetre suspecte, ou extension a permissions larges (tabs, cookies, webRequest) installee hors store
- attaque : T1176 (Browser Extensions)
- severite : elevee
- fiabilite : haute
- faux_positifs : extensions d'entreprise deployees par GPO
- interpretation : persistance et interception possible de la navigation ; croiser avec l'eventuel traffic (SF-R)

### SF-B-008 - Effacement d'historique
- artefact : History/places (periode couverte + trous), croisement eventiel/reseau/disque
- logique : absence de visites pour une periode ou le systeme etait actif (evenementiel, reseau, MFT), compteur de visites global incoherent, ou base reinitialisee (dates de creationRecentes)
- attaque : T1070.008 (Clear Browser History? T1070 Indicator Removal), T1562
- severite : elevee
- fiabilite : moyenne
- faux_positifs : profil neuf, purge automatique parametree (a documenter)
- interpretation : dissimulation ; la periode perdue se reconstruit par les autres collections (timeline affaire)

### SF-B-009 - Navigation privee suspectee
- artefact : History/places (absence), preferences (mode prive), croisement reseau
- logique : trafic HTTPS vers des domaines de navigation dans la capture (SF-R) sans trace dans la base du meme instant
- attaque : T1564 (Hide Artifacts)
- severite : faible a moyenne
- fiabilite : faible
- faux_positifs : sync non active, profil secondaire, base effacee (SF-B-008)
- interpretation : absence de trace n'est pas une preuve - formuler en hypothese et chercher la confirmation ailleurs (TLS SNI, DNS)

### SF-B-010 - Credentials stockes dans le navigateur
- artefact : referentiel `ChromiumBasedBrowsersLoginDataDatabaseFile`, `ChromiumBasedBrowsersWebDataDatabaseFile` (presence, metadonnees)
- logique : presence d'entrees de credentials/autofill pour des services sensibles sur un poste compromis (contenu chiffre, jamais lu) - l'infostealer confirme (SF-W-030/SF-M-007) rend ces entrees exploitables par l'attaquant
- attaque : T1555.003 (Credentials from Web Browsers)
- severite : elevee
- fiabilite : haute (sur la presence ; l'exfiltration requiert un autre signal)
- faux_positifs : usage personnel documente, poste hors parc
- interpretation : en cas de compromission, rotation imperative des credentials du poste ; l'exploitation des valeurs est hors perimetre kit (ecart)

## Rattachement aux referentiels amont

- Les signaux SF-B se rapprochent des definitions ForensicArtifacts (`BrowserHistory`, `ChromiumBasedBrowsers*`, `Firefox*`, `IE*`) : mapping dans `catalogue/artefacts.md`, chemins resolus par `referentiels.py artifacts paths` pour l'extraction ciblee
- DFIQ : Q1020 (pages visitees) et les questions d'acces initial structurent l'enquete (mapping `catalogue/dfiq.md`)
- Toute conclusion cite : signal SF-B + base (hash) + table/ligne + horodatage UTC
