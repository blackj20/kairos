# K.A.I.R.O.S. — cerveau évolutif local

K.A.I.R.O.S. est un moteur symbolique, local et explicable. Il analyse une
requête française, estime son intention, choisit une route, demande les
informations manquantes et conserve les réponses comme expériences.

La **V0.5** ajoute **Skill Factory** : un plan GrowUp déjà validé peut devenir
une skill candidate pure, testée et versionnée. La candidate reste inactive tant
qu’un approbateur humain déclaré n’a pas fourni le rapport exact qui couvre son
contenu.

> Statut honnête : prototype opérationnel de compréhension, décision, mémoire,
> apprentissage supervisé et génération contrôlée de skills pures. Ce n’est pas
> une intelligence générale.

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
- transformer un plan `promoted` en skill candidate pure ;
- analyser le manifeste, les permissions, le code et les tests de la candidate ;
- exécuter les tests dans un processus isolé avec timeout et quotas ;
- lier le rapport à une empreinte SHA-256 de l’artefact ;
- activer explicitement une version après approbation du créateur ;
- restaurer une version précédente avec son chemin, son rapport et son empreinte.

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
python benchmark.py
python holdout.py
python decision_benchmark.py
python growup_benchmark.py
python skill_factory_benchmark.py
python user_acceptance.py
python user_acceptance_additional.py
```

La CI exécute ces portes sous Python 3.11, 3.12 et 3.13 avec `fail-fast: false`.
Une version qui échoue n’annule donc pas le diagnostic des deux autres.

## Suite logique

La prochaine porte ne doit pas être un shell libre. Elle devra introduire des
**outils PC limités**, chacun avec permission explicite, simulation, journal,
confirmation humaine, timeout et rollback. Skill Factory restera responsable de
la génération et des preuves ; un autre organe devra contrôler les effets réels.
