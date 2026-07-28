# K.A.I.R.O.S. — cerveau évolutif local

K.A.I.R.O.S. est un moteur symbolique, local et explicable. Il analyse une
requête française, estime son intention, choisit une route, demande les
informations manquantes et conserve les réponses comme expériences.

La V0.4 ajoute **GrowUp**, l’organe qui transforme l’accumulation d’expériences
en travail d’apprentissage organisé, sans transformer directement une réponse
en vérité.

> Statut honnête : prototype opérationnel de compréhension, décision et
> apprentissage supervisé. Ce n’est pas une intelligence générale.

## Ce que Kairos sait faire

- découper et normaliser une requête ;
- rechercher le sens des mots dans ses connaissances déclaratives ;
- estimer le type, la démarche, l’action et la cible ;
- bloquer un ordre incomplet ou contradictoire ;
- poser une question ciblée ;
- relier la réponse à la question originale ;
- conserver l’expérience après redémarrage ;
- regrouper les difficultés similaires avec GrowUp ;
- calculer leur priorité de manière explicable ;
- produire un plan de recherche, de questionnement et de test ;
- promouvoir une relation uniquement après `Réfléchir → Tester → SECAU` ;
- réutiliser une relation confirmée lors d’une nouvelle requête.

## Ce que Kairos ne sait pas encore faire

- apprendre un domaine depuis rien ;
- déterminer seul qu’une source est vraie ;
- générer et activer librement du code Python ;
- naviguer librement dans le PC ;
- comprendre toute formulation française ;
- remplacer une isolation système forte pour l’exécution de code non fiable.

## Installation

Python 3.11 ou plus récent :

```bash
git clone https://github.com/blackj20/kairos.git
cd kairos
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
kairos --smoke-test
```

Lancer l’interface :

```bash
kairos
```

Analyser les expériences persistantes sans rien promouvoir :

```bash
kairos --growup-scan
```

## Architecture centrale

```text
Utilisateur
   ↓
Kernel
   ↓
Comprendre
├── Découper
├── Sens
├── Contexte
├── Estimer
└── VerifierAnalyse
   ↓
Décision
├── Évaluer
├── ChoisirRoute
├── VerifierDecision
└── Demande
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
relation confirmée, rejetée ou mise en quarantaine
```

Le `Kernel` orchestre. `Comprendre` ne parle pas. `Évaluer` et `ChoisirRoute`
ne modifient aucune mémoire. `GrowUp.analyser()` ne confirme aucune
connaissance. Seul le `Consolidateur` peut demander une promotion à SECAU.

## Exemple : verbe inconnu

```text
Utilisateur : deploie python
Kairos      : Je ne connais pas encore le sens de « deploie » ici.

Utilisateur : installer
Kairos      : réponse enregistrée comme expérience non confirmée
```

À ce stade, `deploie` n’est **pas** réutilisable. Après plusieurs épisodes :

```text
deploie python
+ deploie docker
+ deploie git
→ un groupe GrowUp
→ occurrences : 3
→ relation candidate : deploie → installer
→ plan : collecter preuves, exemples, contre-exemples et régressions
```

La consolidation exige ensuite :

```text
au moins 2 preuves indépendantes
+ au moins 3 exemples positifs
+ au moins 2 contre-exemples
+ tests de régression
→ Réfléchir crée l’hypothèse
→ Tester produit un rapport
→ SECAU vérifie le rapport et la provenance
→ promotion ou rejet
```

Avant le verdict `promote`, la mémoire confirmée reste intacte.

## Utilisation de GrowUp en Python

