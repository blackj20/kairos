# K.A.I.R.O.S. — cerveau évolutif local

K.A.I.R.O.S. est un moteur symbolique, local et explicable. Il analyse une
requête française, estime son intention, choisit une route, demande les
informations manquantes et conserve les réponses comme expériences.

La **V0.16** répare la boucle d’apprentissage interactive : une explication du créateur devient immédiatement une **hypothèse candidate persistante**, traçable jusqu’à la question et à l’expérience. Une simple cible opérationnelle reste une expérience et aucune candidate n’est promue sans preuves, Tester et SECAU. La **V0.15** ajoute des **buts persistants, un journal d’événements et un gestionnaire d’attention**. Kairos peut créer un objectif, le reprendre après redémarrage, sélectionner une prochaine étape explicable, appliquer un budget puis terminer, bloquer ou invalider le but selon l’évaluation causale. Cette boucle reste synchrone et bornée : aucun daemon n’est créé. La **V0.14** ajoute une **boucle d’expérience causale observable**. Pour la première fois, Kairos prédit le résultat attendu d’une route, exécute le plan réel lorsqu’il est autorisé, enregistre les faits bruts, puis sépare la réussite technique de l’objectif réellement atteint. Chaque épisode suit une machine d’états append-only et peut être rejoué pour mesurer une amélioration ou une régression. La première route couverte est `information.search`. La **V0.13** ajoute un **laboratoire de self-correction observable**. La commande `self-correction=on` copie la mémoire cognitive, lance réellement Tester puis SECAU sur les candidates compatibles et conserve un rapport complet. Dans cette copie, Kairos peut promouvoir, rejeter ou mettre en quarantaine sans chaînes métier artificielles. La mémoire principale n’est jamais modifiée. La **V0.12** ajoute la **généralisation composable des intentions**. Kairos combine modalité, destinataire, action, négation et contexte pour distinguer une demande polie d'une question sur sa capacité. Cette porte est mesurée sur 100 formulations naturelles indépendantes. La **V0.11** ajoutait des filtres cognitifs et des choix explicables. Kairos distingue désormais intention, besoin, envie et manque, estime un risque opérationnel, applique prudence et direction, puis justifie sa route. Les valeurs restent techniques et traçables : sécurité humaine, vérité, autorisation, intégrité, réversibilité et alignement. Une envie ne crée jamais une permission. La **V0.10** ajoutait la méta-compréhension et un graphe de petites relations françaises. La **V0.9** ajoutait l’apprentissage naturel persistant et un squelette linguistique indexé. Une faute ou un mot inconnu ouvre une clarification bornée, puis Kairos reprend la question principale. La **V0.8** activait la porte **Research Tester → SECAU**. La V0.7 rendait la route **Information Search** exécutable. La V0.6 ajoutait **Action Router** : les verbes fondamentaux pointent vers
des routes et des capacités déclarées en JSON. Une route absente peut être
composée, mais reste candidate et inexécutable jusqu’à validation. Chaque verdict
SECAU devient également visible dans l’audit.

> Statut honnête : prototype opérationnel de compréhension symbolique, décision,
> mémoire, apprentissage supervisé, buts persistants, attention explicable,
> routage, recherche contrôlée, mesure causale des résultats et consolidation par Tester puis SECAU. Ce n’est pas une intelligence générale : les contrôles
> prouvent une cohérence traçable, pas une vérité absolue.

## Ce que Kairos sait faire

