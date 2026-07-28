"""Tests de liaison question → réponse → expérience."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.decision import MoteurDecision, StockageJson


class TestExperience(unittest.TestCase):
    def test_reponse_est_liee_a_sa_question(self) -> None:
        kernel = Kernel()
        decision = kernel.traiter("installe")
        experience = kernel.repondre_a(decision.question_id, "python")

        self.assertEqual(decision.question_id, experience.question_id)
        self.assertEqual("cible", experience.champ)
        self.assertEqual("python", experience.resolution["value"])
        self.assertEqual(100, experience.resolution["score"])
        self.assertEqual("recorded_not_confirmed", experience.statut)
        self.assertEqual(
            (),
            kernel.moteur_decision.stockage.questions_en_attente(),
        )
        self.assertEqual(
            1,
            len(kernel.moteur_decision.stockage.experiences()),
        )

    def test_meme_question_ne_peut_pas_recevoir_deux_reponses(self) -> None:
        kernel = Kernel()
        decision = kernel.traiter("installe")
        kernel.repondre_a(decision.question_id, "python")
        with self.assertRaises(ValueError):
            kernel.repondre_a(decision.question_id, "docker")

    def test_reponse_vide_est_refusee(self) -> None:
        kernel = Kernel()
        decision = kernel.traiter("installe")
        with self.assertRaises(ValueError):
            kernel.repondre_a(decision.question_id, "   ")

    def test_stockage_persistant_ne_touche_pas_memoires_protegees(self) -> None:
        with tempfile.TemporaryDirectory() as temporaire:
            dossier = Path(temporaire)
            fichiers_decision = (
                "pending_questions.json",
                "experiences.json",
                "learning_events.json",
            )
            fichiers_proteges = (
                "confirmed.json",
                "hypotheses.json",
                "history.json",
            )
            for nom in fichiers_decision + fichiers_proteges:
                (dossier / nom).write_text(
                    '{\n  "version": 1,\n  "items": []\n}\n',
                    encoding="utf-8",
                )

            avant = {
                nom: (dossier / nom).read_bytes()
                for nom in fichiers_proteges
            }
            comprendre = Comprendre()
            stockage = StockageJson(dossier)
            moteur = MoteurDecision(
                comprendre=comprendre,
                stockage=stockage,
            )
            kernel = Kernel(
                comprendre=comprendre,
                moteur_decision=moteur,
            )

            decision = kernel.traiter("cela blorpe")
            kernel.repondre_a(
                decision.question_id,
                "blorpe décrit un état positif",
            )

            apres = {
                nom: (dossier / nom).read_bytes()
                for nom in fichiers_proteges
            }
            self.assertEqual(avant, apres)
            for nom in fichiers_decision:
                donnees = json.loads(
                    (dossier / nom).read_text(encoding="utf-8")
                )
                self.assertIsInstance(donnees["items"], list)


if __name__ == "__main__":
    unittest.main()
