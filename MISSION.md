# Mission K.A.I.R.O.S. — moteur interne autonome et majoritairement hors ligne

## 1. Mission reçue

Construire la meilleure fondation possible pour un cerveau artificiel local capable de **grandir**, sans dépendre d’Internet pour la majorité de son fonctionnement.

L’autorisation générale donnée par le créateur signifie que les choix techniques nécessaires à cette mission peuvent être pris sans interrompre le développement. Elle ne transforme cependant pas une hypothèse en vérité et ne donne jamais à Kairos une permission implicite d’accéder au shell, au matériel, au réseau ou de promouvoir une connaissance non testée.

## 2. Verdict honnête

La V0.18 n’est pas une intelligence générale ni un cerveau conscient. C’est un **moteur interne autonome expérimental** qui relie enfin plusieurs organes déjà présents :

```text
mémoire cognitive
→ inventaire du travail réel
→ contexte local
→ priorité par gain
→ Tester / SECAU dans le laboratoire si possible
→ une question humaine si nécessaire
→ rapport persistant
→ sommeil si aucun travail utile
```

La différence avec V0.17 est importante : Kairos n’attend plus qu’un humain choisisse manuellement la prochaine candidate à consolider. Il inspecte lui-même son état, classe les candidats et choisit le prochain travail utile.

## 3. Choix structurants

### 3.1 Hors ligne par défaut

Le moteur V0.18 refuse de démarrer si sa configuration interne active le réseau.

```json
{
  "network": false,
  "mode": "offline_first"
}
```

Un cycle interne utilise :

- la base SQLite locale ;
- les concepts confirmés ;
- les relations confirmées ;
- les hypothèses candidates ;
- les rapports Tester existants ;
- le laboratoire Self-Correction ;
- les réponses déjà données par le créateur.

Le rapport expose `reseau_utilise=false` et `ratio_hors_ligne=1.0` pour chaque cycle V0.18.

### 3.2 Ne pas inventer du travail

Quand aucune candidate n’existe, Kairos passe en état :

```text
sleeping / no_internal_work
```

Un moteur autonome ne doit pas créer artificiellement un problème pour paraître actif.

### 3.3 Une seule question utile

Lorsqu’une candidate est incomplète, Kairos ne pose pas toutes les questions. Il choisit le manque avec le meilleur gain :

| Manque | Gain attendu |
|---|---:|
| Relation principale | 40 |
| Exemples | 25 |
| Contre-exemples | 20 |
| Source vérifiable | 15 |

Une question déjà en attente n’est pas dupliquée au cycle suivant.

### 3.4 Réutiliser la mémoire sans la confondre avec une preuve

Kairos recherche les concepts et relations confirmés proches de la candidate. Ces voisins deviennent `internal_context`.

Ils servent à poser une meilleure question, mais :

- ils ne deviennent pas des `evidence_ids` ;
- ils ne valident pas la candidate ;
- ils ne suffisent pas pour une promotion ;
- la réponse proposée permet toujours « aucun » afin d’éviter une analogie forcée.

### 3.5 Tester et SECAU réels lorsqu’un contrat existe

Une candidate devient `local_review` si :

- elle provient de `information.search` ;
- elle représente un changement causal `behavior.change` ;
- un rapport Tester local lui est déjà lié.

Le moteur appelle alors le laboratoire Self-Correction sur une copie de la mémoire. Les verdicts ne modifient pas silencieusement la connaissance de production.

### 3.6 Refuser la fausse autonomie

Une candidate complète mais sans contrat Tester est marquée :

```text
blocked / no_executable_contract
```

Kairos ne fabrique pas un test et ne considère pas la structure du dossier comme une preuve de vérité.

### 3.7 Promotion autonome en production interdite

La configuration exige :

```json
{
  "production_promotion": false
}
```

La V0.18 peut enrichir le contexte d’une candidate, sélectionner une question et tester dans le laboratoire. Elle ne peut pas promouvoir une connaissance dans le cerveau principal.

## 4. Architecture livrée

