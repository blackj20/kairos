K.A.I.R.O.S. — architecture complète d’un cerveau évolutif

1. Objectif réel

K.A.I.R.O.S. ne doit pas être un programme qui accumule des réponses. Sonobjectif est de transformer progressivement ses incompréhensions en capacitésréutilisables :

observer
→ comprendre
→ décider
→ demander
→ apprendre
→ tester
→ consolider
→ réutiliser
→ corriger

Une connaissance n’est pas maîtrisée parce qu’elle est enregistrée. Elle estmaîtrisée quand Kairos peut :

la reconnaître sous plusieurs formulations ;

la relier à d’autres concepts ;

l’utiliser pour répondre ou agir ;

détecter les cas où elle ne s’applique pas ;

réussir ses tests sans casser les anciennes capacités.

2. Limite fondamentale

Kairos ne peut pas apprendre Python depuis le néant. Il lui faut au moins unesource :

une réponse de son créateur ;

un document local ;

une documentation technique ;

plusieurs sources Internet vérifiées ;

une compétence déjà confirmée.

Son noyau ne contient pas toutes les connaissances. Il contient lesmécanismes génériques pour apprendre :

chercher une source
extraire des concepts
poser une question
créer une hypothèse
produire des exemples
tester
mesurer les contradictions
versionner
promouvoir ou rejeter

Sans source, « apprendre seul » serait seulement inventer.

3. Vue générale

flowchart TD
    U["Utilisateur ou événement"] --> K["Kernel"]
    K --> C["Comprendre"]
    C --> D["Décision"]
    D --> R["Répondre"]
    D --> Q["Demande"]
    D --> P["Processus"]
    Q --> E["Expérience"]
    E --> G["GrowUp"]
    G --> F["Réfléchir"]
    F --> T["Tester"]
    T --> S["SECAU"]
    S --> M["Mémoire confirmée"]
    S --> B["Skill Builder"]
    B --> X["Sandbox"]
    X --> SR["Skill Registry"]
    SR --> K

4. Invariants

Le kernel orchestre ; il ne comprend, ne parle et n’apprend pas.

Comprendre est en lecture seule.

Évaluer et ChoisirRoute ne produisent aucun effet de bord.

VerifierDecision autorise une route, mais ne crée aucune donnée.

Demande crée uniquement une question en attente.

Expérience conserve un épisode, jamais une vérité.

Réfléchir produit des hypothèses et des propositions de modification.

Tester mesure ; il ne modifie pas les résultats pour réussir.

SECAU promeut, rejette ou met en quarantaine.

Une skill candidate n’est jamais exécutable directement.

Toute modification possède une version, une preuve et un retour arrière.

L’identité, l’objectif central et les permissions exigent l’accord ducréateur.

Aucune donnée sensible ne doit entrer dans l’apprentissage sansautorisation.

Zéro fausse exécution reste une condition de progression.

5. Organisation cible

kairos/
├── kernel/
│   ├── event.py
│   ├── kernel.py
│   ├── queue.py
│   └── scheduler.py
├── language/
│   ├── comprendre.py
│   ├── decouper.py
│   ├── sens.py
│   ├── contexte.py
│   ├── estimation.py
│   └── verifier_analyse.py
├── decision/
│   ├── evaluer.py
│   ├── choisir_route.py
│   ├── verifier_decision.py
│   ├── demande.py
│   └── experience.py
├── cognition/
│   ├── grow_up.py
│   ├── reflechir.py
│   ├── relier.py
│   ├── tester.py
│   ├── secau.py
│   └── planifier.py
├── learning/
│   ├── acquire.py
│   ├── extract.py
│   ├── hypothesis.py
│   ├── consolidate.py
│   ├── provenance.py
│   └── curriculum.py
├── skills/
│   ├── builder.py
│   ├── manifest.py
│   ├── registry.py
│   ├── scanner.py
│   ├── sandbox.py
│   └── rollback.py
├── process/
│   ├── planner.py
│   ├── executor.py
│   ├── permissions.py
│   ├── filesystem.py
│   ├── applications.py
│   └── transactions.py
├── memory/
│   ├── working.py
│   ├── episodic.py
│   ├── semantic.py
│   ├── procedural.py
│   ├── repository.py
│   └── audit.py
├── response/
│   ├── contract.py
│   ├── composer.py
│   └── verifier.py
├── self/
│   ├── identity.py
│   ├── objective.py
│   ├── capabilities.py
│   └── limits.py
└── interfaces/
    ├── cli.py
    ├── api.py
    └── events.py

