# Matrice de correlation des signaux faibles

Les conclusions fortes reposent sur des chaines de signaux, pas sur des signaux isoles. Chaque chaine croise plusieurs artefacts et collections.

## Chaines d'investigation Windows

### C-W-01 - Intrusion par piece jointe puis persistance

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | SF-W-012 (UserAssist : execution utilisateur) | T0 |
| 2 | SF-W-011 (executable depuis Temp) | T0 a +5 min |
| 3 | SF-W-001 ou SF-W-003 (service/tache cree) | T0 a +30 min |
| 4 | SF-W-030 (acces lsass) | T+30 min a +2 h |
| 5 | SF-W-020 (service distant PsExec) | suite |

- **Conclusion si chaine complete** : compromission initiale par interaction utilisateur, puis escalade et mouvement lateral
- **Sources requises** : NTUSER.DAT, Sysmon, Security.evtx

### C-W-02 - Effacement de traces

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | activite malveillante confirmee (toute chaine) | T |
| 2 | SF-W-040 (journal efface) | T+1 h max |

- **Conclusion** : l'attaquant a couvert ses traces ; l'investigation doit s'appuyer sur les sources restantes (Sysmon avant effacement, journaux centralises, NTFS)

## Chaines d'investigation Linux

### C-L-01 - Compromission SSH puis installation

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | SF-L-001 (burst d'echecs) | T0 |
| 2 | SF-L-002 (succes apres burst) | T0 a +10 min |
| 3 | SF-L-010 ou SF-L-011 (sudo/telechargement) | +1 min a +1 h |
| 4 | SF-L-020 (cron) ou SF-L-004 (cle SSH) | suite |

- **Conclusion si chaine complete** : brute force reussi, installation de persistance, compromise machine confirmed
- **Sources requises** : auth.log, cron logs, auditd si disponible

### C-L-02 - Escalade par nouveau compte

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | SF-L-010 (sudo inhabituel) | T0 |
| 2 | SF-L-021 (nouveau compte) | T0 a +30 min |
| 3 | connexion du nouveau compte | suite |

- **Conclusion** : persistance par compte dedie cree avec privileges

## Chaines d'investigation memoire

### C-M-01 - Processus malveillant vivant confirme par la RAM

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | SF-M-001 (processus masque) ou SF-M-002 (code injecte) | T capture |
| 2 | SF-M-004 (ligne de commande anormale du meme processus) | T capture |
| 3 | SF-M-006 (connexion externe du processus) ou SF-M-005 (console) | T capture |

- **Conclusion si chaine complete** : processus malveillant vivant au moment de la capture, meme si les journaux de la machine ont ete effaces (croise SF-W-040)
- **Sources requises** : dump RAM (hash au manifest), sorties des plugins dans `01_work/memoire/`, symboles documentes

## Chaines d'investigation reseau

### C-R-01 - Canal C2 confirme par la capture

| Ordre | Signal | Fenetre |
|-------|--------|---------|
| 1 | SF-R-002 (resolution DNS du domaine suspect) | T0 |
| 2 | SF-R-001 (connexions periodiques vers la destine resolue) | T0 a +1 min, puis regularite |
| 3 | SF-R-005 (telechargement d'executable) ou SF-R-008 (TLS vers la destine) | suite |
| 4 | SF-R-010 (alerte suricata verifiee par flux) | a tout moment |

- **Conclusion si chaine complete** : canal de commande et controle actif depuis la machine ; identifier le processus local (SF-M-006 si dump RAM disponible) et le patient zero
- **Sources requises** : capture (hash au manifest), eve.json, extractions tshark ; verification par suivi de flux pour chaque alerte

## Correlations croisees multi-plateformes

| Chaine | Signaux | Signification |
|--------|---------|---------------|
| R-01 | SF-W-030 (lsass) + SF-L-010 (sudo) sur machine adjacente | propagation des credentials volees |
| R-02 | SF-W-013 (USB inconnu) + SF-W-002 (Run par utilisateur) | introduction par media amovible |
| R-03 | SF-W-040 (effacement journal) + periode muette dans toute autre collection | incident majeur, investiguer les sources externes (SIEM, sauvegardes) |
| R-04 | SF-W-030 ou SF-W-031 (dump lsass) + SF-M-007 (outil de vol vu en RAM) | vol de credentials confirme, rotation imperative sur tous les actifs partages |
| R-05 | SF-W-040 (journal efface) + SF-M-005 (historique console en RAM) | traces reconstruites depuis la RAM, chronologie reconstituable |
| R-06 | SF-L-001/SF-L-002 (brute force SSH puis succes) + SF-M-021 (processus masque) | compromission Linux suivie d'un masquage noyau, rootkit a qualifier |
| R-07 | SF-R-007 (SMB ADMIN$ depuis workstation) + SF-W-020 (service distant sur la destination) | mouvement lateral confirmee par deux sources independantes |
| R-08 | SF-M-006 (connexion externe en RAM) + SF-R-001/SF-R-002 (beaconing et DNS dans la capture) | processus et canal C2 rattaches au meme flux |
| R-09 | SF-R-004 ou SF-R-009 (exfiltration) + SF-W-031/SF-M-007 (dump de credentials) | sequence vol de credentials puis exfiltration, rotation imperative

## Regles d'usage

1. Un signal isole de severite elevee declenche la verification des chaines possibles, jamais une conclusion immediate
2. Une chaine complete avec sources multiples fonde une conclusion de rapport (chaque maillon cite)
3. Un maillon manquant est documente comme ecart, la conclusion reste conditionnelle
4. Les faux positifs de chaque signal sont verifies avant toute correlation
