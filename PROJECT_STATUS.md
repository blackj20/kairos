# État vérifié de K.A.I.R.O.S.

## Statut

**V0.17 — prototype opérationnel avec apprentissage actif naturel et liens candidats autonomes.**

Ce statut signifie que le projet est installable depuis un clone propre,
démarre même lorsque la mémoire mutable n’existe pas encore, analyse une
requête, conserve les expériences, organise leur consolidation avec GrowUp et
peut transformer une relation déjà promue en skill candidate versionnée. La V0.15 conserve désormais un but, sa priorité, son budget et ses événements, puis choisit et exécute une seule étape causale à la fois. Elle reprend un but après redémarrage et ne le termine qu’après preuve causale. La V0.14 ajoute une boucle `prédire → exécuter → observer → évaluer → rejouer` : elle distingue désormais une exécution techniquement correcte d’une mission réellement accomplie. La commande `self-correction=on` copie sa mémoire cognitive et peut lancer le Tester causal puis SECAU dans cette copie sans corrompre la mémoire principale.

La V0.17 ferme la porte suivante : une question naturelle sur un concept inconnu ouvre un manque de sens, l’explication crée automatiquement des liens candidats, puis Kairos choisit relation, exemples, contre-exemples ou source selon un gain attendu. Chaque clarification est bornée à une reformulation et une séance mémorisée ne capture jamais une commande après redémarrage sans reprise explicite.

La V0.16 ferme la rupture observée en usage réel : après une question de manque, l’explication du créateur crée ou réutilise une hypothèse candidate dans `memory/cognition.db`. Son identifiant, son statut et les preuves manquantes sont affichés immédiatement et restent visibles après redémarrage. Une clarification opérationnelle, comme `Python` après `installe quoi ?`, ne crée aucune hypothèse.

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
kairos self-correction=on
kairos self-correction=status
kairos --causal-run "cherche atome"
kairos --causal-replay EPISODE_ID
kairos --causal-status
kairos --goal-create "cherche atome"
kairos --goal-run "cherche atome"
kairos --goal-step GOAL_ID
kairos --goal-status --goal-id GOAL_ID
python self_correction_benchmark.py
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
python user_acceptance_v013.py
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
- 209 formes verbales, 31 entités et 114 formes courantes pré-indexées ;
- 145,45 analyses par seconde mesurées sur Python 3.11 lors du run V0.13 ;
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

### Laboratoire de self-correction V0.13

- déclenchement exact par `self-correction=on` dans la conversation ou la CLI ;
- copie SQLite de `memory/cognition.db` avant toute revue ;
- Tester puis SECAU réellement appelés pour les candidates compatibles ;
- promotion, rejet, attente ou quarantaine possibles uniquement dans la copie ;
- candidate sans contrat de test signalée sans résultat inventé ;
- limites de mesure configurables : cycles, candidates et durée ;
- aucun accès réseau, shell, processus, matériel ou mémoire principale ;
- rapport JSON persistant avec compteurs avant/après et motif d’arrêt ;
- commande `status` liée au dernier run ;
- aucun daemon ou processus autonome caché.

### Expérience causale V0.14

- contrats de résultat déclaratifs séparés des phrases utilisateur;
- prédiction des sorties attendues et des conditions de réussite;
- exécution uniquement d’un plan `ready` dont le contrat est complet;
- observation brute sans verdict sémantique;
- réussite technique et objectif atteint mesurés séparément;
- épisodes et transitions append-only dans SQLite;
- replay lié à l’épisode source avec delta et détection de régression;
- Tester causal exigeant cinq épisodes non vus, ≥ 85 %, amélioration positive et zéro régression;
- revue SECAU réelle dans la copie du laboratoire;
- validation comportementale sans création de concept ni mutation de production;
- première route mesurée : `information.search`.

### Buts persistants et attention V0.15

- machine d’états `pending → active → completed|blocked|invalidated`;
- priorité de 0 à 100 et budget strict de 1 à 20 étapes;
- journal d’événements append-only;
- sélection d’attention explicable sans effet externe;
- exécution d’une seule étape causale par cycle;
- reprise depuis SQLite après redémarrage;
- panne technique retentable uniquement dans la limite du budget;
- route incomplète ou information absente bloquée sans fausse terminaison;
- but terminé uniquement avec `objectif_atteint=true`;
- invalidation explicite empêchant toute future exécution;
- aucune tâche de fond et aucun nouvel accès externe.

## Cycle démontré

