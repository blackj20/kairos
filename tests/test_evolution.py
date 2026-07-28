"""Tests de non-régression de la boucle expérience → connaissance."""

from __future__ import annotations

import unittest

from kairos.cognition import Reflechir, Secau, SecauVerdict, Tester
from kairos.memory import MemoryRepository
from kairos.response import ResponseComposer, ResponseContract, ResponseVerifier


class TestEvolution(unittest.TestCase):
    """Valide les invariants critiques de promotion et de réponse."""

    def setUp(self) -> None:
        """Utilise SQLite en mémoire afin de ne modifier aucun fichier utilisateur."""

        self.repository = MemoryRepository()

    def tearDown(self) -> None:
        """Libère explicitement la connexion après chaque test."""

        self.repository.close()

    def _candidate(self) -> tuple[str, str]:
        """Construit une hypothèse prouvée et un rapport complet réussi."""

        evidence = self.repository.add_evidence(
            "document", "doc://python/class", "Une classe crée des instances.", 90
        )
        hypothesis = Reflechir(self.repository).from_experience(
            "experience_001",
            name="classe Python",
            definition="modèle permettant de créer des instances",
            evidence_ids=[evidence],
            domain="python",
        )
        report, result = Tester(self.repository).test(
            hypothesis,
            original=lambda: True,
            paraphrases=(lambda: True, lambda: True, lambda: True),
            regressions=(lambda: True,),
        )
        self.assertTrue(result["passed"])
        return hypothesis, report

    def test_hypothesis_is_not_directly_searchable(self) -> None:
        """Une hypothèse ne doit jamais apparaître comme connaissance."""

        self._candidate()
        self.assertEqual([], self.repository.search({"text": "classe Python"}))

    def test_secau_promotes_only_after_complete_report(self) -> None:
        """SECAU rend une connaissance visible après tous les contrôles."""

        hypothesis, report = self._candidate()
        result = Secau(self.repository).review(
            hypothesis, report, {"evidence_ids": ["present"]}
        )
        self.assertEqual(SecauVerdict.PROMOTE, result.verdict)
        self.assertEqual(
            1, len(self.repository.search({"text": "classe Python"}))
        )

    def test_three_paraphrases_are_mandatory(self) -> None:
        """Deux reformulations ne suffisent pas à valider un rapport."""

        report_id, report = Tester(self.repository).test(
            "candidate", lambda: True, (lambda: True, lambda: True)
        )
        self.assertFalse(report["passed"])
        self.assertTrue(report_id.startswith("report_"))

    def test_protected_payload_is_quarantined(self) -> None:
        """Les données self protégées ne peuvent pas être promues automatiquement."""

        hypothesis, report = self._candidate()
        result = Secau(self.repository).review(
            hypothesis, report, {"identity": "nouvelle", "evidence_ids": ["x"]}
        )
        self.assertEqual(SecauVerdict.QUARANTINE, result.verdict)

    def test_response_uses_only_confirmed_knowledge(self) -> None:
        """Le compositeur cite uniquement un concept déjà promu."""

        hypothesis, report = self._candidate()
        Secau(self.repository).review(
            hypothesis, report, {"evidence_ids": ["present"]}
        )
        contract = ResponseContract(
            mode="explanation",
            intent="lecon",
            concepts=("classe Python",),
            evidence_ids=("evidence_known",),
        )
        response = ResponseComposer(self.repository).compose(contract)
        self.assertIn("modèle permettant", response)
        self.assertTrue(ResponseVerifier().verify(contract, response).valid)


if __name__ == "__main__":
    unittest.main()
