"""Tests de la chaîne interaction → expérience → hypothèse."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kairos import Kernel
from kairos.apprentissage_naturel import ResultatDialogue
from kairos.hypotheses import GestionnaireHypotheses
from kairos.memory import MemoryRepository


class HypothesisInteractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = MemoryRepository(":memory:")
        self.kernel = Kernel(cognitive_repository=self.repository)

    def tearDown(self) -> None:
        self.repository.close()

    def _teach_deploy(self, *, actor: str = "creator"):
        decision = self.kernel.traiter("deploie python")
        self.assertIsNotNone(decision.question_id)
        return self.kernel.repondre_a(
            str(decision.question_id),
            "installer",
            acteur=actor,
        )

    def test_creator_explanation_creates_real_candidate(self) -> None:
        experience = self._teach_deploy()
        info = experience.resolution["hypothesis"]
        hypothesis = self.repository.hypothesis(info["id"])
        self.assertTrue(info["creee"])
        self.assertEqual("candidate", info["statut"])
        self.assertEqual("deploie", info["nom"])
        self.assertEqual(
            "interaction.semantic_relation",
            hypothesis["payload"]["learning_kind"],
        )
        self.assertEqual(experience.id, hypothesis["created_from_experience_id"])
        self.assertEqual(
            ["sources", "tests", "validation_secau"],
            hypothesis["payload"]["missing"],
        )

    def test_candidate_is_not_promoted_or_reusable(self) -> None:
        experience = self._teach_deploy()
        hypothesis = self.repository.hypothesis(
            experience.resolution["hypothesis"]["id"]
        )
        self.assertEqual("candidate", hypothesis["status"])
        self.assertEqual([], self.repository.search({"text": "deploie"}))
        self.assertIsNone(
            self.kernel.comprendre.connaissances.relations_verbes.obtenir(
                "deploie"
            )
        )

    def test_operational_target_answer_does_not_create_hypothesis(self) -> None:
        decision = self.kernel.traiter("installe")
        experience = self.kernel.repondre_a(
            str(decision.question_id), "python"
        )
        self.assertNotIn("hypothesis", experience.resolution)
        self.assertEqual([], self.repository.candidate_hypotheses())

    def test_non_creator_cannot_teach_hypothesis(self) -> None:
        experience = self._teach_deploy(actor="guest")
        self.assertNotIn("hypothesis", experience.resolution)
        self.assertEqual([], self.repository.candidate_hypotheses())

    def test_repeated_explanation_reuses_candidate(self) -> None:
        first = self._teach_deploy().resolution["hypothesis"]
        second = self._teach_deploy().resolution["hypothesis"]
        self.assertEqual(first["id"], second["id"])
        self.assertFalse(second["creee"])
        self.assertEqual(1, len(self.repository.candidate_hypotheses()))
        self.assertTrue(
            any(
                event["event"] == "HYPOTHESIS_REUSED_FROM_INTERACTION"
                for event in self.repository.audit_events()
            )
        )

    def test_structured_dialogue_creates_hypothesis_and_exposes_it(self) -> None:
        candidate = {
            "session_id": "session_test",
            "topic": "atome",
            "answers": {
                "definition": "un atome est une unité de matière",
                "examples": "hydrogène, carbone, oxygène",
                "counterexamples": "une maison entière n'est pas un atome",
                "relations": "atome est relié à matière et énergie",
            },
            "glossary": {},
            "route_candidates": ["information.search"],
            "relation_candidates": [],
            "status": "candidate",
            "reusable": False,
        }
        self.kernel.apprentissage.session = {
            "id": "active_test",
            "status": "active",
            "topic": "atome",
            "index": 3,
            "answers": {},
            "glossary": {},
            "pending": None,
        }
        result = ResultatDialogue(
            "Séance terminée.",
            termine=True,
            candidate=candidate,
        )
        with patch.object(
            self.kernel.apprentissage,
            "traiter",
            return_value=result,
        ):
            decision = self.kernel.traiter("réponse finale")
        self.assertIsNotNone(decision.apprentissage)
        self.assertIn("Hypothèse créée", decision.reponse)
        hypothesis = self.repository.hypothesis(
            decision.apprentissage["id"]
        )
        self.assertEqual(
            "dialogue.structured_explanation",
            hypothesis["payload"]["learning_kind"],
        )
        self.assertEqual("candidate", hypothesis["status"])

    def test_status_explains_what_is_missing(self) -> None:
        info = self._teach_deploy().resolution["hypothesis"]
        status = GestionnaireHypotheses(self.repository).statut(info["id"])
        self.assertEqual(info["id"], status["hypothesis"]["id"])
        self.assertEqual(
            ["sources", "tests", "validation_secau"],
            status["missing"],
        )

    def test_hypothesis_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cognition.db"
            first_repo = MemoryRepository(path)
            first_kernel = Kernel(cognitive_repository=first_repo)
            decision = first_kernel.traiter("deploie python")
            experience = first_kernel.repondre_a(
                str(decision.question_id), "installer"
            )
            hypothesis_id = experience.resolution["hypothesis"]["id"]
            first_repo.close()

            second_repo = MemoryRepository(path)
            status = GestionnaireHypotheses(second_repo).statut(
                hypothesis_id
            )
            self.assertEqual(hypothesis_id, status["hypothesis"]["id"])
            self.assertEqual("candidate", status["hypothesis"]["status"])
            second_repo.close()


if __name__ == "__main__":
    unittest.main()
