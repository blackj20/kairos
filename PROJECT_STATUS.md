# État vérifié de K.A.I.R.O.S.

## Statut

**V0.12 — prototype opérationnel avec généralisation composable des intentions françaises.**

Ce statut signifie que le projet est installable depuis un clone propre,
démarre même lorsque la mémoire mutable n’existe pas encore, analyse une
requête, conserve les expériences, organise leur consolidation avec GrowUp et
peut transformer une relation déjà promue en skill candidate versionnée.

Une candidate V0.5 reste inactive pendant sa génération et sa validation. Son
activation exige un rapport réussi lié à son empreinte exacte et une approbation
humaine déclarée. Une version précédente peut ensuite être restaurée avec son
chemin, son rapport et son empreinte.

Ce statut ne signifie pas que Kairos est une intelligence générale, qu’il invente
librement du code, qu’il installe un logiciel ou qu’il peut naviguer sans
contrôle dans le PC. Le sandbox V0.5 limite un processus local ; il ne remplace
pas un conteneur, une machine virtuelle ou une politique système forte.

## Commandes reproductibles

```bash
python -m pip install -e .
kairos --smoke-test
kairos --growup-scan
kairos --skill-factory-scan
kairos --route-plan chercher --route-target atome
kairos --secau-status
python -m unittest discover -s tests -v
python intent_generalization_benchmark.py
python meta_comprehension_benchmark.py
python benchmark.py
python holdout.py
python decision_benchmark.py
python growup_benchmark.py
python skill_factory_benchmark.py
python routing_benchmark.py
python user_acceptance.py
python user_acceptance_additional.py
python user_acceptance_v05.py
python user_acceptance_v06.py
```

## Portes validées

### Fondation V0.4 conservée

- installation depuis un checkout propre ;
- commande `kairos` disponible ;
- création automatique d’une mémoire mutable vide au premier démarrage ;
- refus d’écraser silencieusement une mémoire invalide ou corrompue ;
- compréhension et décision symboliques ;
- blocage des ordres incomplets ou contradictoires ;
- liaison `question → réponse → expérience → redémarrage` ;
- aucune promotion automatique d’une expérience ;
- collecte, regroupement, priorité et plans GrowUp persistants ;
- consolidation protégée par `Réfléchir → Tester → SECAU` ;
- sources Internet limitées à deux domaines HTTPS distincts ;
- zéro fausse exécution exigée par les seuils.

### Skill Factory V0.5

- génération autorisée uniquement depuis un plan GrowUp `promoted` ;
- relation contradictoire refusée avant génération ;
- seul le template déterministe `relation_mapper` est autorisé ;
- candidate créée avec toutes les permissions externes fermées ;
- manifeste strict : aucun champ implicite ou inconnu ;
- version sémantique, identifiant et entrypoint validés ;
- timeout de 1 à 10 secondes et mémoire de 64 à 256 Mo ;
- empreinte SHA-256 sur l’ensemble de l’artefact ;
- liens symboliques, fichiers inattendus et volume excessif refusés ;
- scan AST récursif du handler et des tests ;
- imports système, réseau, processus et chargement dynamique refusés ;
- tests exécutés avec `python -I`, sans shell, dans un dossier temporaire ;
- limites CPU, mémoire, taille de fichier et fichiers ouverts appliquées lorsque
  le système les supporte ;
- scan négatif bloquant toute exécution des tests ;
- rapport persistant lié à une candidate et à son empreinte ;
- modification après génération détectée et mise en quarantaine ;
- modification après rapport bloquant l’activation ;
- rapport d’une autre candidate refusé ;
- approbateur inconnu refusé ;
- activation explicite par `Jps` ;
- version précédente marquée `superseded` lorsqu’une nouvelle version devient
  active ;
- registre conservant chemin, rapport, empreinte et approbateur par version ;
- rollback complet et traçable ;
- bases, candidates et artefacts actifs exclus de Git.

### Action Router V0.6

