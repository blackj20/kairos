# K.A.I.R.O.S. — cerveau évolutif local

K.A.I.R.O.S. est un moteur symbolique, local et explicable. La V0.3 conserve la
fondation de compréhension V0.2 et ajoute une couche de décision capable de
bloquer une action incomplète, demander une précision et enregistrer la réponse
comme expérience non confirmée.

Ce prototype ne constitue pas une intelligence générale. Son vocabulaire reste
réduit et ses scores sont des mesures internes, pas des probabilités
scientifiquement calibrées.

La branche actuelle ajoute les contrats décrits par `architecture.md` :

- mémoire évolutive SQLite avec preuves, hypothèses, rapports et audit ;
- boucle `Réfléchir → Tester → SECAU`, sans promotion directe ;
- réponses composées uniquement depuis les connaissances confirmées ;
- acquisition de documents locaux et extraction structurée ;
- Skill Builder, manifeste, scanner AST, processus de test isolé, registre et
  rollback ;
- kernel événementiel basé sur `asyncio.Queue`, sans attente active ;
- opérations fichiers bornées à une racine, prévisualisées, confirmées selon le
  risque, transactionnelles et réversibles.

Ces composants constituent une implémentation de référence locale. Le sandbox
Python réduit le risque grâce à un processus isolé, un timeout et un dossier
temporaire, mais il ne remplace pas une isolation forte par conteneur ou
utilisateur système non privilégié.

## Corrections et vocabulaire adaptatif

Le lexique reconnaît maintenant des verbes quotidiens comme `lire`, `écrire`,
`chercher`, `copier`, `créer`, `déplacer`, `envoyer`, `afficher`, `renommer`,
`sauvegarder`, `télécharger` et `vérifier`, avec leurs formes courantes.

Une faute proche produit une relation candidate à score réduit :

```text
ovre vscode
→ As-tu voulu écrire « ouvre » à la place de « ovre » ?

oui
→ relation confirmée : ovre → ouvre

ovre vscode
→ action « ouvrir » reconnue sans nouvelle question
```

Le même mécanisme s’applique aux entités, par exemple `vsode → vscode`. Une
ressemblance ambiguë n’est pas proposée et une correction refusée ou sans
réponse n’entre jamais dans la mémoire. Avec `Kernel(persister_decisions=True)`,
les relations confirmées sont conservées dans `memory/corrections.json` et
réutilisées aux sessions suivantes.

## Graphe sémantique et auto-amélioration

`data/fr/verbes.json` contient les verbes canoniques, leurs formes, leur sens,
leur famille, leurs exemples et leur niveau de risque lorsqu’il est précisé.
`data/fr/sens.json` contient les relations typées : équivalence contextuelle,
contraire, opération inverse, complément, objectif ou ordre conseillé.

Le contexte empêche les généralisations incorrectes :

```text
mets python      → installer python
ajoute docker    → installer docker
mets fichier     → mettre fichier
ajoute fichier   → ajouter fichier
retire docker    → supprimer docker
```

Un verbe encore inconnu peut être enseigné directement :

```python
kernel = Kernel()
question = kernel.traiter("deploie python")
kernel.repondre_a(question.question_id, "installer", acteur="creator")

# La relation « deploie → installer » est désormais réutilisée.
decision = kernel.traiter("deploie python")
assert decision.analyse.action.valeur == "installer"
```

Il est également possible d’enregistrer une relation issue de recherches
externes. Deux sources Internet distinctes sont obligatoires :

```python
kernel.enseigner_relation_verbe(
    "provisionne",
    "installer",
    sources=(
        "https://documentation.example/source-a",
        "https://documentation.example/source-b",
    ),
)
```

Avec la persistance activée, ces apprentissages sont stockés dans
`memory/semantic_relations.json`. Un utilisateur ordinaire peut fournir une
expérience, mais seul le créateur peut confirmer une nouvelle relation.

## Apprentissage Internet contrôlé

La chaîne `InternetLearningPipeline` exécute maintenant toutes les portes :

```text
deux domaines HTTPS distincts
→ Evidence avec URL et hash
→ extraction de relations explicites
→ Relier fusionne les affirmations concordantes
→ hypothèse candidate
→ au moins 3 exemples et 2 contre-exemples
→ tests positifs, négatifs et régressions
→ SECAU
→ relation confirmée ou rejetée
→ synchronisation du lexique
→ suivi des utilisations
```

Une relation confirmée commence avec une maîtrise de 70. Une réussite ajoute
5 points et une erreur retire 15 points. Trois erreurs consécutives la placent
automatiquement en quarantaine. Chaque utilisation reste dans la table SQLite
`usage_events`.

Le client Internet n’accepte que HTTPS, refuse les adresses locales, impose un
timeout, limite la taille des réponses et n’exécute jamais le HTML. Les tests
utilisent un collecteur injecté afin d’être reproductibles sans réseau.

## Commandes cognitives

```text
pose-moi des questions
→ Réfléchir produit des questions sur définition, exemples,
  contre-exemples et relations

c'est quoi un atome ?
→ réponse sourcée + branches atome/noyau/électrons/protons

comment faire un print avec python ?
→ exemple exécutable, paramètres sep/end et sources Python officielles

apprends python
→ parcours concret + premier exercice
```

Les leçons confirmées se trouvent dans `data/knowledge/core.json`. Elles
contiennent réponse, exemples, contre-exemples, relations et plusieurs sources.

## Architecture

```text
Utilisateur
    ↓
Kernel
    ↓
Comprendre
├── Découper
├── Sens
├── Contexte
├── Estimation
└── VerifierAnalyse
    ↓
Décision
├── Évaluer
├── ChoisirRoute
└── VerifierDecision
       ├── route autorisée
       └── Demande
              ↓
       question en attente
              ↓
       réponse utilisateur
              ↓
          Expérience
```

