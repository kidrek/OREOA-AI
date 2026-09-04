# Journal — 2026-09-INC-042
 
<!--
Règles :
- Le bloc "État courant" est le SEUL réécrit par l'agent (à la fin de chaque session).
  C'est ce qu'il relit en priorité à `/analyse` ; il doit tenir en une dizaine de lignes.
- Tout le reste est en ajout seul (append-only), horodaté en UTC, par session.
- Une entrée = un fait, une piste, une action ou une décision. Jamais de prose libre.
- Une piste ne devient un constat (finding dans case.yaml) que sur validation de l'analyste.
- Chaque affirmation technique pointe vers une preuve : id d'evidence, artefact, record_id ou timestamp.
- Chaque entrée porte le rôle qui l'a écrite : [ingest] [triage] [analyst] [reviewer] [reporter] [human].
- Les sections "Triage" et "Revue" sont écrites par leurs rôles respectifs, jamais par l'analyst.
-->
 
## État courant
_Mis à jour : 2026-09-03T16:40:00Z — session S2_
 
- **Où on en est** : accès initial confirmé sur WKS-042 (F1). Latéralisation vers SRV-DC01 suspectée, non prouvée.
- **Hypothèses ouvertes** : H1 (phishing Office) — 1 constat pour, 0 contre.
- **Collectes manquantes** : SRV-DC01 Security.evtx (demandée le 03/09).
- **Prochaines étapes** : ingérer SRV-DC01 dès réception ; vérifier persistance sur WKS-042 (Run keys, tâches planifiées).
- **Points d'attention** : horloge de WKS-042 en avance de ~4 min (constaté sur EV-001).
---
 
## Session S1 — 2026-09-03 — prenom.nom
_Modèle : qwen2.5-32b-instruct @ host.docker.internal:1234 — Dossier : INCIDENT_
 
### Ingest
- 10:22Z [ingest] `EV-001` déposée : `WKS-042_velociraptor_offline.zip` (sha256 `ab12…`, 1,8 Go). Voie fast : inventaire OK, Hayabusa OK (37 hits), YARA OK (2 hits), ClamAV OK (0), DuckDB OK. Voie deep : plaso en file (job j-0412).
- 10:31Z [ingest] Inventaire EV-001 : OS windows, 42 artefacts, dont EVTX (Security, System, Sysmon), Amcache, Prefetch, ruches NTUSER/SYSTEM/SOFTWARE. Absent : MFT, mémoire vive. Phase WKS-042 → fast_done.
### Triage
- 10:36Z [triage] Brief `derived/triage/EV-001_brief.md`. 22 hunts par défaut exécutés, 61 détections, scoring v1. Top signaux : (1) powershell -enc enfant de WINWORD, score 92 ; (2) Prefetch RCLONE.EXE, score 74, prévalence 1/1 hôte ; (3) YARA `SUSP_PS1_Encoded` sur `%TEMP%\a.ps1`, score 70. Gaps : MFT absente, Security.evtx de SRV-DC01 absent. Hypothèses candidates : phishing Office (medium), exfiltration rclone (low).
### Pistes
- 10:40Z [P1] Hayabusa niveau *high* : `powershell.exe -enc …` enfant de `WINWORD.EXE`, 2026-08-30T02:14:11Z, Sysmon EID 1. Réf. EV-001. ATT&CK T1059.001. → **validé par l'analyste, devient F1**.
- 10:52Z [P2] Prefetch `RCLONE.EXE-3F2A1B.pf`, première exécution 2026-08-30T02:47Z. Réf. EV-001. Piste exfiltration (T1567.002), **non validée** — aucun trafic réseau observé faute de logs.
- 11:05Z [P3] Connexion réseau sortante vers 10.20.0.10:445 depuis WKS-042 à 02:51Z (Sysmon EID 3). Réf. EV-001. Compatible avec latéralisation SMB.
### Gap analysis
- 11:10Z Pour H1 (DFIQ Q???? — « quel fichier a été ouvert par Word ? ») : artefacts requis `WindowsRecentFileCache` / `OfficeMRU` (ruche NTUSER, présente) → à exploiter en S2.
- 11:12Z Pour P3 : `WindowsEventLogSecurity` sur SRV-DC01 absent → **gap G1 ouvert**, demande transmise à l'analyste.
### Revue
- 11:13Z [reviewer] Revue de P1 avant promotion : 2 record_id cités, 2 résolus. Explication bénigne cherchée (macro d'entreprise signée) : aucune macro signée dans OfficeMRU, prévalence 1/1. Aucune chaîne d'injection dans les champs texte d'EV-001. Verdict : **accept**.
### Décisions analyste
- 11:15Z [human] F1 validé (P1, revue accept). P2 et P3 restent des pistes. Collecte SRV-DC01 demandée à l'équipe terrain.
---
 
## Session S2 — 2026-09-03 — prenom.nom
_Modèle : qwen2.5-32b-instruct @ host.docker.internal:1234 — Dossier : INCIDENT_
 
### Ingest
- 15:02Z `/ingest` : aucune nouvelle archive. EV-001 inchangée (taille + mtime). Rien à faire.
### Pistes
- 15:20Z [P4] OfficeMRU (NTUSER j.dupont) : `Facture_082026.docm` ouvert le 2026-08-30T02:13:48Z depuis `Downloads`. Réf. EV-001. Renforce H1.
- 15:41Z [P5] Run key `HKCU\…\Run\Updater` → `%APPDATA%\svc\upd.exe`, écrit le 30/08 02:16Z. Réf. EV-001. Persistance T1547.001. Hash du binaire non calculable (fichier non collecté) → **gap G2 ouvert**.
### Décisions analyste
- 16:35Z P4 validé → F2 (à reporter dans case.yaml). P5 : demander collecte de `upd.exe` avec la prochaine passe Velociraptor.

