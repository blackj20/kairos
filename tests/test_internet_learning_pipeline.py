"""Tests du cycle Internet complet jusqu'au suivi en production."""

from __future__ import annotations

import unittest

from kairos.cognition import SecauVerdict
from kairos.learning import InternetAcquire, InternetLearningPipeline
from kairos.memory import MemoryRepository
from kairos.relations_verbes import MemoireRelationsVerbes


SOURCE_A = """\
deploie signifie installer.
Exemple : deploie python
Exemple : deploie docker
Contre-exemple : deploie une carte sur la table
"""

SOURCE_B = """\
deploie est synonyme de installer.
Exemple : deploie vscode
Exemple : deploie node
Contre-exemple : deploie les ailes
"""


class FakeFetcher:
    """Retourne des documents déterministes sans accès réseau pendant les tests."""

    def __init__(self, documents: dict[str, str]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    def fetch(self, url: str, max_bytes: int) -> tuple[str, str]:
        self.calls.append(url)
        return self.documents[url][:max_bytes], "text/plain"


class TestInternetLearningPipeline(unittest.TestCase):
    """Prouve Acquire → Extract → Relier → Tester → SECAU → suivi."""

    def setUp(self) -> None:
        self.repository = MemoryRepository()
        self.urls = (
            "https://source-a.example/deployer",
            "https://source-b.example/deployer",
        )

    def tearDown(self) -> None:
        self.repository.close()

    def _pipeline(
        self,
        source_a: str = SOURCE_A,
        source_b: str = SOURCE_B,
    ) -> tuple[InternetLearningPipeline, MemoireRelationsVerbes]:
        fetcher = FakeFetcher(
            {self.urls[0]: source_a, self.urls[1]: source_b}
        )
        memory = MemoireRelationsVerbes()
        acquire = InternetAcquire(self.repository, fetcher=fetcher)
        return (
            InternetLearningPipeline(
                self.repository,
                acquire,
                relations_memory=memory,
            ),
            memory,
        )

    @staticmethod
    def _resolver_factory(candidate):
        positives = set(candidate["examples"])

        def resolve(text: str) -> str | None:
            return candidate["target"] if text in positives else None

        return resolve

    def test_complete_pipeline_promotes_and_synchronizes_relation(self) -> None:
        """Chaque étape laisse une preuve avant l'activation finale."""

        pipeline, memory = self._pipeline()
        result = pipeline.learn_relation(
            self.urls,
            self._resolver_factory,
            regressions=(lambda: True,),
        )

        self.assertEqual(2, len(result.evidence_ids))
        self.assertTrue(result.hypothesis_id.startswith("hypothesis_"))
        self.assertTrue(result.report_id.startswith("report_"))
        self.assertEqual(SecauVerdict.PROMOTE, result.secau.verdict)
        relation = self.repository.relation(result.secau.concept_id)
        self.assertEqual("confirmed", relation["status"])
        self.assertEqual("installer", relation["target"])
        self.assertEqual("installer", memory.obtenir("deploie")["target"])

        events = [event["event"] for event in self.repository.audit_events()]
        self.assertEqual(2, events.count("EVIDENCE_ADDED"))
        self.assertIn("HYPOTHESIS_CREATED", events)
        self.assertIn("TEST_RECORDED", events)
        self.assertIn("RELATION_PROMOTED", events)

    def test_missing_counterexamples_prevents_promotion(self) -> None:
        """Deux sources ne compensent jamais l'absence de cas négatifs."""

        source_a = SOURCE_A.replace(
            "Contre-exemple : deploie une carte sur la table\n", ""
        )
        source_b = SOURCE_B.replace(
            "Contre-exemple : deploie les ailes\n", ""
        )
        pipeline, memory = self._pipeline(source_a, source_b)
        result = pipeline.learn_relation(
            self.urls,
            self._resolver_factory,
        )
        self.assertEqual(SecauVerdict.REJECT, result.secau.verdict)
        self.assertIsNone(memory.obtenir("deploie"))

    def test_two_distinct_domains_are_required(self) -> None:
        """Deux pages du même site ne constituent pas deux sources indépendantes."""

        fetcher = FakeFetcher({})
        acquire = InternetAcquire(self.repository, fetcher=fetcher)
        with self.assertRaises(ValueError):
            acquire.fetch_many(
                (
                    "https://same.example/a",
                    "https://same.example/b",
                )
            )
        self.assertEqual([], fetcher.calls)

    def test_successes_and_errors_change_mastery_and_quarantine(self) -> None:
        """La maîtrise monte avec l'usage et trois erreurs isolent la relation."""

        pipeline, _ = self._pipeline()
        result = pipeline.learn_relation(
            self.urls,
            self._resolver_factory,
        )
        relation_id = result.secau.concept_id
        successful = self.repository.record_relation_use(
            relation_id,
            success=True,
            request="deploie python",
        )
        self.assertEqual(75, successful["mastery_score"])

        for index in range(3):
            failed = self.repository.record_relation_use(
                relation_id,
                success=False,
                request=f"erreur {index}",
                details={"expected": "installer", "obtained": "inconnu"},
            )
        self.assertEqual("quarantined", failed["status"])
        self.assertEqual(3, failed["consecutive_errors"])
        self.assertEqual(
            4, len(self.repository.relation_usage(relation_id))
        )


if __name__ == "__main__":
    unittest.main()
