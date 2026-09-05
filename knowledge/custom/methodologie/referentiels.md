# Referentiels normatifs

Referentiels appliques par le kit. Chaque document renvoie au texte normatif de reference.

## ISO/IEC 27037

Identification, collecte, acquisition et preservation des preuves numeriques.

Applique par le kit :

- **Chaine de conservation** : chaque collection est horodatee, identifiee et empreintee (SHA256) des sa reception
- **Preservation** : originals en lecture seule, toute manipulation s'effectue sur des copies tracees
- **Documentation** : chaque action cite collection, outil, version, empreinte

## ISO/IEC 27035

Principes et processus de gestion d'incidents de securite de l'information.

Applique par le kit :

- **Phase preparation** : kit pret (prerequis vérifiés, outils testés)
- **Phase detection** : triage des collections, identification du type d'affaire
- **Phase containment** : mesurable dans le rapport (actifs affectes, mesures)
- **Phase investigation** : phases 2-5 du workflow
- **Phase remediation** : actions recommandees dans le rapport
- **Phase retour d'experience** : lecons apprises dans le rapport

## ISO/IEC 27043

Principes et processus d'investigation generique. Cadre du workflow du kit.

## NIST SP 800-86

Guide d'integration de l'investigation forensique dans la reponse aux incidents.

Applique par le kit :

- **Collection** : inventaire des collections avec empreintes
- **Examination** : structures identifiees et qualifiées
- **Analysis** : correlations, hypotheses, conclusions
- **Reporting** : rapport final, chaque conclusion sourcee

## Regles communes

1. **Preuves intouchées** : aucune modification des originals
2. **Empreintes systematiques** : SHA256 des sa reception, avant tout traitement
3. **Journal append-only** : chaque action cite collection, outil, version, empreinte
4. **Conclusions sourcees** : chaque affirmation cite collection, artefact, hash
5. **Perimetre déclaré** : le scope de l'investigation est posé au triage et respecté
