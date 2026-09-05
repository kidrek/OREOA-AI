# Lecons du kit v2.1 - a reinjecter dans la plateforme v2

Pieges instruits pendant la construction du kit autonome (tag `kit-v2.1`,
journal complet dans son `MEMORY.md`). Chacun reste applicable a la plateforme
v2 (workers conteneurises, mappings, corpus synthetique, runtime agentique).

## Parsing et outils

1. **plaso selectionne les parsers SQLite par FINGERPRINT DE SCHEMA**
   (`REQUIRES_SCHEMA_MATCH`) : une base synthetique au schema simplifie n'est pas
   parsee (filestat seul). Repiquer le schema exact depuis la signature du plugin
   (ex. `chrome_history._SCHEMA_67_3`) et reverifier le fingerprint a chaque
   upgrade plaso. (v2.1)
2. **Pin apt avec epoch** : `suricata=7.0.10-1+deb13u4` sans `1:` n'est pas
   resolu (pool Debian trixie) - verifier le pool avant de pinner. (et. 13)
3. **suricata-update 1.3.3 a une CLI a sous-commandes** : `--disable-file`
   n'existe pas -> `suricata-update update --no-test --disable-conf ...`.
   Relever l'aide in-conteneur avant de scripter. (et. 13)
4. **suricata 7 rejette `nocase` redondant** sur les buffers deja normalises
   (`http.host`). (et. 13)
5. **Fichiers de regels illisibles = regles silencieusement non chargees** :
   `/var/lib/suricata/rules` en root:root 750 pour un daemon lance par
   l'analyste - chmod 644/755 bake obligatoire. Un test de recall detecte ce
   defaut, pas un check de presence de fichiers. (et. 13)
6. **log2timeline ecrit son log dans le CWD** : en docker run sans `-w`, le log
   pollue le montage courant ; fixer `-w /tmp` ou l'equivalent worker. (v2.1)
7. **SQLite lecture seule + WAL** : ouvrir en ro avec fallback `immutable=1`,
   sinon la connexion echoue sur des journaux WAL actifs. (v2.1)
8. **pyewf compile sans zlib dans l'image** : lecture E01 OK, ecriture E01
   impossible in-image - les E01 de test se produisent sur l'hote ou viennent de
   preuves reelles. (v2.0)
9. **Wheels natifs de plaso (libewf, libbde...) exigent une chaine de
   compilation** pip : build-essential + python3-dev puis purge apres. (build initial)

## Docker et build

10. **Le groupe docker n'est effectif qu'a l'ouverture d'une nouvelle session**
    utilisateur - planifier les travaux docker en consequence (ou session
    reinitialisee). (v1.1)
11. **LABEL en fin de Dockerfile** : les changements de metadonnees
    (renommage, version) restent instantanes, le cache apt/pip est preserve. (v1.0->v1.1)
12. **Cache-bust cible** : un ARG passe dans un `echo` de la couche vise
    (referentiels) rafraichit cette seule couche sans reconstruire apt/pip/suricata. (v1.3)

## Runtime agentique

13. **Ne jamais coupler un lanceur au runtime de l'agent** : `agent.sh` utilisait
    `opencode tui --prompt`, sous-commande inexistante - le kit a supprime tout
    lanceur au profit du contrat AGENTS.md lu par l'outil agentique. La v4 fait
    de meme (`make runtime-config` genere la config, le runtime est un hote). (lancement simplifie)
14. **Marqueurs de generation stables** : renommer un marqueur de bloc genere
    (`artefacts`) a casse la preservation d'un mapping lors d'une regen - les
    marqueurs utilises par des traitements sont figes et commentes dans le code. (v1.4)
15. **Tuple destructure a l'envers dans un generateur** : valider l'ordre des
    colonnes des generateurs contre les attentes du parser (test de va-et-vient). (v2.1)

## Methode de qualification

16. **Tester le recall ET le bruit** : un jeu de preuves propre (clean.pcap /
    clean host) doit produire zero alerte au-dessus de `low` - sinon le triage
    initial des regles est insuffisant. (v1.2, repris en T2/T0 v4)
17. **Reverification d'integrite systematique** : re-hasher les preuves a chaque
    re-scan ; toute derivation = arret + journal + decision. (principe kit, repris en regles delta v4)
18. **Une etape non journalisee est une etape perdue** : MEMORY.md lu en debut
    de session, mis a jour a chaque etape, fenetre de contexte geree aux
    frontieres d'etapes. (methode kit, conservee dans AGENTS.md v2)
