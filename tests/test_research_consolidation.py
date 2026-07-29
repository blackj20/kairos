"""Tests de la consolidation recherche → Tester → SECAU."""

from __future__ import annotations

import unittest

from kairos.cognition import SecauVerdict
from kairos.information import ConsolidateurRecherche
from kairos.memory import MemoryRepository


class ResearchConsolidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = MemoryRepository()

    def tearDown(self) -> None:
        self.repository.close()

    def candidate(
        self,
        *,
        domains: int = 2,
        tampered: bool = False,
        protected: bool = False,
    ) -> str:
        urls = [
            "https://science.example/xylophore",
            (
                "https://dictionary.example/xylophore"
                if domains == 2
                else "https://science.example/definition-xylophore"
            ),
        ]
        original_claims = [
            "Un xylophore est un organisme associé au bois.",
            "Le xylophore désigne un organisme vivant lié au bois.",
        ]
        evidence = [
            self.repository.add_evidence("web", url, claim, 75)
            for url, claim in zip(urls, original_claims)
        ]
        claims = list(original_claims)
        if tampered:
            claims[1] = "Cette affirmation a été modifiée après la preuve."
        payload = {
            "created_from_experience_id": "research_test",
            "name": "xylophore",
            "domain": "general",
            "definition": original_claims[0],
            "evidence_ids": evidence,
            "source_urls": urls,
            "source_claims": claims,
            "source_domains": [
                "science.example",
                "dictionary.example" if domains == 2 else "science.example",
            ],
            "comparison": {"independent_domains": domains},
            "research_kind": "information.search",
            "score": 70,
        }
        if protected:
            payload["identity"] = "altération interdite"
        return self.repository.add_hypothesis(payload)

    def test_complete_candidate_is_tested_then_promoted(self) -> None:
        hypothesis = self.candidate()
        result = ConsolidateurRecherche(self.repository).consolider(hypothesis)
        self.assertTrue(result.dossier.ready_for_tester)
        self.assertIsNotNone(result.report_id)
        self.assertTrue(result.report and result.report["passed"])
        self.assertEqual(SecauVerdict.PROMOTE, result.secau.verdict)
        self.assertEqual(1, len(self.repository.search({"text": "xylophore"})))

    def test_single_domain_needs_more_evidence(self) -> None:
        hypothesis = self.candidate(domains=1)
        result = ConsolidateurRecherche(self.repository).consolider(hypothesis)
        self.assertFalse(result.dossier.ready_for_tester)
        self.assertIsNone(result.report_id)
        self.assertEqual(
            SecauVerdict.NEEDS_MORE_EVIDENCE,
            result.secau.verdict,
        )
        self.assertEqual([], self.repository.search({"text": "xylophore"}))

    def test_tampered_claim_is_rejected_by_hash(self) -> None:
        hypothesis = self.candidate(tampered=True)
        result = ConsolidateurRecherche(self.repository).consolider(hypothesis)
        self.assertEqual(SecauVerdict.REJECT, result.secau.verdict)
        self.assertFalse(result.report and result.report["passed"])
        self.assertIn(False, result.report["integrity"])

    def test_protected_payload_is_quarantined(self) -> None:
        hypothesis = self.candidate(protected=True)
        result = ConsolidateurRecherche(self.repository).consolider(hypothesis)
        self.assertEqual(SecauVerdict.QUARANTINE, result.secau.verdict)
        self.assertEqual([], self.repository.search({"text": "xylophore"}))

    def test_old_candidate_without_claims_stays_candidate(self) -> None:
        evidence = self.repository.add_evidence(
            "web", "https://source.example/ancien", "Ancien contenu.", 60
        )
        hypothesis = self.repository.add_hypothesis(
            {
                "created_from_experience_id": "research_old",
                "name": "ancien",
                "definition": "Ancien contenu.",
                "evidence_ids": [evidence],
                "source_urls": ["https://source.example/ancien"],
                "research_kind": "information.search",
                "score": 50,
            }
        )
        result = ConsolidateurRecherche(self.repository).consolider(hypothesis)
        self.assertEqual(SecauVerdict.NEEDS_MORE_EVIDENCE, result.secau.verdict)
        self.assertIn("deux_affirmations", result.dossier.missing)

    def test_every_review_is_observable(self) -> None:
        hypothesis = self.candidate(domains=1)
        ConsolidateurRecherche(self.repository).consolider(hypothesis)
        reviews = [
            event for event in self.repository.audit_events()
            if event["event"] == "SECAU_REVIEWED"
        ]
        self.assertEqual(1, len(reviews))
        self.assertEqual("needs_more_evidence", reviews[0]["verdict"])
        self.assertEqual(hypothesis, reviews[0]["hypothesis"])


if __name__ == "__main__":
    unittest.main()
