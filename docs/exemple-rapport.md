# Rapport d'investigation -- CASE-TEST-0001

Affaire : Affaire de test E2E
Periode : 2026-08-30 02:00 -- 2026-08-30 02:20 (fenetre des evenements synthetiques)
Date : 2026-09-02
Format : full
Nature : donnees 100% synthetiques (IP RFC 5737, comptes fictifs) -- sert d'exemple de rendu du kit

## 1. Resume executif

L'investigation des collections de test montre deux chaines de compromission conformes au catalogue de signaux faibles du kit :

1. Cote Linux (chaine C-L-01) : brute force SSH depuis une source externe (14 echecs en 5 minutes), succes d'authentification immediatement suivi de telechargement et execution d'un script en root, creation d'un compte de persistance et d'un job cron, puis purge partielle des journaux.
2. Cote Windows (chaine C-W-01) : execution d'un binaire depuis le repertoire Temp d'un utilisateur, creation d'un service de persistance hors repertoire standard, acces memoire a lsass par ce service, puis service de type PsExec suggérant un mouvement lateral, et effacement du journal Security.

Aucune de ces observations ne provient de donnees reelles : cette affaire sert uniquement d'exemple de rendu et de test de regression du kit.

## 2. Description de l'affaire

- Contexte : validation de bout en bout du kit sur donnees synthetiques
- Question posee : le kit produit-il une investigation et un rapport conformes a la methodologie
- Perimetre : artefacts Windows (Security, Sysmon, System) et journaux Linux (auth, syslog)
- Referentiels : ISO 27037, ISO 27035, ISO 27043, NIST SP 800-86

## 3. Procedure suivie

| Phase | Actions | Collections exploitees | Outils |
|-------|---------|------------------------|--------|
| 0. Import | scan, typage, SHA256 | auth.log, syslog, security.jsonl | scripts/ingest.py |
| 1. Triage | typage intrusion, collection principale auth.log | idem | agent (skill triage) |
| 2-5 | detection signaux, correlation, observables | idem | agent (skill analyse) + catalogue |
| 6 | redaction du rapport | idem | agent (skill reporting) |

## 4. Inventaire des collections

| Collection | Type | SHA256 | Description |
|-----------|------|--------|-------------|
| auth.log | .log | voir manifest.yaml | journal SSH/sudo synthetique |
| syslog | .log | voir manifest.yaml | journal cron/systemd synthetique |
| security.jsonl | .json | voir manifest.yaml | evenements Windows synthetiques |

## 5. Actifs affectes

| Actif | Type | Role | Source |
|-------|------|------|--------|
| SRV-WEB01 (198.51.100.10) | serveur Linux | cible du brute force SSH | auth.log |
| SRV-WEB01 (compte admin) | compte | compte compromis | auth.log |
| SRV-WEB01 (compte svcbackup) | compte | compte de persistance cree | auth.log |
| WIN-SRV01 (jdupont) | poste Windows | execution initiale invoice.exe | security.jsonl |
| WIN-SRV01 (service WinDefendUpd) | service | persistance malveillante | security.jsonl |

## 6. Timeline consolidee

| Horodate | Evenement | Source |
|----------|-----------|--------|
| 02:00:00 | debut du burst de 14 echecs SSH depuis 203.0.113.77 sur le compte admin | auth.log |
| 02:05:00 | succes d'authentification SSH du compte admin depuis la meme source | auth.log |
| 02:05:30 | wget d'un script depuis la source attaquante vers /tmp/st.sh (sudo root) | auth.log |
| 02:05:35 | chmod +x puis execution de /tmp/st.sh | auth.log |
| 02:06:00 | creation du compte svcbackup (UID 1002, shell bash) | auth.log |
| 02:06:20 | job cron execute sous root depuis /tmp | syslog |
| 02:08:20 | purge de /var/log/auth.log par root | syslog |
| 02:00:00* | execution de invoice.exe depuis AppData\Local\Temp (utilisateur jdupont) | security.jsonl |
| 02:02:00* | creation du service WinDefendUpd pointant vers Windows\Temp\svchosts.exe | security.jsonl |
| 02:10:00* | acces memoire lsass (GrantedAccess 0x1010) par svchosts.exe | security.jsonl |
| 02:15:00* | creation du service PSEXESVC (pattern mouvement lateral) | security.jsonl |
| 02:20:00* | effacement du journal Security (event 1102) | security.jsonl |

Note : les horodates marques * sont ceux des evenements Windows synthetiques, alignes sur la meme fenetre de test ; les deux chaines sont independantes dans les donnees de test.

## 7. Observables

| Type | Valeur | Contexte | Source | Confiance |
|------|--------|----------|--------|-----------|
| ip | 203.0.113.77 | source du brute force et du telechargement | auth.log | elevee |
| compte | admin | compte compromis par brute force | auth.log | elevee |
| compte | svcbackup | compte de persistance cree | auth.log | elevee |
| fichier | /tmp/st.sh | stager telecharge et execute | auth.log, syslog | elevee |
| fichier | C:\Users\jdupont\AppData\Local\Temp\invoice.exe | execution initiale | security.jsonl | elevee |
| fichier | C:\Windows\Temp\svchosts.exe | binaire de persistance, accede a lsass | security.jsonl | elevee |
| service | WinDefendUpd | service de persistance | security.jsonl | elevee |
| service | PSEXESVC | indicateur de mouvement lateral | security.jsonl | moyenne |

## 8. Hypotheses

| Hypothese | Statut | Sources |
|-----------|--------|---------|
| Brute force SSH reussi (C-L-01 complete) | validee | auth.log (SF-L-001, SF-L-002, SF-L-010, SF-L-011, SF-L-020, SF-L-021) |
| Compromission par piece jointe puis mouvement lateral (C-W-01) | validee partiellement : chaine complete jusqu'au service PsExec, destination du mouvement lateral hors perimetre des collections | security.jsonl (SF-W-011, SF-W-001, SF-W-030, SF-W-020, SF-W-040) |
| Lien entre les deux chaines (meme campagne) | non conclue : aucun artefact commun dans les donnees de test | -- |

## 9. Conclusion

Les deux chaines de compromission attendues par les jeux de test sont detectees et corrigeablement sourcees : le kit detecte les signaux du catalogue, construit les timelines, qualifie les observables et distingue hypotheses validees et non conclues. La validation E2E de la tranche verticale v1 est reussie.

## 10. Mesures de containment (recommandees pour ce scenario type)

- Blocage de l'IP source 203.0.113.77 en perimetre
- Revocation et rotation des credentials du compte admin
- Isolement des machines concernees

## 11. Remediation

- Suppression du compte svcbackup, du job cron et de la cle Run/service malveillants
- Reinstallation ou restauration des systemes concernes depuis un etat sain
- Rotation de toutes les credentials exposes aux machines compromisees

## 12. Recommandations de securisation

- Desactiver l'authentification SSH par mot de passe au profit de cles, interdire root
- Activer et centraliser Sysmon + journalisation Security (si ce n'est deja fait)
- Regles de detection : integrer les signaux SF du catalogue au SIEM
- Surveillance des creations de comptes, services et jobs cron

## 13. Annexes

- Empreintes completes : cases/CASE-TEST-0001/manifest.yaml
- Journal d'actions : cases/CASE-TEST-0001/journal.md
- Catalogue applique : catalogue/linux.md (C-L-01), catalogue/windows.md (C-W-01)
