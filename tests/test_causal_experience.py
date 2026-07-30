"""Tests de la boucle causale et de sa porte Tester → SECAU."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos import Kernel
from kairos.causal import MoteurCausal, StatutEpisode, StockageCausal, TesterCausal
from kairos.cognition import Secau, SecauVerdict
from kairos.memory import MemoryRepository
from kairos.self_correction import SelfCorrectionLab


class CausalEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = StockageCausal(self.root / "causal.db")
        self.kernel = Kernel()
        self.engine = MoteurCausal(kernel=self.kernel, stockage=self.store)

    def tearDown(self) -> None:
        self.kernel.close()
        self.store.close()
        self.temp.cleanup()

    def test_known_search_reaches_observable_goal(self) -> None:
        episode = self.engine.executer_message("cherche atome")
        self.assertEqual("evaluated", episode["status"])
        self.assertTrue(episode["evaluation"]["succes_technique"])
        self.assertTrue(episode["evaluation"]["objectif_atteint"])
        self.assertEqual(100, episode["evaluation"]["score_resultat"])
        self.assertEqual(
            ["created", "predicted", "executed", "observed", "evaluated"],
            [item["next_status"] for item in episode["transitions"]],
        )

    def test_unknown_information_is_not_confused_with_technical_success(self) -> None:
        episode = self.engine.executer("chercher", "xylophore")
        self.assertTrue(episode["evaluation"]["succes_technique"])
        self.assertFalse(episode["evaluation"]["objectif_atteint"])
        self.assertIn(
            "information_not_found", episode["evaluation"]["erreurs"]
        )

    def test_blocked_plan_is_never_executed(self) -> None:
        episode = self.engine.executer("chercher", None)
        self.assertFalse(episode["observation"]["execution_tentee"])
        self.assertIn("route_not_executed", episode["evaluation"]["erreurs"])

    def test_observer_records_facts_without_semantic_judgement(self) -> None:
        episode = self.engine.executer("chercher", "atome")
        observation = episode["observation"]
        self.assertNotIn("objectif_atteint", observation)
        self.assertNotIn("comprehension_validee", observation)
        self.assertIn("sortie", observation)

    def test_output_contract_violation_is_detected(self) -> None:
        self.kernel.routeur.registre._handlers["response.explain"] = (
            lambda contexte: {"response": 42}
        )
        episode = self.engine.executer("chercher", "atome")
        self.assertTrue(episode["evaluation"]["succes_technique"])
        self.assertFalse(episode["evaluation"]["objectif_atteint"])
        self.assertIn(
            "output_contract_violation", episode["evaluation"]["erreurs"]
        )

    def test_replay_is_linked_and_detects_no_regression(self) -> None:
        original = self.engine.executer("chercher", "atome")
        replay = self.engine.rejouer(str(original["id"]))
        comparison = replay["comparison"]
        self.assertEqual(original["id"], comparison["source_episode_id"])
        self.assertTrue(comparison["meme_resultat"])
        self.assertFalse(comparison["regression"])
        self.assertEqual(
            original["id"], replay["episode"]["replay_of"]
        )

    def test_storage_refuses_skipped_transition(self) -> None:
        episode_id = self.store.creer("cherche atome", "chercher", "atome", "information.search")
        with self.assertRaises(ValueError):
            self.store.transition(
                episode_id, StatutEpisode.OBSERVED, {"forbidden": True}
            )


class CausalSecauTests(unittest.TestCase):
    @staticmethod
    def _samples(total: int, *, improved: bool = True) -> list[dict[str, object]]:
        return [
            {
                "episode_id": f"episode_{index}",
                "observed": True,
                "unseen": True,
                "baseline_success": False,
                "candidate_success": improved,
            }
            for index in range(total)
        ]

    def test_tester_then_secau_validate_improvement_without_concept(self) -> None:
        repository = MemoryRepository(":memory:")
        hypothesis_id = repository.add_hypothesis(
            {
                "created_from_experience_id": "causal_batch_1",
                "causal_kind": "behavior.change",
                "name": "renseigner_vers_chercher",
                "samples": self._samples(5),
                "score": 90,
            }
        )
        report_id, report = TesterCausal(repository).tester(hypothesis_id)
        result = Secau(repository).review_causal(hypothesis_id, report_id)
        self.assertTrue(report.passed)
        self.assertEqual(SecauVerdict.PROMOTE, result.verdict)
        self.assertEqual("validated", repository.hypothesis(hypothesis_id)["status"])
        self.assertEqual([], repository.search({"text": "renseigner"}))
        repository.close()

    def test_insufficient_causal_sample_needs_more_evidence(self) -> None:
        repository = MemoryRepository(":memory:")
        hypothesis_id = repository.add_hypothesis(
            {
                "created_from_experience_id": "causal_batch_2",
                "causal_kind": "behavior.change",
                "name": "renseigner_vers_chercher",
                "samples": self._samples(2),
                "score": 60,
            }
        )
        report_id, _ = TesterCausal(repository).tester(hypothesis_id)
        result = Secau(repository).review_causal(hypothesis_id, report_id)
        self.assertEqual(SecauVerdict.NEEDS_MORE_EVIDENCE, result.verdict)
        self.assertEqual("candidate", repository.hypothesis(hypothesis_id)["status"])
        repository.close()

    def test_self_correction_validates_only_the_laboratory_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_dir = root / "data" / "cognition"
            config_dir.mkdir(parents=True)
            (config_dir / "self_correction.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mode": "isolated_research_lab",
                        "max_cycles": 3,
                        "max_candidates": 10,
                        "max_seconds": 5,
                        "auto_promote_in_lab": True,
                        "production_commit": False,
                        "permissions": {"production_memory_write": False},
                    }
                ),
                encoding="utf-8",
            )
            production_path = root / "memory" / "cognition.db"
            production_path.parent.mkdir(parents=True, exist_ok=True)
            repository = MemoryRepository(production_path)
            hypothesis_id = repository.add_hypothesis(
                {
                    "created_from_experience_id": "causal_batch_3",
                    "causal_kind": "behavior.change",
                    "name": "renseigner_vers_chercher",
                    "samples": self._samples(5),
                    "score": 90,
                }
            )
            repository.close()
            result = SelfCorrectionLab(root).run(production_path)
            production = MemoryRepository(production_path)
            laboratory = MemoryRepository(Path(result.laboratory_path))
            self.assertTrue(result.production_unchanged)
            self.assertEqual(1, result.secau_calls)
            self.assertEqual("candidate", production.hypothesis(hypothesis_id)["status"])
            self.assertEqual("validated", laboratory.hypothesis(hypothesis_id)["status"])
            production.close()
            laboratory.close()


if __name__ == "__main__":
    unittest.main()
