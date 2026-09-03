# Skill deploiement - Guidage du deploiement du kit

## Mission

Accompagner l'analyste pas a pas dans le deploiement du kit sur un laptop, depuis un OS vierge jusqu'a la premiere affaire, en profil en-ligne ou air-gap. Le protocole de reference est `docs/DEPLOY.md` - cette competence definit le comportement de guidage.

## Premiere regle

Lire `docs/DEPLOY.md` integralement avant de guider. Le guide est la source de verite du contenu (commandes, seuils, configurations LLM) ; cette competence definit la maniere de conduire.

## Diagnostic initial (avant toute action)

Determiner l'etat reel du laptop et annoncer l'etape de reprise :

1. **Profil** : en-ligne ou air-gap ? (question a l'analyste)
2. **OS** : Debian/Ubuntu ? version ? (`cat /etc/os-release`)
3. **Avancement reel**, verifie par l'agent ou par questions :
   - Docker installe et demon actif ? (`docker version` / `systemctl is-active docker`)
   - Utilisateur dans le groupe docker ? (`id -Gn | grep docker`)
   - Kit deploye ? (presence de `AGENTS.md` a l'endroit de lancement)
   - Image provisionnee ? (`python3 scripts/doctor.py check`)
   - LLM configure ? (l'agent repond = cloud OK ; sinon curl de sante pour un endpoint local)

## Deroulement (regles du mode guidance)

- **Une action a la fois** - jamais un bloc de dix commandes
- **Commandes pretes a copier** - dans le contexte exact du laptop ; `sudo` explicite quand requis
- **Verification du retour avant de continuer** - l'analyste colle le resultat, l'agent verifie et decide de la suite
- **L'agent execute lui-meme ce qu'il peut** : `doctor check`, `doctor fix`, `doctor test` (permissions autorisees) - et l'annonce
- **Ce qui exige sudo ou interactivite revient a l'analyste** : installation Docker, ajout au groupe, `/connect` (opencode) ou `/login` (claude code)

### Etapes types (en-ligne, OS vierge)

1. Installation Docker (commandes sudo a l'analyste) -> verification `docker version`
2. Ajout au groupe docker -> **rappeler systematiquement : effective a la nouvelle session** -> verification `id -Gn | grep docker`
3. Clone du depot -> verification presence `AGENTS.md`
4. `doctor check` (execute par l'agent) -> lecture des avertissements
5. `doctor fix` (execute par l'agent) -> consigner le digest de l'image dans le journal
6. `doctor test` (execute par l'agent) -> verdict OK = outils qualifies
7. LLM cloud : fournir la commande `/connect` ou `/login` a l'analyste -> la conversation en cours prouve la connexion ; passerelle : bloc provider + cle en variable d'environnement
8. Premiere affaire : `/case "<nom>"` (ou scaffold decrit dans AGENTS.md) -> journal initie

### Etapes types (air-gap, deux temps)

1. **Machine connectee** : guider la preparation - build, `docker save | gzip` vers `tools/oreoa-ai-tools-<tag>.tar.gz`, SHA256 du bundle, modeles LLM (Ollama/vLLM), copie de `docs/NOTICE` et `docs/licences-image.txt` sur le media
2. **Laptop isole** : import de l'archive du depot (empreinte verifiee), `doctor fix` (charge le bundle apres barriere disque), `doctor test`, config LLM local (bloc provider localhost), curl de sante
3. **Rappel permanent** : aucun reseau sur l'isolee pendant l'investigation, conteneurs toujours sans reseau

## Points de vigilance

- **Groupe docker** : n'est actif qu'a l'ouverture d'une nouvelle session - a signaler a chaque fois
- **Barriere d'espace disque** : si `doctor fix` refuse, arreter et aider a liberer l'espace - jamais de contournement des seuils
- **Jamais de patch manuel** de l'image ou du bundle : toute evolution passe par le Dockerfile et le depot
- **Configuration LLM** : suivre l'arbre de decision de `docs/DEPLOY.md` section 5 - cloud (`/connect`), passerelle (fichier), local (fichier + curl de sante)

## Qualification finale

1. `python3 scripts/doctor.py test` -> verdict OK
2. Premier cas concret : creer une affaire de test, importer une collection synthetique, conduire une mini-analyse
3. Consigner la qualification dans le `MEMORY.md` de l'instance (date, commit du depot, digest de l'image, verdict) - **chaque instance trace son propre etat localement**, sans registre central : les instances sont autonomes et ne se voient pas
4. La coherence du parc se garantit par la version : meme commit du depot + meme digest d'image partout (`docs/DEPLOY.md` section 7)
5. **Passer a l'accueil** : presente `docs/DEMARRAGE-RAPIDE.md` (guide succinct) et `docs/GUIDE-UTILISATION.md` - l'analyste lance ensuite son outil agentique directement dans le dossier du kit ; chaque session commence par l'autotest (verdict doctor) puis le routage (guidage ou accueil)
