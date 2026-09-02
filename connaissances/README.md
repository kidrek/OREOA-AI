# Base de connaissances

Cette dossier regroupe les connaissances appliquees par l'agent en mode guidance : comment capturer la memoire volatile, comment acquerir un disque, comment conduire une reponse a incident en direct, et les specifics Windows et Linux.

## Organisation

| Dossier | Contenu |
|---------|---------|
| `acquisition/` | capture RAM, acquisition disque, live response |
| `windows.md` | specifics Windows (artefacts, journaux, structure) |
| `linux.md` | specifics Linux (journaux, wtmp/btmp, structure) |

## Principe

En mode guidance, l'agent ne pilote pas les outils : il fournit a l'analyste les actions a executer, dans l'ordre de la methodologie, et verifie les resultats retournes. Toutes les collections documentees ici sont exploitables hors ligne.