Le kernel ne calcule aucun score. `Comprendre` ne parle pas et n'écrit pas en
mémoire. `Évaluer` et `ChoisirRoute` sont purs. `VerifierDecision` délègue à
`Demande` sans créer lui-même de donnée.

## Routes

```text
REPONDRE
EXECUTER
CONTROLE
CONFIRMER
CLARIFIER
ETUDIER
REFUSER
```

`ETUDIER` crée un événement d'apprentissage, mais produit extérieurement une
clarification tant que `GrowUp` et `Réfléchir` n'existent pas.

## Organisation principale

```text
kairos-prototype/
├── benchmarks/
│   ├── comprendre.json
│   ├── decision.json
│   └── holdout.json
├── data/
│   ├── decision/
│   │   ├── questions.json
│   │   ├── routes.json
│   │   └── thresholds.json
│   └── fr/
├── kairos/
│   ├── decision/
│   │   ├── choisir_route.py
│   │   ├── configuration.py
│   │   ├── demande.py
│   │   ├── evaluer.py
│   │   ├── experience.py
│   │   ├── modeles.py
│   │   ├── moteur.py
│   │   ├── stockage.py
│   │   └── verifier_decision.py
│   ├── comprendre.py
│   ├── contexte.py
│   ├── estimation.py
│   ├── kernel.py
│   ├── sens.py
│   └── verifier_analyse.py
├── memory/
│   ├── pending_questions.json
│   ├── experiences.json
│   ├── learning_events.json
│   ├── confirmed.json
│   ├── hypotheses.json
│   └── history.json
├── relations/
├── self/
├── tests/
├── benchmark.py
├── decision_benchmark.py
├── holdout.py
├── FOUNDATION.md
└── V0.3_DECISION.md
```

## Seuils décisionnels

```text
85–100 % → route autorisée
51–84 %  → confirmation
31–50 %  → clarification et étude
0–30 %   → explication prioritaire
```

Un champ obligatoire absent ou plusieurs actions détectées bloque toujours
l'exécution.

## Exemple incomplet

```text
Entrée : installe

Comprendre :
type   → ordre 80 %
action → installer 70 %
cible  → absente 0 %

Décision :
score global → 56 %
route        → CLARIFIER

Demande :
« Quelle est la cible de l'action “installer” ? »
```

La réponse `python` est ensuite reliée à la question avec :

```json
{
  "field": "cible",
  "value": "python",
  "score": 100,
  "status": "recorded_not_confirmed"
}
```

Elle ne devient pas automatiquement une connaissance.

## Persistance

`Kernel()` utilise par défaut une mémoire vive afin qu'un test ne modifie aucun
fichier. L'interface interactive utilise :

```python
Kernel(persister_decisions=True)
```

Seuls les fichiers suivants sont alors modifiables :

- `pending_questions.json` ;
- `experiences.json` ;
- `learning_events.json`.

La mémoire confirmée, les hypothèses et l'historique restent intacts.

## Résultats du 28 juillet 2026

| Évaluation | Résultat |
|---|---:|
| Fondation Comprendre, cas centraux | 51/51 — 100 % |
| Holdout, intentions | 29/29 — 100 % |
| Holdout, routage | 28/29 — 96,55 % |
| Décision, routage | 43/43 — 100 % |
| Questions ciblant le bon champ | 100 % |
| Ordres incomplets bloqués | 100 % |
| Fausses exécutions | 0 |
| Tests automatisés | 80/80 |

Un cas prudent du holdout reste visible :

- `ne ferme pas` est désormais clarifié : l'interdiction est comprise, mais sa
  cible est absente.

Ce comportement est une décision de sécurité volontaire.

## Exécution

Python 3.11 ou plus récent suffit.

```bash
python3 main.py
python3 -m unittest discover -s tests -v
python3 benchmark.py
python3 holdout.py
python3 decision_benchmark.py
```

## Exemple d’évolution interne

Une source devient d’abord une preuve. Une expérience crée ensuite une
hypothèse ; trois reformulations et les régressions doivent réussir avant que
SECAU puisse la promouvoir :

```python
from kairos.cognition import Reflechir, Secau, Tester
from kairos.memory import MemoryRepository

memoire = MemoryRepository("memory/kairos.db")
preuve = memoire.add_evidence(
    "creator",
    "lesson://classes",
    "Une classe Python est un modèle qui crée des instances.",
    90,
)
hypothese = Reflechir(memoire).from_experience(
    "experience_001",
    name="classe Python",
    definition="modèle qui crée des instances",
    evidence_ids=[preuve],
    domain="python",
)
rapport_id, _ = Tester(memoire).test(
    hypothese,
    original=lambda: True,
    paraphrases=(lambda: True, lambda: True, lambda: True),
    regressions=(lambda: True,),
)
resultat = Secau(memoire).review(
    hypothese,
    rapport_id,
    {"evidence_ids": [preuve]},
)
print(resultat.verdict)
memoire.close()
```

Pour les opérations PC, `FileExecutor` exige une racine explicite. Il ne reçoit
jamais de commande shell. Une suppression doit utiliser `fs.delete_to_trash`,
être confirmée dans le plan, puis peut être annulée avec
`executor.rollback(transaction.id)`.

## Limites assumées

- l’extraction vise les documents structurés et les définitions explicites ;
- la recherche Internet n’est pas exécutée automatiquement par le kernel ;
- aucune skill candidate n’est activée sans rapport de test ;
- le sandbox local doit être renforcé au niveau OS avant d’exécuter du code
  provenant d’une source non fiable ;
- le corpus linguistique reste celui du prototype et conserve deux cas holdout
  connus et documentés.