```python
from kairos.growup import (
    MoteurGrowUp,
    PreuveApprentissage,
    StockageGrowUp,
)
from kairos.memory import MemoryRepository

moteur = MoteurGrowUp(
    kernel.moteur_decision.stockage,
    cognitive_repository=MemoryRepository("memory/cognition.db"),
    growup_storage=StockageGrowUp("memory/growup.db"),
    relations_memory=kernel.comprendre.connaissances.relations_verbes,
)

rapport = moteur.analyser()
plan = rapport.plans[0]

resultat = moteur.consolider_relation(
    plan.id,
    preuves=(
        PreuveApprentissage(
            "creator",
            "creator://lesson/deployer",
            "Déployer un logiciel signifie ici l’installer.",
            95,
        ),
        PreuveApprentissage(
            "documentation",
            "manual://software/deployment",
            "Le déploiement rend le logiciel disponible par installation.",
            85,
        ),
    ),
    exemples=("deploie python", "deploie docker", "deploie git"),
    contre_exemples=("deploie fichier", "deploie dossier"),
    resolver=resolver_controle,
    regressions=(test_non_regression,),
)
```

Le `resolver` est injecté volontairement : GrowUp ne doit pas inventer le
résultat de ses propres tests.

## Priorité GrowUp

Le score reste explicable :

```text
fréquence       30 %
impact          25 %
risque          25 %
vérifiabilité   20 %
```

Les événements d’apprentissage et les expériences correspondantes ne sont pas
comptés deux fois. Un conflit de sens augmente le risque et impose une demande
de clarification au créateur.

## Mémoire

```text
memory/*.json       questions, expériences et événements de décision
memory/cognition.db preuves, hypothèses, rapports et connaissances confirmées
memory/growup.db    groupes, plans, runs et audit GrowUp
semantic_relations  relations verbales confirmées et réutilisables
```

Les bases SQLite locales sont ignorées par Git. Les tests utilisent des
stockages temporaires ou en mémoire afin de ne jamais contaminer les données
réelles.

## Apprentissage Internet

Une relation issue du Web exige deux domaines HTTPS distincts. Le client refuse
les adresses locales, limite la taille, applique un timeout et n’exécute pas le
HTML.

```text
2 domaines HTTPS distincts
→ Evidence traçable
→ extraction
→ relation candidate
→ exemples et contre-exemples
→ Tester
→ SECAU
→ promotion éventuelle
```

Une page isolée ne peut jamais modifier la compréhension confirmée.

## Skills et opérations PC

Le dépôt contient déjà une fondation de Skill Builder, scanner AST, registre,
tests isolés et rollback. Ces composants restent séparés de GrowUp.

Aucune skill sensible ne doit être activée sans :

```text
manifeste
→ permissions minimales
→ analyse statique
→ sandbox
→ tests
→ rapport
→ activation versionnée
→ rollback
```

Les opérations PC doivent passer par des outils limités et réversibles, jamais
par un accès libre au shell.

## Validation reproductible

```bash
kairos --smoke-test
kairos --growup-scan
python -m unittest discover -s tests -v
python benchmark.py
python holdout.py
python decision_benchmark.py
python growup_benchmark.py
```

État V0.4 :

| Porte | Résultat |
|---|---:|
| Tests automatisés | 90/90 |
| Python | 3.11, 3.12, 3.13 |
| Compréhension centrale | 100 % |
| Décision | 100 % sur le corpus dédié |
| Regroupement GrowUp | seuil ≥ 90 % |
| Traçabilité GrowUp | seuil = 100 % |
| Comptage des occurrences | seuil = 100 % |
| Fausses exécutions autorisées | 0 |

La CI échoue si un benchmark descend sous son seuil.

## Organisation GrowUp

```text
kairos/growup/
├── collecteur.py
├── regroupement.py
├── priorite.py
├── planificateur.py
├── consolidateur.py
├── stockage.py
├── moteur.py
└── modeles.py
```

## Direction suivante

La prochaine porte est le **générateur de skills candidates**. Il ne devra pas
écrire puis exécuter arbitrairement du Python. Il devra produire un dossier
candidat, un manifeste, des tests, un rapport de sandbox et attendre une
activation contrôlée.
