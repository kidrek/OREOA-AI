# Live response - reponse a incident sur systeme vivant

## Principe

La live response collecte les donnees volatiles et semi-volatiles d'un systeme en fonctionnement, avant toute decision d'isolement ou d'arret. Elle suit l'ordre de volatilite et journalise chaque action.

## Ordre de collecte

1. **RAM** : capture memoire (voir `capture-ram.md`)
2. **Etat reseau** : connexions etablies, tables ARP, routes, interfaces
3. **Processus** : liste des processus, lignes de commande, handles
4. **Sessions** : utilisateurs connectes, sessions ouvertes
5. **Journaux** : export des journaux systeme (Security, Sysmon, auth, syslog)
6. **Taches et services** : taches planifiees, services, clefs de persistence
7. **Disque** : acquisition image (derniere action, apres collecte volatile)

## Commandes de reference (Windows)

```powershell
# Etat reseau
netstat -anob
arp -a
route print
ipconfig /all

# Processus
tasklist /v
wmic process get ProcessId,Name,CommandLine

# Sessions
query user
net session

# Taches planifiees
schtasks /query /fo LIST /v

# Services
sc query state= all
```

## Commandes de reference (Linux)

```bash
# Etat reseau
ss -tulnp
arp -n
ip route show

# Processus
ps auxf
lsof -p <pid>

# Sessions
who -u
w

# Journaux
journalctl --since "24 hours ago"

# Taches
crontab -l
ls -la /etc/cron*
```

## Regles

1. **RAM d'abord** : la capture memoire precede toute autre collecte
2. **Ordre de volatilite respecte** : RAM, reseau, processus, sessions, journaux, disque
3. **Empreinte avant envoi** : chaque collection exportee est empreintee
4. **Journal append-only** : chaque action est horodatee dans le journal d'affaire
5. **Pas de reprise d'outils sur le systeme analyse** : les outils sont executes depuis un support externe, jamais installes sur le systeme analyse
