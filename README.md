# K.A.I.R.O.S. — cerveau évolutif local

K.A.I.R.O.S. est un moteur symbolique, local et explicable. Il analyse une
requête française, estime son intention, choisit une route, demande les
informations manquantes et conserve les réponses comme expériences.

La **V0.11** ajoute des **filtres cognitifs et des choix explicables**. Kairos distingue désormais intention, besoin, envie et manque, estime un risque opérationnel, applique prudence et direction, puis justifie sa route. Les valeurs restent techniques et traçables : sécurité humaine, vérité, autorisation, intégrité, réversibilité et alignement. Une envie ne crée jamais une permission. La **V0.10** ajoutait la méta-compréhension et un graphe de petites relations françaises. La **V0.9** ajoutait l’apprentissage naturel persistant et un squelette linguistique indexé. Une faute ou un mot inconnu ouvre une clarification bornée, puis Kairos reprend la question principale. La **V0.8** activait la porte **Research Tester → SECAU**. La V0.7 rendait la route **Information Search** exécutable. La V0.6 ajoutait **Action Router** : les verbes fondamentaux pointent vers
des routes et des capacités déclarées en JSON. Une route absente peut être
composée, mais reste candidate et inexécutable jusqu’à validation. Chaque verdict
SECAU devient également visible dans l’audit.

> Statut honnête : prototype opérationnel de compréhension symbolique, décision,
> mémoire, apprentissage supervisé, routage, recherche contrôlée et consolidation
> par Tester puis SECAU. Ce n’est pas une intelligence générale : les contrôles
> prouvent une cohérence traçable, pas une vérité absolue.

## Ce que Kairos sait faire

- découper et normaliser une requête ;
- rechercher le sens des mots dans ses connaissances déclaratives ;
- estimer le type, la démarche, l’action et la cible ;
- reconnaître une demande indirecte malgré sa forme interrogative ;
- distinguer intention, besoin, envie et information manquante ;
- estimer le risque et choisir entre répondre, router, clarifier, confirmer ou refuser ;
- expliquer un choix par sa direction, ses filtres, son risque et ses informations manquantes ;
- extraire des relations explicables comme `mbote —est_un→ salutation` et `salutation —qualite→ amical` ;
- résoudre `toi`, `moi`, `Kairos` et `Jps` vers des référents explicites sans remplacer une cible concrète ;
- expliquer sa dernière compréhension, ses inconnus et la route choisie ;
- décrire son identité, son objectif, sa version et ses capacités depuis les registres runtime ;
- bloquer un ordre incomplet ou contradictoire ;
- poser une question ciblée ;
- garder l’objectif principal pendant une clarification secondaire ;
- demander confirmation avant de mémoriser une correction orthographique ;
- reprendre une séance d’apprentissage après redémarrage ;
- relier un mot courant à son sens, sa catégorie et une route candidate ;
- produire une connaissance candidate non réutilisable avant Tester et SECAU ;
- relier la réponse à la question originale ;
- conserver l’expérience après redémarrage ;
- regrouper les difficultés similaires avec GrowUp ;
- calculer leur priorité de manière explicable ;
- produire un plan de recherche, de questionnement et de test ;
- promouvoir une relation uniquement après `Réfléchir → Tester → SECAU` ;
- transformer un plan `promoted` en skill candidate pure ;
- analyser le manifeste, les permissions, le code et les tests de la candidate ;
- exécuter les tests dans un processus isolé avec timeout et quotas ;
- lier le rapport à une empreinte SHA-256 de l’artefact ;
- activer explicitement une version après approbation du créateur ;
- restaurer une version précédente avec son chemin, son rapport et son empreinte.
- relier un verbe fondamental à une route et à des capacités atomiques ;
- compiler une route JSON en plan `ready`, `candidate` ou `blocked` ;
- composer une route absente sans l’exécuter automatiquement ;
- exposer les capacités manquantes et chaque verdict SECAU.
- exécuter `chercher` dans la mémoire confirmée ;
- rechercher sur Wikipédia en HTTPS après autorisation `--online` ;
- comparer la provenance et le recouvrement lexical des sources ;
- créer ou réutiliser une hypothèse candidate sans la promouvoir ;
- répondre avec les sources et le statut d’apprentissage.
- préparer un dossier de recherche mesurant preuves, sources et domaines ;
- vérifier l’intégrité SHA-256 de chaque affirmation ;
- appeler réellement Tester puis SECAU ;
- produire `promote`, `needs_more_evidence`, `reject` ou `quarantine` ;
- rendre une connaissance recherchée visible seulement après promotion.

## Ce que Kairos ne sait pas encore faire

- apprendre un domaine depuis rien ;
- déterminer seul qu’une source est vraie ;
- inventer librement du code Python ;
- générer une skill avec accès réseau, shell, processus ou fichiers ;
- installer réellement un logiciel ;
- naviguer librement dans le PC ;
- comprendre toute formulation française ;
- remplacer un conteneur ou une isolation système forte pour du code non fiable.

