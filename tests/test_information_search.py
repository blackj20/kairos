"""Tests de la route exécutable de recherche d'information."""

from __future__ import annotations

import unittest

from kairos import Kernel
from kairos.information import FournisseurStatique, SourceInformation
from kairos.memory import MemoryRepository


class InformationSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = MemoryRepository()

    def tearDown(self) -> None:
        self.repository.close()

    @staticmethod
    def fournisseur() -> FournisseurStatique:
        return FournisseurStatique(
            (
                SourceInformation(
                    "Xylophore — dictionnaire",
                    "https://dictionnaire.example/xylophore",
                    "Un xylophore est un organisme associé au bois.",
                    confiance=70,
                ),
                SourceInformation(
                    "Xylophore — encyclopédie",
                    "https://encyclopedie.example/xylophore",
                    "Le terme xylophore décrit un organisme lié au bois.",
                    confiance=75,
                ),
            )
        )

    def test_recherche_locale_execute_la_route(self) -> None:
        decision = Kernel(
            cognitive_repository=self.repository
        ).traiter("cherche toi-même atoms")
        assert decision.routage is not None
        self.assertEqual("ready", decision.routage["statut"])
        self.assertIn("atome", decision.reponse.casefold())
        self.assertIn("Source confirmée", decision.reponse)

    def test_hors_ligne_n_invente_pas(self) -> None:
        decision = Kernel(
            cognitive_repository=self.repository
        ).traiter("cherche xylophore")
        self.assertIn("Aucune connaissance confirmée", decision.reponse)
        self.assertIn("--online", decision.reponse)
        self.assertEqual([], self.repository.search({"text": "xylophore"}))

    def test_web_cree_une_hypothese_non_confirmee(self) -> None:
        decision = Kernel(
            cognitive_repository=self.repository,
            web_provider=self.fournisseur(),
        ).traiter("cherche toi-même xylophore")
        self.assertIn("hypothèse candidate", decision.reponse)
        self.assertIn("SECAU attend les tests", decision.reponse)
        self.assertEqual([], self.repository.search({"text": "xylophore"}))
        hypotheses = [
            event for event in self.repository.audit_events()
            if event["event"] == "RESEARCH_CANDIDATE_CREATED"
        ]
        self.assertEqual(1, len(hypotheses))

    def test_candidate_reste_en_attente(self) -> None:
        Kernel(
            cognitive_repository=self.repository,
            web_provider=self.fournisseur(),
        ).traiter("cherche xylophore")
        candidate = self.repository.candidate_for("xylophore")
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual("candidate", candidate["status"])
        self.assertEqual(2, len(candidate["payload"]["source_urls"]))

    def test_une_recherche_repetee_reutilise_la_candidate(self) -> None:
        kernel = Kernel(
            cognitive_repository=self.repository,
            web_provider=self.fournisseur(),
        )
        kernel.traiter("cherche xylophore")
        kernel.traiter("cherche xylophore")
        creations = [
            event for event in self.repository.audit_events()
            if event["event"] == "RESEARCH_CANDIDATE_CREATED"
        ]
        self.assertEqual(1, len(creations))

    def test_secau_n_est_jamais_appele_par_la_recherche(self) -> None:
        Kernel(
            cognitive_repository=self.repository,
            web_provider=self.fournisseur(),
        ).traiter("cherche xylophore")
        revues = [
            event for event in self.repository.audit_events()
            if event["event"] == "SECAU_REVIEWED"
        ]
        self.assertEqual([], revues)


if __name__ == "__main__":
    unittest.main()