- catalogue JSON séparant verbes, routes et capacités ;
- 14 verbes fondamentaux ancrés à un objectif opérationnel ;
- route connue compilée en plan contrôlable ;
- route absente composée en candidate ;
- capacité manquante explicitement signalée ;
- aucun handler ou import Python accepté depuis JSON ;
- permissions vérifiées lors de l’enregistrement d’une capacité ;
- route `blocked` ou `candidate` inexécutable ;
- plan de route exposé dans la décision du Kernel ;
- `toi-même` reconnu comme modificateur et non comme cible ;
- chaque verdict SECAU inscrit dans l’audit et consultable en CLI.

### Information Search V0.7

- recherche locale dans les connaissances confirmées ;
- cible inconnue acceptée comme objet de recherche, pas comme sens déjà compris ;
- recherche Wikipédia HTTPS seulement après `--online` ;
- fournisseur injecté pour les tests sans réseau ;
- comparaison du nombre de sources, des domaines et du recouvrement lexical ;
- hypothèse candidate avec empreintes de preuve et URLs ;
- réutilisation d’une candidate existante ;
- zéro promotion et zéro revue SECAU automatique.

### Research Tester → SECAU V0.8

- dossier de consolidation mesurable ;
- deux preuves, deux sources et deux domaines HTTPS ;
- intégrité SHA-256 preuve/source/affirmation ;
- contrôle de présence du sujet et accord lexical ;
- contrôles négatifs de sécurité ;
- rapport Tester lié à l’hypothèse exacte ;
- quatre verdicts SECAU observables ;
- promotion seulement après rapport réussi.

### Apprentissage naturel et indexation V0.9

- une seule question principale exposée à la fois ;
- objectif parent conservé pendant une faute ou un mot inconnu ;
- deux clarifications au maximum par étape ;
- correction orthographique enregistrée seulement après confirmation ;
- reprise de la séance après redémarrage ;
- réponses libres guidées par un exemple, sans format artificiel obligatoire ;
- candidate structurée mais non réutilisable avant Tester et SECAU ;
- 39 concepts courants décrits par sens, catégorie et route éventuelle ;
- 192 formes verbales, 31 entités et 114 formes courantes pré-indexées ;
- 174,61 analyses par seconde mesurées sur Python 3.11 ;
- commande `stop` transmise à la séance active avant de quitter la console.

### Méta-compréhension relationnelle V0.10

- catégories déclaratives pour adjectifs, noms communs, noms propres et références ;
- relations `est_un`, `qualite`, `reference` et actions extraites avec score et preuve ;
- référents stables `self:kairos`, `actor:user` et `creator:jps` ;
- une référence personnelle ne remplace jamais une cible substantive ;
- `explique-toi` résout directement Kairos comme cible ;
- identité, objectif, version, actions, routes et capacités lus depuis l'état runtime ;
- explication de la dernière analyse, des mots inconnus et de la dernière décision ;
- relations pédagogiques conservées comme candidates, jamais comme vérités immédiates ;
- vocabulaire d'explication enrichi sans désactiver les clarifications sur les vrais inconnus ;
- normalisation des apostrophes, accents et clitiques français.

### Filtres cognitifs et choix explicables V0.11

- intention séparée de la forme grammaticale ;
- demandes indirectes routées comme actions sans falsifier leur type linguistique ;
- distinction explicite entre besoin, envie et manque ;
- direction calculée à partir de l'objectif et de la cible ;
- risque opérationnel mesuré par famille d'action ;
- prudence conduisant à router, clarifier, confirmer ou refuser ;
- priorités déclaratives : sécurité humaine, vérité, autorisation, intégrité,
  réversibilité, alignement et efficacité ;
- vocabulaire cognitif enrichi en noms et adjectifs ;
- justification de la dernière décision avec filtres et raisons ;
- une envie ne crée aucune permission ;
- une confirmation ne contourne pas le contrôle des permissions ;
- une interdiction claire sans cible reste une route de contrôle.

### Généralisation des intentions V0.12

- détecteur séparé du moteur de décision ;
- règles déclaratives chargées depuis `data/cognition/intent_rules.json` ;
- composition modalité + destinataire + action au lieu d'une phrase unique ;
- distinction demande d'action / question de capacité / question informative ;
- clitiques normalisés comme `sais-tu → sais + tu` ;
- formes subordonnées françaises ajoutées aux verbes canoniques ;
- demandes polies complètes non pénalisées par leur position syntaxique ;
- besoins et envies compris sans devenir des permissions ;
- contrôle des rôles conservé après généralisation ;
- corpus indépendant de 100 formulations réparties en sept familles ;
- zéro fausse exécution exigée.