## Installation

Python 3.11 ou plus récent :

```bash
git clone https://github.com/blackj20/kairos.git
cd kairos
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
kairos --smoke-test
kairos --route-plan chercher --route-target atome
kairos --secau-status
kairos --online cherche toi-même atome
kairos --research-status
kairos --research-review HYPOTHESIS_ID
```

Lancer l’interface :

```bash
kairos
```

## Architecture centrale

```text
Utilisateur
   ↓
Kernel
   ↓
Comprendre
├── Index lexical V0.9
├── Découper
├── Sens
├── Contexte
├── Relier (références, catégories, qualités, actions)
├── Estimer
└── VerifierAnalyse
   ↓
Filtres cognitifs V0.11
├── Intention malgré la forme
├── Besoins, envies et manques
├── Risque et prudence
├── Direction opérationnelle
└── Choix explicable
   ↓
Méta-compréhension
├── Modèle de soi runtime
├── Explication de la dernière analyse
└── Justification de la dernière décision
   ↓
Dialogue d’apprentissage naturel
├── Question principale persistante
├── Clarification bornée
├── Reprise automatique
└── Candidate non confirmée
   ↓
Décision
├── Évaluer
├── ChoisirRoute
├── VerifierDecision
└── Demande
   ↓
Action Router
├── Catalogue JSON
├── Compilation du plan
├── Registre de capacités
├── Contrôle des permissions
└── Exécution seulement si ready
   ↓
Expérience non confirmée
   ↓
GrowUp
├── Collecteur
├── Regroupement
├── Priorité
├── Planificateur
└── Consolidateur
       ↓
Réfléchir → Tester → SECAU
       ↓
Plan GrowUp promoted
       ↓
Skill Factory
├── Builder déterministe
├── Manifeste strict
├── PermissionPolicy
├── Empreinte d’intégrité
├── Scanner AST récursif
├── Sandbox de tests
├── Rapport persistant
├── Approbation humaine
├── Registre versionné
└── Rollback complet
```

Le `Kernel` orchestre. `Comprendre` ne parle pas. `Évaluer`, `ChoisirRoute` et
`GrowUp.analyser()` ne modifient aucune connaissance confirmée. Skill Factory ne
peut lire que les plans déjà `promoted` et ne peut jamais activer une candidate
pendant sa génération ou sa validation.

## Boucle d’apprentissage GrowUp

```text
incompréhension
→ question ciblée
→ réponse du créateur
→ expérience non confirmée
→ GrowUp collecte et regroupe
→ preuves + exemples + contre-exemples
→ Réfléchir crée une hypothèse
→ Tester produit un rapport
→ SECAU promeut, rejette ou met en quarantaine
→ plan GrowUp éventuellement promoted
```

Une expérience seule n’est jamais une preuve suffisante.

## Cycle Skill Factory V0.5

```text
plan GrowUp promoted
→ génération d’une candidate inactive
→ permissions toutes fermées
→ empreinte SHA-256
→ validation du manifeste
→ scan de tous les fichiers Python, tests compris
→ exécution des tests en processus isolé
→ rapport lié à l’empreinte exacte
→ approbation humaine explicite
→ copie versionnée dans skills/active
→ activation dans le registre
→ rollback possible
```

La V0.5 ne génère actuellement qu’un template sûr : `relation_mapper`. Il
transforme une action déjà validée en son action canonique sans accès au réseau,
au système de fichiers, aux processus ou au shell.

Exemple conceptuel :

```text
deploie → installer
```

La candidate reçoit :

```json
{
  "action": "deploie",
  "target": "python"
}
```

Et peut produire, après activation :

```json
{
  "status": "ok",
  "source_action": "deploie",
  "action": "installer",
  "target": "python"
}
```

Elle ne lance aucune installation.

## Commandes GrowUp

Analyser les expériences sans rien promouvoir :

```bash
kairos --growup-scan
```

## Commandes Skill Factory

Lister les plans éligibles, candidates et versions actives :

```bash
kairos --skill-factory-scan
```

Générer une candidate depuis un plan GrowUp `promoted` :

```bash
kairos --skill-generate PLAN_ID --skill-version 0.1.0
```

Un identifiant peut être imposé :

```bash
kairos --skill-generate PLAN_ID \
  --skill-id learned.deploie \
  --skill-version 0.1.0
```

Valider la candidate sans l’activer :

```bash
kairos --skill-validate CANDIDATE_ID
```

Activer l’artefact exact couvert par un rapport réussi :

```bash
kairos --skill-activate CANDIDATE_ID \
  --report-id SKILL_REPORT_ID \
  --approved-by Jps
```

Restaurer la version précédente :