```text
incompréhension
→ question ciblée
→ réponse du créateur
→ expérience non confirmée
→ hypothèse candidate persistante liée à l’expérience
→ GrowUp collecte et regroupe
→ preuves + exemples + contre-exemples
→ Réfléchir consolide l’hypothèse
→ Tester produit le rapport
→ SECAU promeut ou rejette
→ self-correction peut rejouer ce contrôle dans une copie isolée
→ prédiction du résultat attendu
→ exécution et observation factuelle
→ évaluation de la finalité
→ replay et mesure de la régression
→ création d’un but persistant
→ choix explicable de l’attention
→ une étape causale bornée
→ terminaison, blocage ou invalidation
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
Une question seule ne crée jamais d’hypothèse.
Une réponse opérationnelle ne devient jamais une connaissance.
Une explication du créateur peut créer une candidate, jamais une promotion.
Une candidate interactive reste liée à son expérience d’origine.
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
La self-correction ne modifie jamais `memory/cognition.db`.
Une promotion de laboratoire n’est pas une connaissance de production.
Une candidate sans contrat de test n’est jamais promue artificiellement.
La self-correction est synchrone, bornée et traçable.
L’observateur causal ne décide jamais si le but est atteint.
Une exécution réussie ne vaut pas réussite de la mission.
Un épisode causal ne peut sauter aucune transition.
Un replay reste lié à son épisode source.
Une amélioration comportementale validée en laboratoire ne devient pas une vérité de production.
Un but ne devient completed qu’après validation causale.
Le gestionnaire d’attention choisit mais n’exécute rien.
Un but terminal ne peut plus être repris.
Le budget interdit toute répétition infinie.
La V0.15 ne démarre aucun daemon.
```

## Apprentissage actif naturel V0.17

Le parcours installé suivant est vérifié de bout en bout :

```text
c'est quoi un xylophore ?
→ manque de sens explicite
→ explication naturelle du créateur
→ hypothèse candidate persistante
→ lien autonome xylophore —est_un→ instrument musical
→ trois exemples
→ deux contre-exemples
→ piste information.search
→ dossier prêt pour recherche, Tester et SECAU
```

Questions disponibles et gain maximal :

| Champ | Gain |
|---|---:|
| Relation interne | 40 % |
| Exemples | 25 % |
| Contre-exemples | 20 % |
| Piste de source | 15 % |

Une seule reformulation est permise. Si un champ essentiel reste inexpliqué,
le statut devient `needs_human_input`; Kairos conserve la réponse brute et
n'invente aucun lien. RapidFuzz fonctionne hors ligne et ne sert qu'au
rapprochement de formes.

Commandes :

```text
consolide
continue d'apprendre
pose tes questions
pause
statut apprentissage
kairos --learning-status
```

## Hypothèses interactives V0.16

Parcours vérifié :

```text
deploie python
→ question sur le sens de « deploie »
→ réponse du créateur : installer
→ expérience enregistrée
→ hypothesis_... créée avec statut candidate
→ sources, tests et validation_secau signalés comme manquants
→ même candidate retrouvée après redémarrage
```

Commandes disponibles :

```bash
kairos --hypothesis-status
kairos --hypothesis-status --hypothesis-id HYPOTHESIS_ID
```

La phrase naturelle `mes hypothèses` fonctionne aussi dans la console. La
candidate n’entre ni dans le lexique actif ni dans les connaissances confirmées.

## Résultats vérifiés par la CI V0.17

Le dernier commit n’est accepté que si toutes les portes suivantes restent
vertes sous Python 3.11, 3.12 et 3.13 :

| Porte | Résultat |
|---|---:|
| Tests automatisés | 217/217 |
| Apprentissage actif V0.17 | 19/19 |
| Questions utiles | 100 % |
| Liens candidats autonomes démontrés | 1 |
| Clarifications non bornées | 0 |
| Acceptation V0.17 via commande installée | 21/21 |
| Hypothèses interactives V0.16 | 15/15 |
| Acceptation V0.16 via commande installée | 14/14 |
| Hypothèses faussement promues | 0 |
| Réponses opérationnelles mal classées | 0 |
| Buts et attention V0.15 | 15/15 |
| Terminaison du but connu | 100 % |
| Fausses terminaisons | 0 |
| Boucles non bornées | 0 |
| Expérience causale V0.14 | 15/15 |
| Réussite des formulations causales | 100 % |
| Régressions causales | 0 |
| Appels SECAU causaux observés | 1 |
| Self-correction V0.13 | 13/13 |
| Appels SECAU internes observés | 2 |
| Mutations de la mémoire principale | 0 |
| Acceptation V0.13 via commande installée | 8/8 |
| Acceptation V0.14 via commande installée | 12/12 |
| Acceptation V0.15 via commande installée | 15/15 |
| Acceptation totale | 110/110 |
| Généralisation des intentions | 100/100 |
| Précision d’intention et de route | 100 % |
| Benchmark filtres cognitifs | 13/13 |
| Benchmark méta-compréhension | 11/11 |
| Benchmark squelette | 145,45 analyses/s |
| Benchmark Action Router | 15/15 |
| Benchmark Information Search | 8/8 |
| Benchmark Research SECAU | 10/10 |
| Fausses exécutions ou promotions | 0 |

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

**V0.18 — vérification active.** Choisir la meilleure source d’information manquante : mémoire, créateur, documentation ou Web autorisé. Toute question devra être liée à un champ manquant du but actif, apporter un gain attendu mesurable et reprendre ensuite la mission parent. Aucune récursion libre de questions ne sera acceptée. Exécuter ensuite le laboratoire sur plusieurs mémoires et mesurer ses divergences réelles. Ensuite seulement, définir une procédure séparée `proposer → comparer → approuver → importer → rollback` pour transférer une conclusion vers la mémoire principale. La V0.13 ne possède volontairement aucun raccourci d’importation. L’autonomie matérielle reste derrière une porte distincte : plan, code candidat, analyse statique, simulateur, tests de réaction, autorisation humaine, journal et rollback.
