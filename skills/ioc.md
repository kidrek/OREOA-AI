# Skill ioc - observables de l'affaire

## Mission

Produire et tenir le tableau des observables (IOC) de l'affaire dans `02_analysis/ioc/ioc.md`, a partir du template `templates/ioc.md`, alimente au fil des phases 2-5.

## Types d'observables

| Type | Exemples | Sources typiques |
|------|----------|------------------|
| ip | 203.0.113.77 | capture reseau, netscan RAM, journaux |
| domaine | c2.malveillant.invalid | capture DNS, eve.json |
| url / uri | hxxp://serveur/gate.php | capture HTTP, journaux proxy |
| fichier | C:\Temp\invoice.exe | Sysmon, UserAssist, malfind |
| hash | SHA256 d'un objet extrait | exports d'affaire, objets transferes |
| compte | svcbackup, jdupont | journaux d'authentification, comptes crees |
| regle-kit | sid suricata 1000002 | eve.json (alerte verifiee) |

## Regles

1. **Source obligatoire** : chaque observable cite sa source (collection + artefact + empreinte) - un IOC non source est une hypothese
2. **Confiance declaree** : elevee (sources multiples convergentes), moyenne (source unique verifiee), faible (indicatif, a confirmer)
3. **Separation stricte** : observables confirms et hypotheses non conclues vivent dans deux sections distinctes (template ioc.md)
4. **Verification avant inscription** : une alerte suricata (SF-R-010) n'entre au tableau qu'apres verification par suivi de flux ; une suspicion RAM (SF-M-002) apres contexte du processus
5. **Defanging** : les valeurs reseau sont deguisees dans le rapport (hxxp, [.]) ; les valeurs brutes restent dans les annexes techniques de l'affaire

## Procedure

1. Au fil de l'analyse : extraire les candidats (signaux du catalogue, alertes, artefacts)
2. Verifier chaque candidat (flux, contexte, croissement des collections)
3. Inscrire avec type, valeur, contexte, source, confiance
4. A la phase 5 : consolider, dedupliquer, marquer les chaines reliant les observables
5. Reporter les observables confirms dans la section observables du rapport final (template rapport.md)

## Fichier produit

| Fichier | Contenu |
|---------|---------|
| `02_analysis/ioc/ioc.md` | tableau des observables (confirms + non conclues) |

## Lien avec les catalogues

Les observables naissent des signaux confirmes : `catalogue/windows.md`, `catalogue/linux.md`, `catalogue/memoire.md`, `catalogue/reseau.md` ; les chaines de correlation (`catalogue/correlation.md`) relient les observables entre eux et fondent les conclusions du rapport.