```text
kairos/interne/
├── __init__.py
├── __main__.py
├── modeles.py
└── moteur.py

data/cognition/
└── internal_engine.json

memory/internal_runs/
├── internal_<date>_<id>.json
└── latest.json
```

### Types de travail

```text
local_review
human_question
blocked
```

### États d’un cycle

```text
sleeping
waiting_human
worked
blocked
```

## 5. Contrat du cycle interne

Entrée : état actuel de `memory/cognition.db`.

Sortie : un rapport contenant :

- les candidates observées ;
- leur priorité ;
- leur type de travail ;
- les manques détectés ;
- le contexte local trouvé ;
- la question sélectionnée ;
- le résultat du laboratoire ;
- les compteurs avant/après ;
- l’usage du réseau ;
- la raison d’arrêt.

Un cycle est synchrone. Aucun daemon n’est créé.

## 6. Commandes

Après installation :

```bash
kairos-internal on
kairos-internal status
kairos-internal off
```

Ou directement :

```bash
python -m kairos.interne on
```

Alias reconnus par le parseur interne :

```text
internal-engine=on
internal-engine=status
internal-engine=off
moteur-interne=on
moteur-interne=statut
growup=on
```

## 7. Ce que le moteur peut réellement faire

1. Scanner les hypothèses candidates locales.
2. Chercher des concepts et relations confirmés proches.
3. Enregistrer ces rapprochements comme contexte non probant.
4. Déterminer si Tester/SECAU peut être appelé.
5. Lancer la self-correction dans le laboratoire.
6. Choisir la meilleure question restante.
7. Conserver cette question dans la session d’apprentissage.
8. Éviter de reposer la même question en attente.
9. Produire un rapport JSON auditable.
10. Dormir lorsqu’aucun travail utile n’existe.

## 8. Ce que le moteur ne peut pas encore faire

- découvrir seul une vérité sans observation ni source ;
- inventer un bon test pour n’importe quelle candidate ;
- transformer automatiquement une piste locale en preuve ;
- importer automatiquement les conclusions du laboratoire ;
- apprendre toute la langue française ;
- écrire et exécuter librement du code ;
- contrôler un ordinateur ou une carte Arduino ;
- garantir qu’une relation statistiquement utile est vraie ;
- fonctionner comme une conscience humaine.

## 9. Mesures de validation V0.18

Les portes ajoutées vérifient notamment :

- sommeil sans candidate ;
- une seule question à gain maximal ;
- aucune duplication de question ;
- lancement du laboratoire à la frontière réelle Tester/SECAU ;
- blocage sans contrat Tester ;
- réutilisation du contexte local sans création de preuve ;
- refus du réseau interne ;
- refus de la promotion autonome ;
- rapport persistant ;
- aucune modification des compteurs de connaissance de production pendant une question.

Le benchmark dédié contient 12 contrôles.

## 10. Pourquoi cette architecture sert le but final

Le but n’est pas de donner à Kairos une longue chaîne rigide. Le but est de lui donner une boucle minimale qui lui permet de répondre à quatre questions essentielles :

```text
Qu’est-ce qui manque réellement ?
Que puis-je faire localement maintenant ?
Quel résultat prouverait un progrès ?
Quand dois-je demander de l’aide ou dormir ?
```

Cette boucle est évolutive car les nouveaux Tester, fournisseurs locaux, capacités causales et skills pourront produire de nouveaux types de travail sans réécrire le principe central.

## 11. Prochaine porte rationnelle

La prochaine étape ne doit pas être davantage de vocabulaire. Elle doit être un **générateur de contrats Tester** limité à quelques familles observables :

```text
definition
classification
relation sémantique
route d’action
résultat causal
```

Pour chaque famille, Kairos devra générer des cas positifs, des cas négatifs et un replay, puis mesurer si la nouvelle relation améliore réellement les résultats. Tant que ce mécanisme n’existe pas, une grande partie des candidates restera correctement bloquée.

## 12. Principe non négociable

> Kairos peut travailler seul sur ce qu’il peut observer et tester. Lorsqu’il ne peut ni observer ni tester, son autonomie consiste à poser la meilleure question ou à s’arrêter — jamais à inventer.