data/
├── fr/
├── decision/
├── policies/
└── templates/

memory/
├── kairos.db
├── audit.jsonl
├── pending_questions.json
└── checkpoints/

skills/
├── candidates/
├── active/
├── quarantined/
└── archived/

6. Organes

Organe

Entrée

Sortie

Écriture autorisée

Kernel

événement

résultat orchestré

audit uniquement

Comprendre

texte + contexte

AnalysisReport

aucune

Évaluer

analyse

scores et manques

aucune

ChoisirRoute

évaluation

route proposée

aucune

VerifierDecision

route + règles

verdict

aucune

Demande

manque identifié

question

questions en attente

Expérience

épisode complet

événement

mémoire épisodique

Réfléchir

expériences

hypothèses

hypothèses uniquement

Relier

hypothèse + mémoire

relations candidates

hypothèses

Tester

candidat

rapport de tests

rapports

SECAU

rapports

promotion/rejet

mémoire contrôlée

Skill Builder

spécification validée

skill candidate

candidates

Skill Registry

skill validée

version active

registre

Processus

plan autorisé

effets PC

transaction + audit

Répondre

contrat de sortie

texte

aucune

7. Kernel événementiel

Le kernel final ne doit pas utiliser une boucle qui consomme inutilement leprocesseur. Il doit attendre des événements :

class Kernel:
    async def run(self) -> None:
        while self.running:
            event = await self.queue.get()
            try:
                result = await self.handle(event)
                await self.audit.success(event, result)
            except Exception as error:
                await self.audit.failure(event, error)

Événements possibles :

USER_MESSAGE
QUESTION_ANSWERED
LEARNING_REQUESTED
CONSOLIDATION_REQUESTED
SKILL_TEST_FINISHED
PROCESS_FINISHED
SCHEDULED_REVIEW
SYSTEM_ERROR

Le kernel connaît seulement les contrats :

class Component(Protocol):
    async def handle(self, event: Event) -> Result: ...

8. Mémoire

8.1 Pourquoi ne pas tout garder en JSON

JSON convient aux règles statiques et aux petits prototypes. Pour une mémoireévolutive, tout conserver dans de gros JSON crée :

des recherches lentes ;

des écritures concurrentes dangereuses ;

des doublons ;

des fichiers entièrement corrompus après une mauvaise écriture ;

aucune transaction fiable.

Architecture recommandée :

Donnée

Stockage

règles françaises

JSON versionné

politiques et seuils

JSON versionné

événements immuables

JSONL append-only

mémoire évolutive

SQLite

skills

fichiers + registre SQLite

versions du code

Git

checkpoints

archives signées

SQLite est disponible dans Python sans serveur externe.

8.2 Types de mémoire

Mémoire de travail
→ contexte de la session actuelle

Mémoire épisodique
→ questions, réponses, erreurs et résultats

Mémoire sémantique
→ concepts et relations confirmés

Mémoire procédurale
→ skills et méthodes confirmées

Mémoire hypothétique
→ éléments à tester

Mémoire self
→ identité, maison, objectif, capacités et limites

8.3 Tables principales

CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    definition TEXT,
    mastery_score INTEGER NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    source_concept_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_concept_id TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    evidence_id TEXT NOT NULL
);

CREATE TABLE evidence (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    trust_score INTEGER NOT NULL,
    collected_at TEXT NOT NULL
);

CREATE TABLE hypotheses (
    id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    score INTEGER NOT NULL,
    created_from_experience_id TEXT NOT NULL
);

CREATE TABLE experiences (
    id TEXT PRIMARY KEY,
    request TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    feedback_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    active_version TEXT,
    status TEXT NOT NULL,
    mastery_score INTEGER NOT NULL
);

CREATE TABLE skill_versions (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    version TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    test_report_id TEXT NOT NULL,
    status TEXT NOT NULL
);

