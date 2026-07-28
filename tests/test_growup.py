"""Tests de la boucle GrowUp sans promotion implicite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.connaissances import Connaissances
from kairos.decision import MoteurDecision, StockageMemoire
from kairos.growup import (
    MoteurGrowUp,
    PreuveApprentissage,
    StockageGrowUp,
)
from kairos.memory import MemoryRepository
from kairos.normalisation import cle
from kairos.relations_verbes import MemoireRelationsVerbes


class GrowUpTests(unittest.TestCase):
    def _kernel(self, stockage, relations=None) -> Kernel:
        comprendre = Comprendre(
            Connaissances(relations_verbes=relations or MemoireRelationsVerbes())
        )
        return Kernel(
            comprendre=comprendre,
            moteur_decision=MoteurDecision(comprendre, stockage=stockage),
        )

    def _enseigner_trois_episodes(self, stockage) -> None:
        kernel = self._kernel(stockage)
        for logiciel in ("python", "docker", "git"):
            decision = kernel.traiter(f"deploie {logiciel}")
            self.assertEqual("clarification", decision.route)
            self.assertIsNotNone(decision.question_id)
            experience = kernel.repondre_a(
                decision.question_id,
                "installer",
                acteur="creator",
            )
            candidate = experience.resolution["candidate_semantic_relation"]
            self.assertEqual("deploie", candidate["source"])
            self.assertEqual("installer", candidate["target"])

    @staticmethod
    def _resolver(texte: str) -> str | None:
        mots = set(cle(texte).split())
        logiciels = {"python", "docker", "git", "vscode", "node"}
        if "deploie" in mots and mots.intersection(logiciels):
            return "installer"
        return None

    def test_three_similar_experiences_become_one_prioritized_plan(self) -> None:
        stockage_decision = StockageMemoire()
        self._enseigner_trois_episodes(stockage_decision)
        relations = MemoireRelationsVerbes()
        moteur = MoteurGrowUp(
            stockage_decision,
            cognitive_repository=MemoryRepository(),
            growup_storage=StockageGrowUp(),
            relations_memory=relations,
        )

        rapport = moteur.analyser()

        self.assertEqual(1, len(rapport.groupes))
        groupe = rapport.groupes[0]
        plan = rapport.plans[0]
        self.assertEqual(3, groupe.occurrences)
        self.assertEqual("deploie", groupe.relation_source)
        self.assertEqual("installer", groupe.relation_target)
        self.assertEqual("collecter_preuves", plan.route)
        self.assertEqual(6, plan.tests_requis)
        self.assertIsNone(relations.obtenir("deploie"))
        self.assertEqual(1, len(moteur.stockage.runs()))
        self.assertTrue(moteur.stockage.audit())

    def test_relation_is_reused_only_after_tester_and_secau(self) -> None:
        stockage_decision = StockageMemoire()
        self._enseigner_trois_episodes(stockage_decision)
        relations = MemoireRelationsVerbes()
        cognitive = MemoryRepository()
        growup_storage = StockageGrowUp()
        moteur = MoteurGrowUp(
            stockage_decision,
            cognitive_repository=cognitive,
            growup_storage=growup_storage,
            relations_memory=relations,
        )
        plan = moteur.analyser().plans[0]
        self.assertIsNone(relations.obtenir("deploie"))

        resultat = moteur.consolider_relation(
            plan.id,
            preuves=(
                PreuveApprentissage(
                    "creator",
                    "creator://lesson/deploie",
                    "Déployer un logiciel signifie ici l'installer pour le rendre disponible.",
                    95,
                ),
                PreuveApprentissage(
                    "documentation",
                    "manual://software/deployment",
                    "Dans ce contexte contrôlé, déployer une application conduit à son installation.",
                    85,
                ),
            ),
            exemples=("deploie python", "deploie docker", "deploie git"),
            contre_exemples=("deploie fichier", "deploie dossier"),
            resolver=self._resolver,
            regressions=(lambda: self._kernel(StockageMemoire()).traiter(
                "cette marche est cassée"
            ).analyse.action.valeur is None,),
        )

        self.assertEqual("promote", resultat.verdict)
        self.assertIsNotNone(resultat.relation_id)
        self.assertEqual("installer", relations.obtenir("deploie")["target"])
        self.assertEqual("promoted", growup_storage.plan(plan.id).statut)

        nouveau_kernel = self._kernel(StockageMemoire(), relations)
        decision = nouveau_kernel.traiter("deploie vscode")
        self.assertEqual("installer", decision.analyse.action.valeur)
        self.assertEqual("competence", decision.route)
        self.assertIsNone(decision.question_id)
        self.assertTrue(
            any(event["event"] == "RELATION_PROMOTED" for event in cognitive.audit_events())
        )

    def test_insufficient_evidence_never_activates_relation(self) -> None:
        stockage_decision = StockageMemoire()
        self._enseigner_trois_episodes(stockage_decision)
        relations = MemoireRelationsVerbes()
        moteur = MoteurGrowUp(
            stockage_decision,
            cognitive_repository=MemoryRepository(),
            growup_storage=StockageGrowUp(),
            relations_memory=relations,
        )
        plan = moteur.analyser().plans[0]

        with self.assertRaises(ValueError):
            moteur.consolider_relation(
                plan.id,
                preuves=(
                    PreuveApprentissage(
                        "creator",
                        "creator://single-source",
                        "Une seule preuve ne peut jamais confirmer cette relation.",
                        95,
                    ),
                ),
                exemples=("deploie python", "deploie docker", "deploie git"),
                contre_exemples=("deploie fichier", "deploie dossier"),
                resolver=self._resolver,
            )

        self.assertIsNone(relations.obtenir("deploie"))
        self.assertEqual("planned", moteur.stockage.plan(plan.id).statut)

    def test_conflicting_targets_require_creator_clarification(self) -> None:
        stockage = StockageMemoire()
        kernel = self._kernel(stockage)
        for logiciel, cible in (("python", "installer"), ("docker", "ouvrir")):
            decision = kernel.traiter(f"deploie {logiciel}")
            kernel.repondre_a(decision.question_id, cible, acteur="creator")

        moteur = MoteurGrowUp(stockage)
        rapport = moteur.analyser()
        groupe = rapport.groupes[0]
        plan = rapport.plans[0]

        self.assertGreater(len(groupe.relation_targets), 1)
        self.assertTrue(groupe.contradictions)
        self.assertEqual("demander_createur", plan.route)
        self.assertIn("target_confirmation", plan.manques)

    def test_growup_registry_survives_restart(self) -> None:
        stockage_decision = StockageMemoire()
        self._enseigner_trois_episodes(stockage_decision)

        with tempfile.TemporaryDirectory() as dossier:
            path = Path(dossier) / "growup.db"
            premier = StockageGrowUp(path)
            moteur = MoteurGrowUp(
                stockage_decision,
                growup_storage=premier,
            )
            plan_id = moteur.analyser().plans[0].id
            premier.close()

            second = StockageGrowUp(path)
            self.assertIsNotNone(second.plan(plan_id))
            self.assertEqual(1, len(second.runs()))
            self.assertTrue(second.audit())
            second.close()


if __name__ == "__main__":
    unittest.main()
