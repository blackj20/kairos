"""Preuves de fonctionnement depuis l'entrée jusqu'à la mémoire persistante."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.cli import smoke_test
from kairos.decision import MoteurDecision, StockageJson


def preparer_memoire(dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    for nom in ("pending_questions.json", "experiences.json", "learning_events.json"):
        (dossier / nom).write_text(
            json.dumps({"version": 1, "items": []}) + "\n",
            encoding="utf-8",
        )


def construire_kernel(dossier: Path) -> Kernel:
    comprendre = Comprendre()
    stockage = StockageJson(dossier)
    moteur = MoteurDecision(comprendre, stockage=stockage)
    return Kernel(comprendre=comprendre, moteur_decision=moteur)


class OperationalFlowTests(unittest.TestCase):
    def test_smoke_test_demarre_et_analyse(self) -> None:
        self.assertEqual(smoke_test(), 0)

    def test_question_reponse_experience_survit_au_redemarrage(self) -> None:
        with tempfile.TemporaryDirectory() as temporaire:
            dossier = Path(temporaire) / "memory"
            preparer_memoire(dossier)

            premier = construire_kernel(dossier)
            decision = premier.traiter("installe")
            self.assertEqual(decision.route, "clarification")
            self.assertIsNotNone(decision.question_id)

            experience = premier.repondre_a(decision.question_id, "python")
            self.assertEqual(experience.statut, "recorded_not_confirmed")
            self.assertEqual(experience.resolution["field"], "cible")
            self.assertEqual(experience.resolution["value"], "python")

            redemarre = construire_kernel(dossier)
            experiences = redemarre.moteur_decision.stockage.experiences()
            questions = redemarre.moteur_decision.stockage.questions_en_attente()

            self.assertEqual(len(experiences), 1)
            self.assertEqual(experiences[0].id, experience.id)
            self.assertEqual(experiences[0].statut, "recorded_not_confirmed")
            self.assertEqual(questions, ())
            self.assertFalse((dossier / "confirmed.json").exists())


if __name__ == "__main__":
    unittest.main()