9. Cycle d’apprentissage

UNKNOWN
  ↓
TO_STUDY
  ↓
QUESTION_PENDING ou SOURCE_REQUIRED
  ↓
EXPERIENCE_RECORDED
  ↓
HYPOTHESIS
  ↓
LINKED
  ↓
TESTING
  ├── REJECTED
  ├── NEEDS_MORE_EVIDENCE
  └── VERIFIED
         ↓
     CONFIRMED
         ↓
      REUSED
         ↓
      MASTERED

9.1 Détection

score 0–30
→ explication prioritaire

score 31–50
→ clarification + étude

score 51–84
→ confirmation

score ≥ 85
→ route autorisée après vérification

score 100
→ maîtrise démontrée, jamais simple confiance

9.2 Acquisition

Trois modes, dans cet ordre :

enseignement structuré : le créateur répond ;

document local : Kairos extrait titres, définitions et exemples ;

recherche externe : plusieurs sources avec provenance.

Une source produit une Evidence, pas directement une connaissance.

9.3 Extraction

Le moteur d’extraction doit produire :

{
  "concept": "classe Python",
  "definition_candidate": "modèle permettant de créer des objets",
  "relations": [
    ["classe Python", "crée", "objet Python"],
    ["classe Python", "contient", "méthode"]
  ],
  "examples": ["class Personne: ..."],
  "source_refs": ["evidence_001"],
  "confidence": 62
}

Extraire du texte technique général est difficile. Sans modèle linguistiquepuissant, la première version doit privilégier :

les documents structurés ;

les définitions explicites ;

les blocs de code ;

les réponses guidées du créateur.

9.4 Consolidation

Une hypothèse est confirmée seulement si :

la source est identifiable ;

aucun conflit non résolu n’existe ;

la question originale est réussie ;

au moins trois reformulations sont réussies ;

tous les tests de régression passent ;

aucune permission interdite n’est demandée.

10. Réfléchir

Réfléchir est un orchestrateur cognitif :

Lire les événements faibles
→ regrouper les problèmes
→ prioriser
→ appeler Demande ou Acquire
→ Relier
→ créer une hypothèse
→ Tester
→ appeler SECAU

Il ne doit pas écrire directement dans la mémoire confirmée.

Priorité d’un problème :

priority =
    faiblesse_du_score
  + fréquence
  + importance_pour_objectif
  + risque_si_erreur
  - coût_d_apprentissage

11. SECAU

SECAU réalise l’audit automatique final :

structure valide ?
provenance présente ?
relations cohérentes ?
contradictions résolues ?
tests originaux réussis ?
trois reformulations réussies ?
régression complète réussie ?
permissions respectées ?
rollback disponible ?

Résultats :

PROMOTE
REJECT
QUARANTINE
NEEDS_MORE_EVIDENCE
ROLLBACK

SECAU peut promouvoir une connaissance ordinaire. Il ne peut pas modifierautomatiquement :

self/identity ;

l’objectif central ;

les permissions ;

la relation avec le créateur ;

les politiques de sécurité ;

son propre système de validation.

12. Architecture d’une skill

Une skill n’est pas seulement un fichier .py. Elle doit avoir :

skills/candidates/python_explain/
├── skill.json
├── handler.py
├── knowledge/
│   ├── concepts.json
│   └── examples.json
├── tests/
│   ├── cases.json
│   └── test_handler.py
└── evidence/
    └── sources.json

12.1 Manifest

{
  "id": "python.explain",
  "name": "Expliquer Python",
  "version": "0.1.0",
  "status": "candidate",
  "entrypoint": "handler:run",
  "intents": ["lecon", "question"],
  "domains": ["python"],
  "input_schema": {
    "question": "string",
    "concept": "string"
  },
  "output_schema": {
    "answer": "string",
    "evidence": "array"
  },
  "permissions": {
    "network": false,
    "filesystem_read": [],
    "filesystem_write": [],
    "process": false,
    "shell": false
  },
  "limits": {
    "timeout_seconds": 2,
    "memory_mb": 64
  },
  "mastery_score": 0,
  "source_hash": null,
  "test_report": null
}

