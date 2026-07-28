# Décision de fondation

## Statut

**Conservée comme fondation centrale le 28 juillet 2026.**

## Invariants

1. Le kernel orchestre et ne comprend pas.
2. `Comprendre` suit obligatoirement :
   `Découper → Sens → Contexte → Estimation → Vérifier`.
3. Le kernel suit le verdict de `Vérifier` sans recalculer les scores.
4. `Comprendre` possède un accès en lecture seule aux connaissances.
5. Une requête contenant plusieurs actions est clarifiée avant exécution.
6. Une information apprise devient d'abord une hypothèse.
7. Une modification doit être traçable, testée et réversible.
8. L'identité, l'objectif principal et la relation avec le créateur sont
   protégés contre les modifications automatiques.
9. Une capacité n'est déclarée acquise qu'avec une preuve reproductible.
10. Zéro fausse exécution reste une condition de progression.
11. `VerifierAnalyse` valide la langue ; `VerifierDecision` autorise la route.
12. Seuls `Demande` et `Expérience` écrivent dans la mémoire V0.3 autorisée.
13. Une expérience reste non confirmée jusqu'à la future phase `Réfléchir`.

## Ce que la validation signifie

La validation confirme l'architecture et son contrat interne. Elle ne signifie
pas que Kairos comprend tout le français ni qu'il possède une intelligence
générale.

## Ce qui ne doit pas être ajouté maintenant

- des compétences nombreuses sans compréhension fiable ;
- une écriture directe dans la mémoire confirmée ;
- des règles non testées ajoutées pour gonfler artificiellement les scores ;
- une réponse générée directement dans le kernel ;
- une dépendance entre les fichiers `self` et une phrase utilisateur ordinaire.

## Prochaine porte

Avant d'activer l'apprentissage autonome :

- corpus d'au moins 600 phrases ;
- mesures par type de requête ;
- journal des erreurs ;
- tests de non-régression ;
- protocole `question → hypothèse → vérification → promotion ou rejet`.
