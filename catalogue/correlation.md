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

## Correlations croisees multi-plateformes

| Chaine | Signaux | Signification |
|--------|---------|---------------|
| R-01 | SF-W-030 (lsass) + SF-L-010 (sudo) sur machine adjacente | propagation des credentials volees |
| R-02 | SF-W-013 (USB inconnu) + SF-W-002 (Run par utilisateur) | introduction par media amovible |
| R-03 | SF-W-040 (effacement journal) + periode muette dans toute autre collection | incident majeur, investiguer les sources externes (SIEM, sauvegardes) |

## Regles d'usage

1. Un signal isole de severite elevee declenche la verification des chaines possibles, jamais une conclusion immediate
2. Une chaine complete avec sources multiples fonde une conclusion de rapport (chaque maillon cite)
3. Un maillon manquant est documente comme ecart, la conclusion reste conditionnelle
4. Les faux positifs de chaque signal sont verifies avant toute correlation