12.2 Contrat

from typing import Protocol

class Skill(Protocol):
    def can_handle(self, request: dict) -> int:
        """Retourne un score entre 0 et 100."""

    def run(self, request: dict, context: dict) -> dict:
        """Retourne une sortie conforme au manifest."""

Le kernel ne cherche pas les fichiers au hasard. Il interroge SkillRegistry,qui retourne uniquement les versions actives.

13. Création automatique d’une skill

Besoin répété détecté
→ SkillSpec proposée
→ permissions minimales calculées
→ scaffold créé depuis un template
→ code candidat généré
→ analyse AST
→ tests syntaxiques
→ tests unitaires
→ tests de sécurité
→ exécution sandbox
→ régression globale
→ SECAU
→ candidate, active ou quarantined

13.1 Règles de génération

Interdits par défaut :

eval ;

exec ;

compile sur une entrée utilisateur ;

imports os, subprocess, socket, ctypes ;

shell ;

écriture hors dossier temporaire ;

réseau ;

installation automatique de paquets ;

modification du kernel.

Le scanner utilise ast.parse() pour inspecter :

imports ;

appels interdits ;

accès aux attributs dangereux ;

code exécuté au chargement ;

conformité de l’entrypoint.

Une analyse Python seule n’est pas un sandbox de sécurité. L’exécution réelledoit être isolée au niveau du système d’exploitation avec :

processus séparé ;

utilisateur sans privilèges ;

système de fichiers limité ;

réseau désactivé ;

limite CPU et mémoire ;

timeout ;

dossier temporaire détruit après test.

14. Exemple : apprendre les classes Python

État initial

Question : « C’est quoi une classe Python ? »
Mémoire Python : vide
Score : 22 %
Route : ETUDIER

Étape 1 — détecter

{
  "topic": "classe Python",
  "missing": ["definition", "relations", "examples"],
  "score": 22,
  "status": "to_study"
}

Étape 2 — acquérir

Kairos demande :

« Puis-je consulter une documentation Python ou veux-tu me l’expliquer ? »

Il collecte ensuite une ou plusieurs preuves.

Étape 3 — extraire

Concepts candidats :

classe
objet
instance
attribut
méthode
héritage
constructeur

Relations candidates :

classe → crée → instance
instance → appartient à → classe
classe → contient → méthode
instance → possède → attribut
__init__ → initialise → instance

Étape 4 — construire la skill candidate

Skill Builder produit :

python.explain
python.example.class
python.validate.example

La première skill formule une explication depuis les connaissances confirmées.La deuxième utilise uniquement des modèles de code validés. La troisièmevérifie la syntaxe des exemples.

Étape 5 — tester

Questions :

Qu’est-ce qu’une classe Python ?
À quoi sert une classe ?
Quelle différence entre classe et objet ?
Comment créer une classe simple ?
Que fait __init__ ?

Contre-exemples :

Une fonction est-elle toujours une classe ?
Une instance et une classe sont-elles identiques ?
Faut-il toujours utiliser l’héritage ?

Les exemples de code sont compilés et testés dans le sandbox.

Étape 6 — activer

Si tous les contrôles passent :

{
  "skill": "python.explain",
  "status": "active",
  "mastery_score": 100,
  "verified_paraphrases": 3,
  "regressions": 0,
  "rollback_version": "none"
}

Sinon, la skill reste candidate ou part en quarantaine.

Vérité technique

Un moteur symbolique peut construire ce workflow et utiliser des modèlesparamétrés. Il ne pourra pas générer de manière fiable n’importe quel nouveauprogramme Python sans :

un moteur de synthèse de code ;

un modèle génératif ;

ou des templates procéduraux déjà disponibles.

Kairos peut donc apprendre progressivement des concepts et des procéduresencadrées. Il ne doit pas prétendre inventer correctement tout Python depuisquelques règles françaises.

15. Répondre

Répondre reçoit un contrat final :

{
  "mode": "explanation",
  "intent": "lecon",
  "concepts": ["classe Python", "instance", "méthode"],
  "skill": "python.explain",
  "evidence_ids": ["evidence_001"],
  "constraints": {
    "language": "fr",
    "max_length": 500
  }
}

