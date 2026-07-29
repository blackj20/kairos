"""Tests V0.9 du dialogue naturel et des index linguistiques."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Kernel
from kairos.apprentissage_naturel import DialogueApprentissage
from kairos.connaissances import Connaissances


class TestNaturalLearning(unittest.TestCase):
    def test_common_vocabulary_has_meaning_and_route(self) -> None:
        connaissances = Connaissances()
        mbote = connaissances.trouver_mot_courant("mbote")
        self.assertIsNotNone(mbote)
        self.assertEqual("communication", mbote["category"])
        self.assertEqual("response.greet", mbote["route"])
        self.assertIn("salutation", mbote["meaning"])

    def test_spelling_clarification_resumes_parent_question(self) -> None:
        dialogue = DialogueApprentissage(Connaissances())
        first = dialogue.demarrer("atome")
        self.assertIn("Question 1/4", first)
        clarification = dialogue.traiter(
            "un atomme est une petite unité de matière"
        )
        self.assertIn("atome", clarification.texte)
        self.assertIn("question principale", clarification.texte)
        resumed = dialogue.traiter("oui")
        self.assertIn("Correction confirmée", resumed.texte)
        self.assertIn("Question 2/4", resumed.texte)

    def test_unknown_word_is_explained_without_losing_answer(self) -> None:
        dialogue = DialogueApprentissage(Connaissances())
        dialogue.demarrer("mbote")
        question = dialogue.traiter(
            "mbote signifie bonkoko dans une salutation"
        )
        self.assertIn("bonkoko", question.texte)
        resumed = dialogue.traiter(
            "bonkoko représente ici une formule amicale"
        )
        self.assertIn("provisoirement", resumed.texte)
        self.assertIn("Question 2/4", resumed.texte)

    def test_clarifications_are_bounded(self) -> None:
        dialogue = DialogueApprentissage(Connaissances())
        dialogue.demarrer("atome")
        dialogue.traiter("un atomme est une petite unité de matière")
        rejected = dialogue.traiter("non")
        self.assertIn("même question", rejected.texte)
        self.assertTrue(dialogue.active)

    def test_session_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as dossier:
            path = Path(dossier) / "learning_sessions.json"
            first = DialogueApprentissage(Connaissances(), path)
            first.demarrer("mbote")
            first.traiter("mbote est une formule de salutation amicale")
            second = DialogueApprentissage(Connaissances(), path)
            self.assertTrue(second.active)
            self.assertIn("situations concrètes", second.attente)

    def test_kernel_keeps_one_question_at_a_time(self) -> None:
        kernel = Kernel()
        first = kernel.traiter("pose-moi des questions sur atome")
        self.assertIn("Question 1/4", first.reponse)
        self.assertNotIn("Question 2/4", first.reponse)
        next_turn = kernel.traiter(
            "un atome est une unité fondamentale de la matière"
        )
        self.assertIn("Question 2/4", next_turn.reponse)
        self.assertNotIn("Question 3/4", next_turn.reponse)

    def test_indexed_lookups_match_expected_entries(self) -> None:
        connaissances = Connaissances()
        self.assertEqual("chercher", connaissances.trouver_verbe("cherche")[0])
        self.assertEqual(("python", "logiciels"), connaissances.trouver_entite("python"))
        self.assertIn("article:definis", connaissances.fonctions_pour("le"))


if __name__ == "__main__":
    unittest.main()
