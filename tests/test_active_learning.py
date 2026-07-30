"""Tests V0.17 du moteur de questions utiles et de liens candidats."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import ApprentissageActif, Kernel
from kairos.memory import MemoryRepository


class ActiveLearningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = MemoryRepository(":memory:")
        self.engine = ApprentissageActif(self.repository)

    def tearDown(self) -> None:
        self.repository.close()

    def _candidate(self, name: str = "xylophore") -> str:
        return self.repository.add_hypothesis(
            {
                "created_from_experience_id": f"experience_{name}",
                "name": name,
                "definition": f"explication provisoire de {name}",
                "domain": "language",
                "score": 40,
                "learning_kind": "interaction.user_explanation",
                "evidence_ids": [],
                "examples": [],
                "counterexamples": [],
                "missing": ["relation", "sources", "tests", "validation_secau"],
                "next_action": "ask_best_question",
            }
        )

    def test_starts_with_highest_gain_missing_field(self) -> None:
        hypothesis_id = self._candidate()
        result = self.engine.demarrer()
        self.assertEqual(hypothesis_id, result.hypothesis_id)
        self.assertEqual("relation", result.question.champ)
        self.assertEqual(40, result.question.gain_attendu)
        self.assertTrue(self.engine.active)

    def test_natural_definition_creates_internal_candidate_link(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        result = self.engine.recevoir("c'est un instrument musical")
        hypothesis = self.repository.hypothesis(hypothesis_id)
        links = hypothesis["payload"]["relation_candidates"]
        self.assertEqual("est_un", links[0]["relation"])
        self.assertEqual("instrument musical", links[0]["target"])
        self.assertEqual(1, len(result.liens_crees))
        self.assertEqual("candidate", hypothesis["status"])

    def test_relation_clarification_is_bounded(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        retry = self.engine.recevoir("ça dépend de beaucoup de choses")
        self.assertEqual(2, retry.question.tentative)
        advanced = self.engine.recevoir("je ne peux pas mieux expliquer")
        self.assertEqual("examples", advanced.question.champ)
        hypothesis = self.repository.hypothesis(hypothesis_id)
        session = hypothesis["payload"]["active_learning"]
        self.assertIn("relation", session["skipped_fields"])

    def test_examples_are_deduplicated_with_fuzzy_matching(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        self.engine.recevoir("c'est un instrument")
        self.engine.recevoir("un xylophone, Un xylophone")
        hypothesis = self.repository.hypothesis(hypothesis_id)
        self.assertEqual(1, len(hypothesis["payload"]["examples"]))
        self.assertEqual("examples", hypothesis["payload"]["active_learning"]["pending_field"])

    def test_complete_structure_remains_candidate(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        self.engine.recevoir("c'est un instrument musical")
        self.engine.recevoir("xylophone, marimba, balafon")
        self.engine.recevoir("piano, guitare")
        final = self.engine.recevoir("cherche toi-même")
        hypothesis = self.repository.hypothesis(hypothesis_id)
        self.assertEqual("ready_for_research", final.statut)
        self.assertEqual("candidate", hypothesis["status"])
        self.assertEqual("self_research", hypothesis["payload"]["source_strategy"])
        self.assertEqual("research_and_test", hypothesis["payload"]["next_action"])
        self.assertIn("sources", hypothesis["payload"]["missing"])
        self.assertEqual([], self.repository.search({"text": "xylophore"}))

    def test_pause_and_natural_resume(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        paused = self.engine.recevoir("pause")
        self.assertEqual("paused", paused.statut)
        self.assertFalse(self.engine.active)
        resumed = self.engine.demarrer("xylophorre")
        self.assertEqual(hypothesis_id, resumed.hypothesis_id)
        self.assertTrue(self.engine.active)

    def test_unknown_candidate_is_not_invented(self) -> None:
        self._candidate()
        result = self.engine.demarrer("absolument-introuvable")
        self.assertEqual("nothing_to_learn", result.statut)
        self.assertFalse(self.engine.active)

    def test_kernel_starts_from_natural_consolidate_command(self) -> None:
        kernel = Kernel(cognitive_repository=self.repository)
        decision = kernel.traiter("deploie python")
        experience = kernel.repondre_a(str(decision.question_id), "installer")
        hypothesis_id = experience.resolution["hypothesis"]["id"]
        start = kernel.traiter("consolide")
        self.assertEqual(hypothesis_id, start.apprentissage["hypothesis_id"])
        self.assertEqual("examples", start.apprentissage["question"]["champ"])
        followup = kernel.traiter(
            "déployer une API, déployer un site, déployer un service"
        )
        self.assertIn("ne doit pas", followup.reponse.casefold())
        self.assertEqual("clarification", followup.route)

    def test_unknown_definition_question_opens_teachable_gap(self) -> None:
        kernel = Kernel(cognitive_repository=self.repository)
        decision = kernel.traiter("c'est quoi un xylophore ?")
        self.assertIsNotNone(decision.question_id)
        self.assertIn("Explique-le naturellement", decision.reponse)
        experience = kernel.repondre_a(
            str(decision.question_id),
            "un xylophore est un instrument musical",
        )
        hypothesis = experience.resolution["hypothesis"]
        self.assertEqual("xylophore", hypothesis["nom"])
        self.assertEqual("candidate", hypothesis["statut"])

    def test_full_subject_definition_is_extracted_as_relation(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        result = self.engine.recevoir(
            "xylophore est un instrument de musique",
        )
        self.assertEqual("est_un", result.liens_crees[0]["relation"])
        self.assertEqual(
            "instrument de musique",
            result.liens_crees[0]["target"],
        )

    def test_user_explanation_never_promotes_knowledge(self) -> None:
        hypothesis_id = self._candidate()
        self.engine.demarrer(hypothesis_id)
        self.engine.recevoir("c'est une salutation")
        hypothesis = self.repository.hypothesis(hypothesis_id)
        self.assertEqual("candidate", hypothesis["status"])
        self.assertFalse(
            any(
                event["event"] == "KNOWLEDGE_PROMOTED"
                for event in self.repository.audit_events()
            )
        )

    def test_active_session_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cognition.db"
            first = MemoryRepository(path)
            first_engine = ApprentissageActif(first)
            hypothesis_id = first.add_hypothesis(
                {
                    "created_from_experience_id": "experience_restart",
                    "name": "mbote",
                    "definition": "mbote est une salutation",
                    "score": 40,
                    "evidence_ids": [],
                    "examples": [],
                    "counterexamples": [],
                }
            )
            first_engine.demarrer(hypothesis_id)
            first.close()

            second = MemoryRepository(path)
            second_engine = ApprentissageActif(second)
            self.assertFalse(second_engine.active)
            self.assertEqual(1, second_engine.statut()["resumable"])
            resumed = second_engine.demarrer("mbote")
            self.assertEqual(hypothesis_id, resumed.hypothesis_id)
            self.assertTrue(second_engine.active)
            self.assertIn("examples", second_engine.attente)
            second.close()

    def test_origin_cannot_be_rewritten(self) -> None:
        hypothesis_id = self._candidate()
        hypothesis = self.repository.hypothesis(hypothesis_id)
        payload = dict(hypothesis["payload"])
        payload["created_from_experience_id"] = "experience_forged"
        with self.assertRaises(ValueError):
            self.repository.update_hypothesis_payload(hypothesis_id, payload)


if __name__ == "__main__":
    unittest.main()
