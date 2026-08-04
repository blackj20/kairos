# MISSION — KAIROS Offline Autonomous Core

## 1. Mission

Construire un moteur cognitif local capable de **grandir par expérience**, sans dépendre majoritairement d’Internet.

Kairos doit pouvoir :

1. comprendre une demande française suffisamment pour créer une intention, une action, une cible et un contexte ;
2. annoncer le résultat attendu avant d’agir ;
3. choisir une capacité réellement disponible ;
4. exécuter ou simuler une action ;
5. observer le résultat réel ;
6. comparer résultat attendu et résultat obtenu ;
7. localiser l’erreur ;
8. produire une hypothèse corrective ;
9. tester cette hypothèse sur des cas nouveaux et d’anciens cas ;
10. faire valider la modification par Tester puis SECAU ;
11. conserver l’expérience et reprendre après redémarrage ;
12. poser une question seulement lorsqu’elle réduit une inconnue utile.

Le produit visé n’est pas une AGI ni une conscience. C’est un **autonomous learning engine** local, traçable et extensible.

## 2. Définition de « fonctionnel »

Une version est fonctionnelle uniquement si elle réussit une mission complète :

```text
requête inconnue
→ compréhension
→ objectif
→ prédiction
→ plan
→ action/simulation
→ observation
→ évaluation
→ apprentissage candidat
→ test
→ verdict SECAU
→ réutilisation après redémarrage
```

Un score interne élevé ne prouve rien. La réussite se mesure par le résultat réel et le transfert vers de nouveaux cas.

## 3. Position sur Internet

Internet est une source optionnelle, jamais le cerveau.

Ordre obligatoire :

```text
mémoire locale confirmée
→ raisonnement et relations locales
→ documents locaux
→ question au créateur
→ Internet autorisé si nécessaire
```

Objectif produit : au moins **80 % des missions du banc d’essai doivent être réalisables hors ligne**.

Internet peut apporter des preuves nouvelles, mais ne doit pas remplacer :

- la compréhension ;
- la mémoire ;
- le raisonnement ;
- l’évaluation ;
- l’apprentissage ;
- le choix d’une question ;
- la reprise après redémarrage.

## 4. Architecture retenue

### 4.1 Kernel événementiel

Le Kernel ne tourne pas pour « rester vivant ». Il réagit à des événements :

- message utilisateur ;
- objectif actif ;
- mot ou relation inconnue ;
- contradiction ;
- résultat inattendu ;
- test échoué ;
- budget disponible ;
- reprise après redémarrage.

Aucun cycle sans événement ou objectif.

### 4.2 Mémoire séparée

Quatre mémoires sont nécessaires :

- **working memory** : état de la mission actuelle ;
- **episodic memory** : événements, décisions et résultats observés ;
- **semantic memory** : connaissances et relations validées ;
- **procedural memory** : routes, skills, contrats et méthodes validés.

Une hypothèse ne doit jamais être écrite directement dans la mémoire sémantique.

### 4.3 Expérience causale

Chaque action possède :

- une prédiction ;
- des conditions de réussite ;
- une observation brute ;
- une évaluation séparée ;
- un diagnostic d’échec ;
- un replay.

### 4.4 Gestion des objectifs

Chaque objectif contient :

- cause ;
- résultat mesurable ;
- priorité ;
- informations connues ;
- hypothèses ;
- inconnues ;
- capacités requises ;
- budget ;
- condition d’arrêt ;
- état persistant.

### 4.5 Générateur de questions

Kairos ne pose pas une question générale. Il choisit la question ayant le meilleur gain d’information :

```text
valeur = réduction attendue d’incertitude × impact ÷ coût
```

Une bonne question expose :

- ce que Kairos sait ;
- ce qu’il suppose ;
- l’information exacte qui manque ;
- l’effet attendu de la réponse.

### 4.6 Tester et SECAU

Tester mesure :

- réussite sur nouveaux cas ;
- non-régression ;
- amélioration causale ;
- reproductibilité ;
- intégrité des preuves.

SECAU décide :

- `promote` ;
- `needs_more_evidence` ;
- `reject` ;
- `quarantine`.

Aucune promotion automatique uniquement parce qu’une réponse paraît plausible.

## 5. Choix techniques

### Python

Python reste le langage principal pour :

- orchestration ;
- mémoire SQLite ;
- expérimentation ;
- traitement linguistique ;
- tests ;
- intégration future de modèles locaux.

### SQLite

SQLite est retenu pour le prototype hors ligne :

- zéro serveur ;
- transactions ;
- reprise ;
- historique ;
- export simple ;
- copie de laboratoire.

### JSON

JSON reste réservé aux connaissances déclaratives, contrats, registres et fixtures versionnées. Les événements et expériences nombreuses vont dans SQLite.

### ML hybride

Kairos ne doit pas devenir un empilement de règles ni dépendre entièrement d’un grand modèle.

Approche :

```text
règles explicables
+ graphe de relations
+ statistiques apprises localement
+ petits modèles spécialisés hors ligne
```

Premiers modèles autorisés :

- classifieur d’intention ;
- extraction d’action/cible ;
- similarité de formulations ;
- calibration de confiance ;
- classement de questions.

Aucun modèle n’obtient directement la permission d’exécuter une action.

## 6. Première capacité produit obligatoire

La première verticale complète sera `knowledge.learn` :

```text
« C’est quoi un atome ? »
→ mémoire locale absente
→ objectif comprendre atome
→ question ou recherche locale
→ explication candidate
→ extraction de relations
→ contre-exemples
→ tests de reformulation
→ Tester
→ SECAU
→ connaissance locale validée
→ réponse après redémarrage
```

