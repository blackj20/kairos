# État vérifié de K.A.I.R.O.S.

## Statut

**V0.4 — prototype opérationnel de compréhension, décision et apprentissage supervisé orchestré par GrowUp.**

Ce statut signifie que le projet est installable depuis un clone propre,
démarre, analyse une requête, bloque les actions incomplètes, relie une réponse
à une question, conserve l’expérience après redémarrage, regroupe les difficultés
similaires et produit des plans d’apprentissage traçables.

Il ne signifie pas que Kairos est une intelligence générale, qu’il apprend sans
source, ni qu’il peut exécuter librement du code ou naviguer sans contrôle dans
le PC.

## Commandes reproductibles

```bash
python -m pip install -e .
kairos --smoke-test
kairos --growup-scan
python -m unittest discover -s tests -v
python benchmark.py
python holdout.py
python decision_benchmark.py
python growup_benchmark.py
```

## Portes validées

- installation depuis un checkout propre ;
- commande `kairos` disponible ;
- smoke test du kernel, des connaissances, de la décision et de la réponse ;
- scan GrowUp installé et exécutable ;
- 90 tests automatisés réussis ;
- validation CI sous Python 3.11, 3.12 et 3.13 ;
- persistance `question → réponse → expérience → redémarrage` ;
- aucune promotion automatique d’une expérience ;
- regroupement des expériences et événements décrivant le même manque ;
- comptage sans doublement des occurrences ;
- priorité expliquée par fréquence, impact, risque et vérifiabilité ;
- plans GrowUp persistants et audités ;
- conflit de sens envoyé au créateur pour clarification ;
- consolidation `Réfléchir → Tester → SECAU` ;
- deux preuves, trois exemples et deux contre-exemples obligatoires ;
- rapports liés à leur propre hypothèse ;
- activation d’une relation seulement après verdict `promote` ;
- sources Internet limitées à deux domaines HTTPS distincts ;
- benchmarks transformés en barrières avec code de sortie non nul ;
- zéro fausse exécution exigée par les seuils.

## Boucle d’apprentissage démontrée

```text
incompréhension
→ question ciblée
→ réponse du créateur
→ expérience non confirmée
→ GrowUp collecte
→ GrowUp regroupe
→ GrowUp calcule la priorité
→ GrowUp produit un plan
→ preuves + exemples + contre-exemples
→ Réfléchir crée l’hypothèse
→ Tester produit un rapport
→ SECAU promeut, rejette ou met en quarantaine
→ relation confirmée éventuellement réutilisée
```

## Invariants

```text
GrowUp.analyser() ne modifie jamais une connaissance confirmée.
Une expérience n’est jamais une preuve suffisante à elle seule.
Un rapport ne peut valider qu’une hypothèse correspondante.
Une relation conflictuelle ne peut pas atteindre Tester.
Une relation non promue ne peut pas entrer dans le lexique actif.
```

## Résultats de validation

| Porte | Résultat |
|---|---:|
| Tests automatisés | 90/90 |
| Python | 3.11, 3.12, 3.13 |
| Installation propre | réussie |
| Smoke test | réussi |
| Scan GrowUp | réussi |
| Benchmark Comprendre | réussi |
| Benchmark holdout | réussi |
| Benchmark Décision | réussi |
| Benchmark GrowUp | réussi |
| Fausses exécutions | 0 autorisée |

## Prochaine porte

La prochaine étape est la V0.5 : génération de **skills candidates** à partir
d’un plan validé. La candidate devra rester inactive jusqu’à la réussite de
l’analyse statique, du sandbox, des tests, du contrôle des permissions et du
rollback.