## Cycle démontré

```text
incompréhension
→ question ciblée
→ réponse du créateur
→ expérience non confirmée
→ GrowUp collecte et regroupe
→ preuves + exemples + contre-exemples
→ Réfléchir crée l’hypothèse
→ Tester produit le rapport
→ SECAU promeut ou rejette
→ plan GrowUp promoted
→ Skill Factory génère une candidate inactive
→ manifeste + permissions + empreinte + scan AST
→ tests dans le sandbox local
→ rapport lié à l’artefact exact
→ approbation humaine
→ activation versionnée
→ rollback possible
```

## Invariants

```text
Une expérience seule n’est jamais une vérité confirmée.
GrowUp.analyser() ne modifie jamais une connaissance confirmée.
Un plan non promoted ne génère aucune skill.
Une relation conflictuelle ne génère aucune skill.
Une candidate générée ou validée reste inactive.
La V0.5 n’accorde ni réseau, ni shell, ni processus, ni fichiers.
Le scanner inspecte aussi les tests.
Un scan négatif empêche l’exécution.
Un rapport ne couvre qu’une candidate et une empreinte.
Une modification après rapport bloque l’activation.
Seul un approbateur déclaré peut activer ou rollback.
Chaque version active possède son chemin, rapport, digest et approbateur.
Le rollback restaure toutes les métadonnées de la version précédente.
Une envie, un besoin ou un score cognitif ne crée jamais une permission.
Une action nuisible explicite est refusée avant tout routage.
Une action irréversible ou physique exige une confirmation explicite.
```

## Résultats vérifiés par la CI V0.12

Le dernier commit n’est accepté que si toutes les portes suivantes restent
vertes sous Python 3.11, 3.12 et 3.13 :

| Porte | Seuil |
|---|---:|
| Tests automatisés | 168/168 |
| Acceptation historique et V0.4 | 18/18 |
| Acceptation CLI Skill Factory | 11/11 |
| Acceptation totale | 40/40 |
| Smoke test | réussi |
| Scan GrowUp installé | réussi |
| Scan Skill Factory installé | réussi |
| Généralisation des intentions V0.12 | 100/100 |
| Précision d'intention V0.12 | 100 % |
| Précision de route V0.12 | 100 % |
| Benchmark filtres cognitifs V0.11 | 13/13 |
| Benchmark méta-compréhension V0.10 | 11/11 |
| Benchmark squelette | ≥ 100 analyses/s (143,76 mesurées lors du run final) |
| Benchmark Comprendre | réussi |
| Benchmark holdout | réussi |
| Benchmark Décision | réussi |
| Benchmark GrowUp | réussi |
| Benchmark Skill Factory | réussi |
| Benchmark Action Router | 15/15 |
| Benchmark Information Search | 8/8 |
| Benchmark Research SECAU | 10/10 |
| Promotions non testées | 0 |
| Promotions frauduleuses | 0 |
| Fausses exécutions de route | 0 |
| Fausses exécutions | 0 autorisée |

## Parcours V0.5 acceptés

Les commandes utilisateur couvrent :

```text
kairos --skill-factory-scan
kairos --skill-generate PLAN_ID --skill-version 0.1.0
kairos --skill-validate CANDIDATE_ID
kairos --skill-activate CANDIDATE_ID --report-id RAPPORT --approved-by intrus
kairos --skill-activate CANDIDATE_ID --report-id RAPPORT --approved-by Jps
kairos --skill-generate PLAN_ID --skill-version 0.2.0
kairos --skill-rollback learned.deploie --approved-by Jps
```

Le parcours démontre également qu’une candidate n’est pas activée
implicitement et qu’une altération après le rapport est refusée.

## Prochaine porte

La prochaine étape doit relier les concepts candidats issus des explications au cycle GrowUp → Tester → SECAU. Le corpus V0.12 reste obligatoire pour empêcher toute régression d'intention. L'autonomie matérielle viendra seulement après une porte séparée : plan, génération de code candidate, analyse statique, simulateur, tests de réaction, autorisation humaine, journal et rollback.