Il ne décide ni du sujet ni de la route. Il compose, puis VerifierReponsecontrôle :

cohérence avec la question ;

présence des éléments demandés ;

absence d’affirmation sans preuve ;

respect des limites ;

correspondance avec la décision.

16. Processus : naviguer dans le PC

Processus sera ajouté seulement après la compréhension, la décision et lesskills contrôlées.

16.1 Architecture

Demande utilisateur
→ Comprendre
→ Décision
→ Planifier
→ VerifierPlan
→ Prévisualiser
→ demander permission si nécessaire
→ Exécuter transaction
→ Vérifier résultat
→ Audit
→ Commit ou rollback

16.2 Outils autorisés

fs.list
fs.stat
fs.read
fs.search
fs.create_directory
fs.copy
fs.move
fs.rename
fs.delete_to_trash
app.list
app.open
process.status

Kairos ne reçoit jamais un outil générique shell(command).

16.3 Niveaux de risque

Niveau

Exemples

Règle

lecture

lister, rechercher, lire

autorisable par politique

modification réversible

copier, créer, renommer

prévisualisation + audit

modification sensible

déplacer beaucoup de fichiers

confirmation

destruction

supprimer, écraser

corbeille + confirmation

système

installer, services, permissions

confirmation forte

interdit

désactiver sécurité, voler secrets

refus

16.4 Plan

{
  "goal": "ranger les fichiers Python dans Projets",
  "steps": [
    {
      "tool": "fs.search",
      "arguments": {"root": "~/Téléchargements", "pattern": "*.py"},
      "risk": "read"
    },
    {
      "tool": "fs.create_directory",
      "arguments": {"path": "~/Projets/Python"},
      "risk": "reversible_write"
    },
    {
      "tool": "fs.move",
      "arguments": {
        "sources_from": "step_1",
        "destination": "~/Projets/Python"
      },
      "risk": "sensitive_write",
      "requires_confirmation": true
    }
  ]
}

Chaque plan possède :

préconditions ;

effets attendus ;

permissions ;

niveau de risque ;

validation ;

étapes compensatoires ;

preuve du résultat.

17. Sécurité et gouvernance

17.1 Permissions

créateur
→ enseigner, confirmer, activer une skill, autoriser une action sensible

superviseur
→ tester et confirmer les actions autorisées

utilisateur
→ demander, répondre et utiliser les skills publiques

skill
→ uniquement les permissions de son manifest

17.2 Provenance

Chaque connaissance confirmée conserve :

{
  "sources": ["evidence_001", "experience_014"],
  "created_by": "reflechir",
  "validated_by": "secau",
  "approved_by": null,
  "version": 3,
  "content_hash": "sha256:...",
  "rollback_to": 2
}

17.3 Audit

audit.jsonl est append-only :

{"event":"SKILL_CREATED","skill":"python.explain","version":"0.1.0"}
{"event":"SKILL_TESTED","result":"passed","report":"test_021"}
{"event":"SKILL_ACTIVATED","actor":"creator_001"}

18. Scores

Ne pas utiliser un pourcentage unique pour tout.

language_score
decision_score
source_trust_score
hypothesis_score
test_score
reuse_score
mastery_score
risk_score

mastery_score = 100 exige :

compréhension complète du périmètre ;

source vérifiée ;

aucune contradiction active ;

tests réussis ;

trois reformulations réussies ;

régression réussie ;

réutilisation réussie.

Un score de 100 ne signifie jamais vérité universelle.

19. Interfaces internes

class KnowledgeRepository(Protocol):
    def search(self, query: dict) -> list[dict]: ...
    def add_hypothesis(self, hypothesis: dict) -> str: ...
    def promote(self, hypothesis_id: str, report_id: str) -> str: ...


class SkillRegistry(Protocol):
    def candidates(self, request: dict) -> list[dict]: ...
    def activate(self, skill_id: str, version: str, report_id: str) -> None: ...
    def rollback(self, skill_id: str, version: str) -> None: ...


class SandboxRunner(Protocol):
    def validate(self, candidate_path: str) -> dict: ...
    def run_tests(self, candidate_path: str) -> dict: ...


