# Capture de memoire volatile (RAM)

## Principe

La memoire volatile est la preuve la plus perishable : elle doit etre capturee en premier, avant toute autre action sur le systeme vivant. La capture s'effectue toujours vers un support externe, jamais vers le disque local du systeme analyse.

## Regles

1. **Ordre de volatilite** : RAM d'abord, puis etat reseau, puis processus, puis disque
2. **Support externe** : la capture s'ecrit sur un support externe (USB, reseau isole), jamais sur le disque du systeme analyse
3. **Empreinte immediate** : le SHA256 du dump est calcule des la fin de la capture
4. **Journalisation** : chaque etape est horodatee dans le journal d'affaire

## Outils et commandes

| Outil | Plateforme | Commande |
|-------|-----------|----------|
| WinPmem | Windows | `winpmem.exe dump.raw` |
| AVML | Linux | `sudo avml /mnt/usb/dump.lime` |
| LiME | Linux (module noyau) | `sudo insmod lime.ko path=/mnt/usb/dump.lime format=lime` |

## Verifications apres capture

1. Le dump est integre (taille coherente, SHA256 calcule)
2. Le dump est copie sur le support externe
3. Le SHA256 est consigne dans le manifest d'affaire
4. La capture est journalisee (heure, outil, version, cible)

## Precautions

1. La capture elle-meme ecrit dans la memoire (driver charge) : la capturer le plus tot possible
2. Verifier l'espace disponible sur le support externe (taille RAM au moins)
3. Ne jamais monter la partition swap du systeme analyse
4. Journaliser chaque etape dans le journal d'affaire
