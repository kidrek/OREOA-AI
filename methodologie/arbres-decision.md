# Arbres de decision par type d'affaire

Ces arbres guident l'agent dans le choix des collections a exploiter et l'ordre d'analyse, selon le type d'affaire posee au triage.

## Principe general

```
Question posee
    |
    v
Type d'affaire ? ---- intrusion -----> arbre intrusion
    |                 |
    |                 +-- malware --------> arbre malware
    |                 |
    |                 +-- exfiltration ---> arbre exfiltration
    |                 |
    |                 +-- abus interne ---> arbre abus interne
    |                 |
    |                 +-- inconnu --------> collection principale la plus riche, puis type raffine
    v
```

## Arbre intrusion

```
Intrusion suspectee
    |
    +-- Quel actif ? ---- Windows ------> journaux Security + Sysmon, persistent
    |                 +-- Linux --------> auth.log, wtmp/btmp, cron, ssh
    |
    +-- Mode d'entree ?
    |       +-- service expose -> journaux du service (web, ssh, rdp)
    |       +-- credential     -> comptes, journaux d'authentification
    |       +-- phishing       -> artefacts utilisateur, execution
    |
    +-- Signaux : nouveau compte, service cree, tache planifiee,
    |             lateral movement, elevation
    v
Timeline consolidee : entree -> exploration -> persistence -> impact
```

## Arbre malware

```
Malware suspecte
    |
    +-- Première detection ? ---- fichier, processus, reseau, journal
    |
    +-- Comment executé ? ------> utilisateur, service, tache planifiee, exploitation
    |
    +-- Communication ? ---------> C2, exfiltration, lateral movement
    v
Collections : fichiers (quarantaine, temp, persist), process (lign de commande),
              reseau (connexions, DNS), journaux d'execution
```

## Arbre exfiltration

```
Exfiltration suspectee
    |
    +-- Volume transfere ? ------> reseau (connexions, DNS, volumes)
    +-- Destination ? ------------> cloud, service de transfert, media amovible
    +-- Comptes utilises ? ------> comptes de service, comptes utilisateurs
    v
Sources : journaux reseau, journaux d'application, artefacts de service
```

## Arbre abus interne

```
Abus interne suspecte
    |
    +-- Quel compte ? -----------> journaux d'authentification, sessions
    +-- Quel actif ? ------------> fichiers, bases, messagerie, impression
    +-- Quelle periode ? --------> timeline des actions du compte
    v
Sources : journaux d'acces, journaux d'application, artefacts utilisateur
```

## Regles de priorite multi-collections

1. **Collection principale d'abord** : la collection identifiee au triage comme principale est traitee en premier
2. **Croisement ensuite** : les autres collections servent a confirmer ou infirmer
3. **Ecart documenté** : tout ecart (source absente, periode muette) est documenté, jamais comblé par speculation
4. **Timeline consolidee** : fusion horodatee de toutes les collections, chaque evenement sourcé
5. **Hypotheses testables** : chaque hypothesis doit pouvoir etre validee ou invalidee par un artefact

## Mode guidance

En mode guidance, l'agent ne pilote pas les outils : il fournit a l'analyste les actions a executer, dans l'ordre de la methodologie, et verifie les resultats retournes. Le workflow est le meme, seuls les acteurs changent.

Voir `skills/guidance.md` pour les regles detaillees du mode guidance.
