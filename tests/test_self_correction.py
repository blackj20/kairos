"""Tests V0.13 du laboratoire interne de self-correction."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.memory import MemoryRepository
from kairos.self_correction import SelfCorrectionLab


class TestSelfCorrectionLab(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        config_dir = self.root / "data" / "cognition"
        config_dir.mkdir(parents=True)
        (config_dir / "self_correction.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "mode": "isolated_research_lab",
                    "max_cycles": 5,
                    "max_candidates": 20,
                    "max_seconds": 5,
                    "auto_promote_in_lab": True,
                    "production_commit": False,
                    "permissions": {
                        "network": False,
                        "shell": False,
                        "process": False,
                        "hardware": False,
                        "production_memory_write": False,
                        "laboratory_memory_write": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.source = self.root / "memory" / "cognition.db"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _candidate(
        self,
        *,
        two_domains: bool = True,
        protected: bool = False,
    ) -> str:
        repository = MemoryRepository(self.source)
        urls = [
            "https://science.example/xylophore",
            (
                "https://dictionary.example/xylophore"
                if two_domains
                else "https://science.example/xylophore-2"
            ),
        ]
        claims = [
            "Un xylophore est un organisme associé au bois.",
            "Le xylophore désigne un organisme vivant lié au bois.",
        ]
        evidence = [
            repository.add_evidence("web", url, claim, 75)
            for url, claim in zip(urls, claims)
        ]
        payload = {
            "created_from_experience_id": "self_correction_test",
            "name": "xylophore",
            "domain": "general",
            "definition": claims[0],
            "evidence_ids": evidence,
            "source_urls": urls,
            "source_claims": claims,
            "research_kind": "information.search",
            "score": 70,
        }
        if protected:
            payload["identity"] = "ne jamais modifier"
        hypothesis_id = repository.add_hypothesis(payload)
        repository.close()
        return hypothesis_id

    def test_complete_candidate_is_promoted_only_inside_lab(self) -> None:
        hypothesis_id = self._candidate()
        result = SelfCorrectionLab(self.root).run(self.source)

        self.assertTrue(result.production_unchanged)
        self.assertEqual(1, result.verdicts["promote"])
        self.assertEqual(1, result.secau_calls)
        self.assertEqual(1, result.after_lab["concepts"])

        production = MemoryRepository(self.source)
        self.assertEqual(
            "candidate", production.hypothesis(hypothesis_id)["status"]
        )
        self.assertEqual([], production.search({"text": "xylophore"}))
        production.close()

        laboratory = MemoryRepository(result.laboratory_path)
        self.assertEqual(1, len(laboratory.search({"text": "xylophore"})))
        laboratory.close()

    def test_incomplete_candidate_reveals_missing_evidence(self) -> None:
        self._candidate(two_domains=False)
        result = SelfCorrectionLab(self.root).run(self.source)
        self.assertEqual(1, result.verdicts["needs_more_evidence"])
        self.assertEqual(0, result.after_lab["concepts"])
        self.assertTrue(result.production_unchanged)

    def test_protected_payload_is_quarantined_in_lab(self) -> None:
        self._candidate(protected=True)
        result = SelfCorrectionLab(self.root).run(self.source)
        self.assertEqual(1, result.verdicts["quarantine"])
        self.assertEqual(0, result.after_lab["concepts"])

    def test_candidate_without_test_contract_is_reported_not_invented(self) -> None:
        repository = MemoryRepository(self.source)
        hypothesis_id = repository.add_hypothesis(
            {
                "created_from_experience_id": "unknown_contract",
                "name": "inconnu",
                "definition": "information non testable automatiquement",
                "evidence_ids": [],
                "score": 20,
            }
        )
        repository.close()
        result = SelfCorrectionLab(self.root).run(self.source)
        self.assertEqual(0, result.secau_calls)
        self.assertEqual(hypothesis_id, result.skipped[0]["hypothesis"])

    def test_status_reuses_last_observable_report(self) -> None:
        lab = SelfCorrectionLab(self.root)
        self.assertEqual("never_run", lab.status()["state"])
        result = lab.run(self.source)
        status = lab.status()
        self.assertEqual(result.run_id, status["run_id"])
        self.assertFalse(status["background_process"])

    def test_exact_conversation_commands_are_recognized(self) -> None:
        self.assertEqual(
            "on", SelfCorrectionLab.parse_command("self-correction = on")
        )
        self.assertEqual(
            "status",
            SelfCorrectionLab.parse_command("SELF-CORRECTION=STATUT"),
        )
        self.assertIsNone(
            SelfCorrectionLab.parse_command("active la correction peut-être")
        )

    def test_configuration_can_never_write_production_memory(self) -> None:
        path = self.root / "data" / "cognition" / "self_correction.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["production_commit"] = True
        path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(ValueError):
            SelfCorrectionLab(self.root)


if __name__ == "__main__":
    unittest.main()
