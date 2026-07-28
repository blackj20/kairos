"""Tests de la couche Évaluer → ChoisirRoute → VerifierDecision."""

from __future__ import annotations

import unittest

from kairos import Comprendre, Kernel
from kairos.decision import (
    ChoisirRoute,
    Evaluer,
    Route,
    StockageMemoire,
)


class TestDecision(unittest.TestCase):
    def test_commande_complete_reste_executable(self) -> None:
        decision = Kernel().traiter("install python")
        self.assertEqual("competence", decision.route)
        self.assertIsNone(decision.question_id)
        self.assertGreaterEqual(decision.evaluation["score_global"], 85)

    def test_ordre_sans_cible_est_bloque(self) -> None:
        decision = Kernel().traiter("installe")
        self.assertEqual("clarification", decision.route)
        self.assertEqual(
            ("cible",),
            decision.evaluation["champs_manquants"],
        )
        self.assertIn("cible", decision.question.casefold())

    def test_tous_les_ordres_incomplets_sont_bloques(self) -> None:
        for requete in (
            "installe",
            "ouvre",
            "ferme",
            "lance",
            "marche",
            "supprime",
        ):
            with self.subTest(requete=requete):
                decision = Kernel().traiter(requete)
                self.assertNotEqual("competence", decision.route)

    def test_cible_inconnue_demande_confirmation(self) -> None:
        decision = Kernel().traiter("install flarble")
        self.assertEqual("confirmer", decision.route)
        self.assertIsNotNone(decision.question_id)
        self.assertIn("bien compris", decision.question)

    def test_plusieurs_actions_sont_bloquees(self) -> None:
        decision = Kernel().traiter("ouvre python et ferme vscode")
        self.assertEqual("clarification", decision.route)
        self.assertEqual(
            ("plusieurs_actions",),
            decision.evaluation["contradictions"],
        )
        self.assertIn("plusieurs possibilités", decision.question)

    def test_score_tres_faible_devient_etude_interne(self) -> None:
        kernel = Kernel()
        decision = kernel.traiter("cela blorpe")
        self.assertEqual("clarification", decision.route)
        self.assertEqual("etudier", decision.verdict["route"])
        evenements = kernel.moteur_decision.stockage.apprentissages()
        self.assertEqual(1, len(evenements))
        self.assertEqual("blorpe", evenements[0].focus)
        self.assertEqual("high", evenements[0].priorite)

    def test_evenements_faibles_similaires_sont_regroupes(self) -> None:
        kernel = Kernel()
        kernel.traiter("cela blorpe")
        kernel.traiter("ça blorpe")
        evenements = kernel.moteur_decision.stockage.apprentissages()
        self.assertEqual(1, len(evenements))
        self.assertEqual(2, evenements[0].occurrences)

    def test_role_non_autorise_ne_peut_pas_executer(self) -> None:
        decision = Kernel().traiter("install python", acteur="user")
        self.assertEqual("refuser", decision.route)
        self.assertFalse(decision.verdict["valide"])

    def test_evaluer_et_choisir_route_n_ecrivent_rien(self) -> None:
        comprendre = Comprendre()
        stockage = StockageMemoire()
        analyse = comprendre.analyser("installe")
        evaluation = Evaluer().analyser(analyse)
        route = ChoisirRoute().choisir(evaluation)

        self.assertEqual(Route.CLARIFIER, route.route)
        self.assertEqual((), stockage.questions_en_attente())
        self.assertEqual((), stockage.experiences())
        self.assertEqual((), stockage.apprentissages())

    def test_questions_ciblent_le_bon_element(self) -> None:
        cas = (
            ("installe", "cible"),
            ("ouvre", "cible"),
            ("ferme", "cible"),
            ("lance", "cible"),
            ("supprime", "cible"),
            ("truc bizarre", "sens"),
            ("blork", "sens"),
            ("cv", "type_requete"),
            ("python docker", "type_requete"),
            ("", "type_requete"),
            ("ouvre python et ferme vscode", "contradiction"),
        )
        correctes = 0
        for texte, champ in cas:
            kernel = Kernel()
            decision = kernel.traiter(texte)
            question = kernel.moteur_decision.stockage.obtenir_question(
                decision.question_id
            )
            if question and question.champ_manquant == champ:
                correctes += 1

        precision = 100 * correctes / len(cas)
        self.assertGreaterEqual(precision, 90)
        self.assertEqual(100, precision)


if __name__ == "__main__":
    unittest.main()
