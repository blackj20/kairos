"""Tests V0.12 de généralisation des intentions françaises."""

from __future__ import annotations

import unittest

from kairos import Kernel
from kairos.generalisation_intention import GeneralisateurIntention


class TestGeneralisateurIntention(unittest.TestCase):
    def setUp(self) -> None:
        self.generalisateur = GeneralisateurIntention()

    def test_modal_person_and_action_are_composed(self) -> None:
        lecture = self.generalisateur.analyser(
            "tu pourrais gentiment ouvrir le dossier",
            action="ouvrir",
            type_requete="question",
        )
        self.assertTrue(lecture.indirecte)
        self.assertEqual("demande_indirecte", lecture.nature)
        self.assertGreaterEqual(lecture.score, 90)

    def test_impersonal_polite_request_is_directive(self) -> None:
        decision = Kernel().traiter(
            "serait-il possible de chercher atome ?"
        )
        self.assertEqual(
            "demande_indirecte",
            decision.analyse.cognition["intention"],
        )
        self.assertEqual("competence", decision.route)

    def test_capability_question_never_executes(self) -> None:
        decision = Kernel().traiter("sais-tu installer docker ?")
        self.assertNotEqual(
            "demande_indirecte",
            decision.analyse.cognition["intention"],
        )
        self.assertEqual("repondre", decision.route)

    def test_dangerous_capability_question_never_executes(self) -> None:
        decision = Kernel().traiter(
            "es-tu capable de supprimer le fichier ?"
        )
        self.assertEqual("repondre", decision.route)
        self.assertNotEqual("competence", decision.route)

    def test_how_to_question_is_informational(self) -> None:
        decision = Kernel().traiter("comment supprimer le fichier ?")
        self.assertEqual("obtenir_information", decision.analyse.cognition["intention"])
        self.assertEqual("repondre", decision.route)

    def test_personal_learning_desire_is_not_an_order(self) -> None:
        decision = Kernel().traiter("je voudrais apprendre python")
        self.assertNotEqual(
            "demande_indirecte",
            decision.analyse.cognition["intention"],
        )
        self.assertNotEqual("competence", decision.route)

    def test_indirect_irreversible_action_requires_confirmation(self) -> None:
        decision = Kernel().traiter(
            "aurais-tu la possibilité de supprimer le fichier ?"
        )
        self.assertEqual(
            "demande_indirecte",
            decision.analyse.cognition["intention"],
        )
        self.assertEqual("confirmer", decision.route)

    def test_confirmation_does_not_bypass_role_permission(self) -> None:
        decision = Kernel().traiter(
            "pourrais-tu supprimer le fichier ?",
            acteur="user",
        )
        self.assertEqual("refuser", decision.route)

    def test_prohibition_stays_protection(self) -> None:
        decision = Kernel().traiter(
            "est-ce que tu peux ne jamais supprimer le fichier ?"
        )
        self.assertEqual("protection", decision.analyse.cognition["intention"])
        self.assertEqual("controle", decision.route)

    def test_expression_matching_respects_word_boundaries(self) -> None:
        lecture = self.generalisateur.analyser(
            "impeux tu ouvrir dossier",
            action="ouvrir",
            type_requete="question",
        )
        self.assertFalse(lecture.indirecte)

    def test_signals_are_explainable(self) -> None:
        decision = Kernel().traiter(
            "j'aimerais que tu vérifies le fichier"
        )
        raisons = decision.analyse.cognition["raisons"]
        self.assertTrue(any("ouverture directive" in raison for raison in raisons))

    def test_configuration_words_do_not_create_false_unknowns(self) -> None:
        decision = Kernel().traiter(
            "aurais-tu la possibilité de chercher atome ?"
        )
        inconnus = set(decision.analyse.jetons_inconnus)
        self.assertNotIn("possibilité", inconnus)
        self.assertEqual("competence", decision.route)


if __name__ == "__main__":
    unittest.main()