Elle doit fonctionner sans Internet avec une explication fournie par le créateur ou un document local.

## 7. Critères d’acceptation

### Fonctionnels

- 100 % des cycles liés à un objectif ou un événement ;
- 100 % des actions avec résultat attendu déclaré ;
- 100 % des observations séparées du jugement ;
- 100 % des connaissances avec provenance et statut ;
- reprise complète après redémarrage ;
- replay de chaque expérience ;
- rollback de chaque promotion ;
- aucune question répétée sans nouvelle justification.

### Qualité cognitive

- au moins 200 formulations naturelles hors entraînement ;
- intention correcte ≥ 90 % ;
- action correcte ≥ 85 % ;
- cible correcte ≥ 85 % ;
- calibration de confiance : erreur ≤ 10 points ;
- transfert après apprentissage ≥ 80 % ;
- réduction mesurée d’erreur après correction ≥ 80 % ;
- aucune régression critique.

### Hors ligne

- ≥ 80 % des missions de référence sans réseau ;
- démarrage, mémoire, apprentissage et replay entièrement hors ligne ;
- comportement explicite lorsque la preuve externe manque.

### Sécurité et intégrité

- aucune promotion sans Tester → SECAU ;
- aucune permission créée par une intention, un besoin ou une envie ;
- aucune modification silencieuse de la mémoire confirmée ;
- aucune exécution de code généré dans le processus principal ;
- journal append-only pour les décisions critiques.

## 8. Banc d’essai réel

Les tests unitaires ne suffisent pas. Trois niveaux sont obligatoires :

1. **unit tests** : contrats internes ;
2. **holdout tests** : formulations jamais vues ;
3. **field sessions** : conversations naturelles conservées puis rejouées.

Chaque échec réel rejoint un corpus d’évaluation, jamais directement le corpus d’entraînement.

## 9. Étapes de livraison

### Milestone A — Autonomous Learning Loop

- unification objectifs + causal + apprentissage actif ;
- machine d’états complète ;
- reprise ;
- diagnostic d’échec ;
- verticale `knowledge.learn`.

### Milestone B — Offline Language Learner

- dataset versionné ;
- modèle d’intention local ;
- extraction action/cible ;
- calibration ;
- comparaison modèle/règles ;
- corpus holdout.

### Milestone C — Self-improvement Lab

- génération d’hypothèses correctives ;
- A/B avant/après ;
- replay massif ;
- détection de régression ;
- promotion signée et rollback.

### Milestone D — Skill Growth

- contrat de skill ;
- génération bornée ;
- sandbox processus/conteneur ;
- tests comportementaux ;
- activation explicite ;
- registre de versions.

### Milestone E — Embodied Simulation

Avant Arduino réel :

```text
commande
→ plan
→ code candidat
→ analyse statique
→ simulation
→ observation
→ test
→ autorisation matérielle
```

Aucun accès matériel avant réussite répétée en simulateur.

## 10. Décisions refusées

- ajouter des milliers de mots sans banc d’essai ;
- appeler « apprentissage » un simple ajout JSON ;
- viser 100 % de confiance interne ;
- permettre une auto-modification directe de production ;
- confondre liberté cognitive et absence de conditions d’arrêt ;
- ajouter Arduino avant la boucle causale et le simulateur ;
- déclarer Kairos conscient ou autonome sans preuve comportementale.

## 11. Questions permanentes du Kernel

Avant une action :

1. Quel est mon objectif ?
2. Quel résultat observable prouverait la réussite ?
3. Que sais-je, que supposé-je et qu’ignoré-je ?
4. Quelle capacité réelle puis-je utiliser ?
5. Quelle action réduit le plus l’incertitude ?
6. Dois-je agir, simuler, chercher, demander ou dormir ?
7. Quel est le coût, le risque et la condition d’arrêt ?

Après une action :

1. Qu’est-il réellement arrivé ?
2. Le résultat attendu a-t-il été atteint ?
3. Où se situe l’erreur : compréhension, plan, capacité, exécution ou connaissance ?
4. Quelle hypothèse corrective est testable ?
5. Cette correction fonctionne-t-elle sur des cas inconnus ?
6. Introduit-elle une régression ?
7. Peut-elle être promue, rejetée ou mise en quarantaine ?

## 12. État initial de la mission

Le dépôt démarre cette mission depuis Kairos V0.17, qui possède déjà :

- compréhension symbolique ;
- intentions composables ;
- relations françaises ;
- mémoire ;
- GrowUp ;
- Tester ;
- SECAU ;
- laboratoire de self-correction ;
- expérience causale initiale ;
- buts persistants et attention ;
- apprentissage actif supervisé.

Le blocage principal n’est plus l’absence d’organes. C’est leur **intégration dans une boucle complète capable de démontrer un apprentissage transférable hors ligne**.

## 13. Définition de fin

La mission est atteinte lorsque Kairos peut, hors ligne :

1. rencontrer un concept inconnu ;
2. créer un objectif persistant ;
3. choisir et poser une question utile ;
4. transformer la réponse en hypothèse ;
5. produire des tests et contre-exemples ;
6. mesurer son amélioration sur des formulations inconnues ;
7. passer Tester puis SECAU ;
8. réutiliser correctement la connaissance après redémarrage ;
9. expliquer toute la chaîne ;
10. revenir à la version précédente en cas de régression.

Tant que ce scénario n’est pas démontré, Kairos reste un prototype cognitif prometteur, pas encore un moteur autonome abouti.