- découper et normaliser une requête ;
- rechercher le sens des mots dans ses connaissances déclaratives ;
- estimer le type, la démarche, l’action et la cible ;
- reconnaître une demande indirecte malgré sa forme interrogative ;
- distinguer une demande d'action d'une question sur sa capacité ;
- composer des indices de modalité, personne, politesse, action et négation ;
- reconnaître des formes subordonnées courantes comme « que tu vérifies » ;
- distinguer intention, besoin, envie et information manquante ;
- estimer le risque et choisir entre répondre, router, clarifier, confirmer ou refuser ;
- expliquer un choix par sa direction, ses filtres, son risque et ses informations manquantes ;
- extraire des relations explicables comme `mbote —est_un→ salutation` et `salutation —qualite→ amical` ;
- résoudre `toi`, `moi`, `Kairos` et `Jps` vers des référents explicites sans remplacer une cible concrète ;
- expliquer sa dernière compréhension, ses inconnus et la route choisie ;
- décrire son identité, son objectif, sa version et ses capacités depuis les registres runtime ;
- bloquer un ordre incomplet ou contradictoire ;
- poser une question ciblée ;
- transformer l’explication du créateur en hypothèse candidate persistante ;
- afficher l’identifiant, le statut et les preuves encore manquantes ;
- réutiliser une candidate identique au lieu de créer des doublons ;
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
- rendre une connaissance recherchée visible seulement après promotion;
- lancer `self-correction=on` depuis la conversation ou la CLI;
- cloner la mémoire cognitive dans un laboratoire jetable;
- appeler réellement Tester puis SECAU sur les candidates ayant un contrat de test;
- exposer les candidates impossibles à tester au lieu d’inventer une validation;
- comparer l’état avant/après et prouver que la mémoire principale n’a pas changé;
- prédire les sorties attendues d’une capacité et les conditions de réussite d’une route;
- enregistrer séparément exécution, observation factuelle et évaluation de l’objectif;
- distinguer `exécution réussie` de `information réellement trouvée`;
- rejouer un épisode et détecter une amélioration ou une régression;
- faire passer une amélioration comportementale par Tester puis SECAU dans le laboratoire, sans créer une vérité sur le monde;
- créer et conserver un but avec priorité et budget d’étapes;
- choisir le prochain but par un score d’attention explicable;
- reprendre un but après redémarrage;
- terminer uniquement après validation causale;
- bloquer une mission impossible ou incomplète sans fausse réussite;
- invalider explicitement un objectif devenu obsolète.

## Ce que Kairos ne sait pas encore faire

- apprendre un domaine depuis rien ;
- déterminer seul qu’une source est vraie ;
- inventer librement du code Python ;
- générer une skill avec accès réseau, shell, processus ou fichiers ;
- installer réellement un logiciel ;
- naviguer librement dans le PC ;
- comprendre toute formulation française ;
- remplacer un conteneur ou une isolation système forte pour du code non fiable;
- fusionner automatiquement les conclusions du laboratoire dans sa mémoire principale;
- tourner en tâche de fond : la self-correction V0.13 est synchrone et bornée;
- générer seul une correction causale : la V0.14 sait tester une candidate fournie, pas inventer la modification;
- mesurer causalement toutes les routes : la V0.14 couvre d’abord `information.search`;
- inventer seul de nouveaux objectifs utiles : la V0.15 exécute seulement les buts explicitement créés;
- choisir automatiquement la meilleure question pédagogique ou collecter seul les preuves manquantes ;

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
kairos --hypothesis-status
kairos --hypothesis-status --hypothesis-id HYPOTHESIS_ID
kairos --online cherche toi-même atome
kairos --research-status
kairos --research-review HYPOTHESIS_ID
kairos self-correction=on
kairos self-correction=status
kairos --causal-run "cherche atome"
kairos --causal-replay EPISODE_ID
kairos --causal-status
kairos --goal-create "cherche atome"
kairos --goal-run "cherche atome"
kairos --goal-step GOAL_ID
kairos --goal-status --goal-id GOAL_ID
kairos --goal-invalidate GOAL_ID --reason "objectif remplacé"
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
Généralisation d'intention V0.12
├── Modalité et destinataire
├── Demande ou question de capacité
├── Clitiques et formes subordonnées
└── Signaux explicables
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
├── Hypothèse persistante issue de l’explication
├── Statut et preuves manquantes visibles
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
Expérience causale V0.14
├── Prédiction depuis les contrats de résultat
├── Exécution du plan réel autorisé
├── Observation factuelle sans jugement
├── Évaluation technique et finalité séparées
├── Replay lié à l’épisode source
└── Tester causal → SECAU dans le laboratoire
   ↓