```bash
kairos --skill-rollback learned.deploie --approved-by Jps
```

Une commande invalide termine avec un code non nul et commence par
`SKILL_FACTORY_ERROR`.

## Manifeste et permissions

Chaque candidate possède un `skill.json` strict :

```text
id
name
version
status
entrypoint
intents
domains
input_schema
output_schema
permissions
limits
```

En V0.5, les permissions suivantes doivent rester fermées :

```json
{
  "network": false,
  "filesystem_read": [],
  "filesystem_write": [],
  "process": false,
  "shell": false
}
```

Une permission supplémentaire, un champ inconnu, un chemin absolu, un `..`, une
version non sémantique ou un entrypoint ambigu provoque un rejet.

## Scanner AST

Le scanner inspecte récursivement le handler **et les tests**. Il bloque
notamment :

- les liens symboliques ;
- les fichiers inattendus ;
- les imports système, réseau, processus et chargement dynamique ;
- `eval`, `exec`, `compile`, `open` et `__import__` ;
- les attributs dangereux comme `system`, `popen`, `unlink`, `urlopen` ;
- le code exécuté au chargement du module ;
- les accès dunder sensibles ;
- une candidate trop volumineuse ou contenant trop de fichiers.

Un scan négatif empêche le lancement des tests.

## Sandbox

Les tests sont copiés dans un dossier temporaire et exécutés avec :

```text
python -I
aucun shell
PYTHONPATH vide
timeout
limite mémoire
limite CPU
limite de taille de fichiers
limite de fichiers ouverts
```

Cette défense réduit les risques, mais reste un **sandbox de processus local**.
Elle ne remplace pas un conteneur, une machine virtuelle ou un profil système
fort. Les futures skills ayant des effets sur le PC devront passer par des outils
séparés et limités.

## Intégrité et activation

Le rapport contient l’empreinte du candidat. L’activation vérifie :

```text
candidate connue
+ statut validated
+ rapport connu
+ rapport réussi
+ rapport appartenant à cette candidate
+ empreinte actuelle = empreinte générée = empreinte du rapport
+ approbateur autorisé
```

Modifier un commentaire après validation suffit à changer l’empreinte et bloque
l’activation.

Le statut `active` du manifeste est normalisé dans l’empreinte : la copie active
peut changer uniquement son état de cycle de vie sans changer le code qui a été
testé.

## Rollback

Le registre conserve pour chaque version :

```text
path
report_id
digest
approved_by
status
```

Le rollback ne change donc pas seulement `0.2.0` en `0.1.0`. Il restaure aussi le
chemin de l’artefact, le rapport, l’empreinte et l’approbateur de la version
précédente.

## Mémoire et artefacts

```text
memory/*.json                 décisions et expériences
memory/cognition.db           preuves, hypothèses et connaissances
memory/growup.db              groupes, plans et audit GrowUp
memory/skills.db              candidates, rapports et audit Skill Factory
memory/skill_registry.json    versions actives et historique de rollback
skills/candidates/            artefacts générés mais inactifs
skills/active/                copies versionnées explicitement activées
```

Ces artefacts d’exécution sont ignorés par Git. Les tests utilisent des dossiers
et bases temporaires.

## Invariants

```text
Une expérience n’est jamais une vérité confirmée.
GrowUp.analyser() ne promeut rien.
Une relation conflictuelle n’atteint pas Tester.
Un plan non promoted ne génère aucune skill.
Une candidate générée ou validée reste inactive.
Une permission externe est interdite en V0.5.
Le scanner inspecte aussi les tests.
Un rapport ne couvre qu’une candidate et une empreinte.
Une modification après rapport bloque l’activation.
Seul un approbateur déclaré peut activer ou rollback.
Toute version activée est traçable et réversible.
```

## Validation reproductible

```bash
kairos --smoke-test
kairos --growup-scan
kairos --skill-factory-scan
python -m unittest discover -s tests -v
python cognitive_filters_benchmark.py
python meta_comprehension_benchmark.py
python benchmark.py
python holdout.py
python decision_benchmark.py
python growup_benchmark.py
python skill_factory_benchmark.py
python routing_benchmark.py
python user_acceptance.py
python user_acceptance_additional.py
python user_acceptance_v06.py
```

La CI exécute ces portes sous Python 3.11, 3.12 et 3.13 avec `fail-fast: false`.
Une version qui échoue n’annule donc pas le diagnostic des deux autres.

## Suite logique

La prochaine porte doit éprouver les filtres sur davantage de paraphrases et
relier leurs concepts candidats au cycle GrowUp → Tester → SECAU. Une future
commande physique devra d’abord produire un plan, compiler une candidate,
l’exécuter dans un simulateur, vérifier la réaction, demander une autorisation
humaine et conserver un rollback. Aucun accès Arduino ou shell libre n’est
accordé par la V0.11.
