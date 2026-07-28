# État vérifié de K.A.I.R.O.S.

## Statut

**Prototype opérationnel de compréhension, décision et apprentissage supervisé.**

Ce statut signifie que le projet est installable depuis un clone propre,
démarre, analyse une requête, bloque les actions incomplètes, relie une réponse
à une question, conserve l'expérience après redémarrage et protège la mémoire
confirmée.

Il ne signifie pas que Kairos est une intelligence générale ni qu'il apprend
n'importe quel domaine sans source ni supervision.

## Commandes reproductibles

```bash
python -m pip install -e .
kairos --smoke-test
python -m unittest discover -s tests -v
python benchmark.py
python holdout.py
python decision_benchmark.py
```

## Portes validées

- installation editable depuis un checkout propre ;
- commande `kairos` disponible ;
- smoke test du kernel, des connaissances, de la décision et de la réponse ;
- tests unitaires et tests de bout en bout ;
- persistance `question → réponse → expérience → redémarrage` ;
- aucune promotion automatique d'une expérience ;
- relation créateur conservée comme candidate avant consolidation ;
- consolidation `Réfléchir → Tester → SECAU` avant réutilisation ;
- rapports de test liés à leur propre hypothèse ;
- exceptions de test enregistrées comme échecs ;
- sources Internet limitées à deux domaines HTTPS distincts ;
- benchmarks transformés en barrières avec code de sortie non nul ;
- validation CI sous Python 3.11, 3.12 et 3.13 ;
- zéro fausse exécution exigée par les seuils.

## Boucle d'apprentissage actuellement démontrée

```text
incompréhension
→ question ciblée
→ réponse du créateur
→ expérience non confirmée
→ relation candidate
→ preuves + exemples + contre-exemples
→ Tester
→ SECAU
→ relation confirmée
→ réutilisation
```

## Prochaine porte

La prochaine étape n'est pas d'ajouter des dizaines de skills. Elle consiste à
orchestrer automatiquement les expériences en attente dans un vrai mode
`GrowUp`, tout en conservant les mêmes exigences de preuve, de régression et de
retour arrière.