Buts et attention V0.15
├── But persistant avec priorité et budget
├── Événements append-only
├── Sélection explicable de l’attention
├── Une étape causale par cycle
├── Reprise après redémarrage
└── Terminé, bloqué ou invalidé
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
Self-correction Lab V0.13
├── Copie SQLite isolée
├── Exploration sans chaîne métier prédéfinie
├── Tester puis SECAU réels
├── Rapport avant/après
└── Zéro écriture en production
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
→ hypothèse candidate persistante liée à l’expérience
→ GrowUp collecte et regroupe
→ preuves + exemples + contre-exemples
→ Réfléchir consolide l’hypothèse
→ Tester produit un rapport
→ SECAU promeut, rejette ou met en quarantaine
→ plan GrowUp éventuellement promoted
```

Une expérience seule n’est jamais une preuve suffisante.

## Hypothèses interactives V0.16

Dans la console, la séquence suivante crée une vraie candidate cognitive :

```text
deploie python
→ Kairos demande le sens de « deploie »

installer
→ expérience enregistrée
→ hypothèse créée : hypothesis_...
→ statut : candidate
→ manques : sources, tests, validation_secau
```

La commande `kairos --hypothesis-status` liste les candidates. La forme naturelle
`mes hypothèses` donne le même résultat dans la conversation. Après redémarrage,
la candidate reste disponible dans `memory/cognition.db`.

Une question seule ne crée rien. Une réponse opérationnelle courte à
`installe quoi ?`, par exemple `Python`, reste une expérience : elle ne devient
pas une connaissance. Une explication du créateur peut créer ou réutiliser une
candidate, mais elle reste inutilisable tant que ses preuves, ses tests et la
validation SECAU manquent.

## Laboratoire de self-correction V0.13

Depuis une conversation ou la CLI :

```bash
kairos self-correction=on
kairos self-correction=status
kairos self-correction=off
kairos --self-correction on
```

`on` exécute immédiatement un cycle borné. Il ne démarre pas un daemon. La base `memory/cognition.db` est copiée dans `memory/self_correction_runs/`; Tester et SECAU travaillent uniquement sur cette copie. Les promotions du laboratoire sont donc observables, mais non réutilisables par la mémoire principale.

La liberté porte sur les relations et hypothèses explorées, pas sur les effets externes. Réseau, shell, processus, matériel et écriture en production restent fermés. Les seules limites de laboratoire sont des limites de mesure : nombre de cycles, nombre de candidates et durée maximale. Une candidate sans contrat de test est signalée comme `skipped`; Kairos ne fabrique pas un test pour obtenir artificiellement 100 %.

## Buts, événements et attention V0.15

```text
But pending → attention → active → étape causale
                              ↓
                completed | blocked | invalidated
