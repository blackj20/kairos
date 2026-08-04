from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.interne import MoteurInterne, TypeTravail
from kairos.memory import MemoryRepository


class _FakeLabResult:
    def vers_dict(self) -> dict[str, object]:
        return {
            "state": "completed",
            "secau_calls": 1,
            "production_unchanged": True,
        }


class _FakeLab:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def run(self, source_path: Path) -> _FakeLabResult:
        self.calls.append(source_path)
        return _FakeLabResult()


class InternalEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "memory").mkdir(parents=True)
        (self.root / "data" / "cognition").mkdir(parents=True)
        self.repository = MemoryRepository(self.root / "memory" / "cognition.db")
        self.config = {
            "mode": "offline_first",
            "max_candidates": 10,
            "max_seconds": 5,
            "run_lab": True,
            "ask_one_question": True,
            "network": False,
            "production_promotion": False,
        }

    def tearDown(self) -> None:
        self.repository.close()
        self.temp.cleanup()

    def _engine(self, lab: _FakeLab | None = None) -> MoteurInterne:
        chosen = lab or _FakeLab()
        return MoteurInterne(
            self.root,
            repository=self.repository,
            lab_factory=lambda _root: chosen,
            config=self.config,
        )

    def _candidate(self, **payload: object) -> str:
        data = {
            "name": "xylophore",
            "definition": "un instrument musical inconnu",
            "created_from_experience_id": "experience_test",
            "score": 35,
            **payload,
        }
        return self.repository.add_hypothesis(data)

    def test_empty_memory_sleeps_without_inventing_work(self) -> None:
        result = self._engine().run()
        self.assertEqual(result.etat, "sleeping")
        self.assertEqual(result.candidats_vus, 0)
        self.assertEqual(result.taches_executees, 0)
        self.assertFalse(result.reseau_utilise)
        self.assertEqual(result.ratio_hors_ligne, 1.0)
        self.assertTrue(Path(result.report_path).exists())

    def test_selects_one_high_gain_question(self) -> None:
        hypothesis_id = self._candidate()
        result = self._engine().run()
        self.assertEqual(result.etat, "waiting_human")
        self.assertIsNotNone(result.question)
        assert result.question is not None
        self.assertEqual(result.question.hypothesis_id, hypothesis_id)
        self.assertEqual(result.question.champ, "relation")
        self.assertEqual(result.question.gain_attendu, 40)
        self.assertFalse(result.connaissances_production_modifiees)
        candidate = self.repository.hypothesis(hypothesis_id)
        assert candidate is not None
        learning = candidate["payload"]["active_learning"]
        self.assertEqual(learning["pending_field"], "relation")
        self.assertEqual(len(learning["questions"]), 1)

    def test_repeated_cycle_does_not_duplicate_pending_question(self) -> None:
        hypothesis_id = self._candidate()
        engine = self._engine()
        engine.run()
        engine.run()
        candidate = self.repository.hypothesis(hypothesis_id)
        assert candidate is not None
        questions = candidate["payload"]["active_learning"]["questions"]
        self.assertEqual(len(questions), 1)

    def test_reviewable_candidate_launches_real_lab_boundary(self) -> None:
        self._candidate(research_kind="information.search")
        lab = _FakeLab()
        result = self._engine(lab).run()
        self.assertEqual(result.etat, "worked")
        self.assertEqual(len(lab.calls), 1)
        assert result.laboratoire is not None
        self.assertEqual(result.laboratoire["secau_calls"], 1)
        self.assertEqual(result.taches[0].type, TypeTravail.REVUE_LOCALE)
        self.assertIsNone(result.question)

    def test_complete_candidate_without_tester_contract_is_blocked(self) -> None:
        self._candidate(
            relation_candidates=[
                {
                    "source": "xylophore",
                    "relation": "est_un",
                    "target": "instrument",
                }
            ],
            examples=["a", "b", "c"],
            counterexamples=["d", "e"],
            source_leads=["documentation locale"],
        )
        result = self._engine().run()
        self.assertEqual(result.etat, "blocked")
        self.assertEqual(result.taches[0].type, TypeTravail.BLOQUE)
        self.assertIn("aucun contrat Tester", result.taches[0].raison)

    def test_local_concepts_inform_the_question_without_becoming_proof(self) -> None:
        self.repository.connection.execute(
            "INSERT INTO concepts VALUES (?, ?, ?, ?, 90, 'confirmed', 1, ?, NULL)",
            (
                "concept_instrument",
                "instrument",
                "musique",
                "objet musical utilisé pour produire un son",
                json.dumps(["evidence_local"]),
            ),
        )
        self.repository.connection.commit()
        hypothesis_id = self._candidate()
        result = self._engine().run()
        assert result.question is not None
        self.assertIn("instrument", result.question.texte)
        candidate = self.repository.hypothesis(hypothesis_id)
        assert candidate is not None
        context = candidate["payload"]["internal_context"]
        self.assertEqual(context[0]["ref"], "concept:concept_instrument")
        self.assertNotIn("evidence_ids", candidate["payload"])

    def test_configuration_cannot_enable_network_or_autopromotion(self) -> None:
        bad_network = {**self.config, "network": True}
        with self.assertRaises(ValueError):
            MoteurInterne(
                self.root,
                repository=self.repository,
                config=bad_network,
            )
        bad_promotion = {**self.config, "production_promotion": True}
        with self.assertRaises(ValueError):
            MoteurInterne(
                self.root,
                repository=self.repository,
                config=bad_promotion,
            )

    def test_status_and_natural_commands_are_observable(self) -> None:
        engine = self._engine()
        self.assertEqual(engine.status()["etat"], "never_run")
        result = engine.run()
        self.assertEqual(engine.status()["run_id"], result.run_id)
        self.assertEqual(MoteurInterne.parse_command("moteur-interne=on"), "on")
        self.assertEqual(MoteurInterne.parse_command("internal-engine=status"), "status")
        self.assertIsNone(MoteurInterne.parse_command("cherche atome"))


if __name__ == "__main__":
    unittest.main()
