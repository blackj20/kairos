"""Régressions ciblées sur l'intégrité de l'apprentissage."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.cognition import Secau, SecauVerdict, Tester
from kairos.knowledge_base import KnowledgeBase
from kairos.memory import MemoryRepository


class KnowledgeBaseIntegrityTests(unittest.TestCase):
    def test_alias_is_not_matched_inside_an_unrelated_word(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.json"
            path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "science.atom",
                                "aliases": ["atome"],
                                "answer": "définition",
                                "sources": ["source"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            knowledge = KnowledgeBase(path)

            self.assertIsNone(knowledge.find("étudier l'anatomie"))
            self.assertEqual(
                knowledge.find("définis un atome")["id"],
                "science.atom",
            )


class TesterIntegrityTests(unittest.TestCase):
    def test_exception_becomes_a_failed_and_traceable_case(self) -> None:
        repository = MemoryRepository()
        tester = Tester(repository)

        def broken_case() -> bool:
            raise RuntimeError("boom")

        _, report = tester.test(
            "hypothesis_test",
            original=broken_case,
            paraphrases=(lambda: True, lambda: True, lambda: True),
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["original"])
        self.assertIn("RuntimeError: boom", report["errors"]["original"])
        repository.close()


class SecauIntegrityTests(unittest.TestCase):
    def test_report_for_another_hypothesis_is_rejected(self) -> None:
        repository = MemoryRepository()
        evidence_id = repository.add_evidence(
            "creator",
            "lesson://integrity",
            "Une preuve contrôlée.",
            90,
        )
        first = repository.add_hypothesis(
            {
                "created_from_experience_id": "experience_1",
                "name": "première hypothèse",
                "definition": "première définition",
                "evidence_ids": [evidence_id],
                "score": 60,
            }
        )
        second_payload = {
            "created_from_experience_id": "experience_2",
            "name": "seconde hypothèse",
            "definition": "seconde définition",
            "evidence_ids": [evidence_id],
            "score": 60,
        }
        second = repository.add_hypothesis(second_payload)
        report_id = repository.save_report(first, {"passed": True})

        result = Secau(repository).review(second, report_id, second_payload)

        self.assertEqual(result.verdict, SecauVerdict.REJECT)
        self.assertIn("ne correspond pas", result.reason)
        repository.close()


if __name__ == "__main__":
    unittest.main()