```

Le stockage `memory/goals.db` conserve la mission, l’action, la cible, la priorité, le budget, le nombre d’étapes et le dernier épisode causal. Chaque création, sélection, reprise, exécution et terminaison est inscrite dans un journal append-only.

Le score d’attention combine la priorité déclarée, un bonus de reprise pour un objectif déjà actif et le coût des étapes utilisées. Le choix n’exécute rien : il produit seulement `goal_id`, `score`, `raisons` et `contexte`.

Une étape est autorisée uniquement si la route est `ready` et possède un contrat de résultat. Les erreurs techniques peuvent être retentées jusqu’au budget. Une cible absente, une information introuvable, un contrat violé ou une route bloquée termine immédiatement le but en `blocked`. Seule une évaluation causale avec `objectif_atteint=true` produit `completed`.

Commandes :

```bash
kairos --goal-create "cherche atome" --goal-priority 80
kairos --goal-step GOAL_ID
kairos --goal-status --goal-id GOAL_ID
kairos --goal-run "cherche atome" --goal-max-steps 3
kairos --goal-invalidate GOAL_ID --reason "objectif remplacé"
```

## Expérience causale V0.14

```text
Comprendre → Prédire → Planifier → Exécuter → Observer → Évaluer → Replay
```

Les contrats déclaratifs de `data/cognition/capability_outcomes.json` décrivent les sorties attendues des capacités et les conditions de réussite des routes. L’observateur enregistre uniquement les faits d’exécution. L’évaluateur décide ensuite si le contrat technique est respecté et si la mission est réellement accomplie.

Exemple : une recherche peut terminer sans exception tout en échouant à trouver une information. Kairos conserve alors `technical_success=true` et `goal_reached=false`, avec la cause localisée. Le stockage `memory/causal_experiences.db` interdit de sauter une transition d’état et relie chaque replay à son épisode source.

Une candidate d’amélioration comportementale exige au moins cinq épisodes non vus, au moins 85 % de réussite, une amélioration strictement positive et zéro régression. Tester puis SECAU peuvent la valider dans la copie de laboratoire. Cette validation ne crée aucun concept confirmé et ne modifie jamais la mémoire principale.

Commandes :

```bash
kairos --causal-run "cherche atome"
kairos --causal-replay EPISODE_ID
kairos --causal-status
```

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
memory/self_correction_runs/  copies de laboratoire et rapports V0.13
memory/causal_experiences.db   épisodes et transitions causales V0.14
memory/goals.db                 buts et événements d’attention V0.15
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
La self-correction ne travaille que sur une copie de cognition.db.
Une promotion de laboratoire ne devient jamais une vérité de production.
Une candidate sans contrat de test est exposée, jamais validée artificiellement.
`self-correction=on` est synchrone, borné et observable.
L’observation causale ne contient aucun jugement sur la réussite du but.
Une réussite technique ne prouve jamais que la mission est accomplie.
Une transition causale ne peut pas sauter un état.
Un replay référence toujours l’épisode source.
Une validation comportementale de laboratoire ne crée aucune vérité du monde.
Un but ne devient completed qu’après validation causale.
Le choix d’attention n’exécute aucune capacité.
Un but terminal ne peut plus recevoir d’étape.
Chaque but possède un budget strict de 1 à 20 étapes.
Aucune boucle ou tâche de fond n’est démarrée implicitement.
```

## Validation reproductible

```bash
kairos --smoke-test
kairos --growup-scan
kairos --skill-factory-scan
python -m unittest discover -s tests -v
python autonomy_benchmark.py
python causal_benchmark.py
python self_correction_benchmark.py
python intent_generalization_benchmark.py
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
python user_acceptance_v013.py
python user_acceptance_v014.py
python user_acceptance_v015.py
```

La CI exécute ces portes sous Python 3.11, 3.12 et 3.13 avec `fail-fast: false`.
Une version qui échoue n’annule donc pas le diagnostic des deux autres.

## Suite logique

La prochaine porte est **V0.17 — apprentissage actif** : choisir entre demander au créateur, consulter la mémoire, rechercher une source ou reconnaître qu’aucune preuve n’est disponible. Chaque question devra identifier le champ manquant qu’elle débloque, rester liée au but actif et ne jamais ouvrir une récursion de questions. Ensuite seulement, une procédure explicite `proposer → comparer → approuver → importer → rollback` pourra transférer une amélioration validée vers la mémoire principale. Aucune conclusion ne rejoindra `cognition.db` tant que ce protocole n’aura pas ses propres tests, son approbation et son rollback. Le corpus V0.12 restera une barrière de non-régression. Une future
commande physique devra d’abord produire un plan, compiler une candidate,
l’exécuter dans un simulateur, vérifier la réaction, demander une autorisation
humaine et conserver un rollback. Aucun accès Arduino ou shell libre n’est
accordé par la V0.11.