class ToolExecutor(Protocol):
    def preview(self, plan: dict) -> dict: ...
    def execute(self, approved_plan: dict) -> dict: ...
    def rollback(self, transaction_id: str) -> dict: ...

Les composants dépendent de ces interfaces, pas de fichiers précis. Celapermet de remplacer JSON par SQLite ou un sandbox local sans réécrire lecerveau.

20. Tests

Comprendre

intentions ;

négations ;

ambiguïtés ;

paraphrases ;

contexte conversationnel ;

mots inconnus.

Décision

champs manquants ;

actions multiples ;

route incohérente ;

permissions ;

fausses exécutions ;

questions ciblées.

Apprentissage

question correctement reliée ;

hypothèse non promue directement ;

provenance obligatoire ;

trois reformulations ;

contradiction ;

non-régression.

Skills

manifest ;

AST ;

imports ;

permissions ;

timeout ;

mémoire ;

sortie conforme ;

quarantaine ;

rollback.

Processus PC

traversal de chemin ;

lien symbolique ;

suppression ;

écrasement ;

permissions ;

dry-run ;

transaction ;

rollback ;

audit.

21. Roadmap

Phase 1 — Comprendre

Statut : fondation existante.

Phase 2 — Décision

Statut : V0.3 existante.

Phase 3 — Répondre

Objectif :

contrat de réponse ;

composition depuis connaissances confirmées ;

vérification de cohérence ;

aucune invention.

Porte :

≥ 90 % réponses cohérentes
100 % respect de la décision
0 affirmation sans source dans les tests critiques

Phase 4 — GrowUp et Réfléchir

Objectif :

lire les événements faibles ;

poser les questions ;

créer les hypothèses ;

relier les réponses.

Porte :

100 % réponses liées
≥ 90 % hypothèses correctement typées
0 promotion directe

Phase 5 — Tester et SECAU

Objectif :

tests automatiques ;

reformulations ;

régression ;

promotion contrôlée ;

rollback.

Porte :

100 % promotions accompagnées d’un rapport
100 % rollback fonctionnel
0 modification des données protégées

Phase 6 — Skill Builder

Objectif :

manifest ;

scaffold ;

scanner AST ;

sandbox ;

registre ;

versions.

Porte :

100 % skills candidates isolées
0 permission implicite
0 activation sans tests
100 % rollback

Phase 7 — Démonstration Python

Point de départ : mémoire du domaine Python vide.

Objectif :

acquérir une source ;

apprendre classe, objet, méthode, attribut ;

construire python.explain ;

répondre aux questions ;

tester les exemples.

Porte :

10/10 questions centrales
≥ 80 % questions nouvelles
3 reformulations par concept
100 % exemples exécutables dans le sandbox
0 régression

Phase 8 — Processus PC

Objectif :

lecture du PC ;

plans ;

permissions ;

transactions ;

modifications réversibles.

Porte :

100 % actions sensibles confirmées
100 % opérations destructives réversibles
0 accès hors périmètre
0 shell générique

22. Décisions à ne pas prendre

Tout mettre en JSON indéfiniment.

Donner au kernel le droit de comprendre ou d’écrire.

Autoriser Réfléchir à modifier directement la mémoire confirmée.

Exécuter une skill immédiatement après sa création.

Donner un accès shell libre à Processus.

Utiliser le score de confiance comme preuve de vérité.

Déclarer une connaissance maîtrisée après un seul exemple.

Ajouter des milliers de skills avant de valider la boucle d’apprentissage.

23. Définition finale du cerveau évolutif

Kairos sera réellement évolutif lorsqu’il pourra réussir ce scénario sansrègle spéciale écrite pour Python :

« Je ne comprends pas classe Python »
→ crée un événement
→ cherche ou demande une source
→ extrait des concepts
→ crée une hypothèse
→ construit une skill candidate
→ la teste dans un sandbox
→ rejette ou active
→ répond
→ réutilise sur une nouvelle question
→ détecte et corrige une erreur

Le cœur de l’intelligence ne sera pas le fichier Python créé. Ce sera leprocessus capable de produire, vérifier, utiliser et corriger ce fichier sanscorrompre le reste du système.
