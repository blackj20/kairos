"""Tests V0.15 : buts persistants, événements et attention."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Kernel
from kairos.autonomie import (
    GestionnaireAttention,
    MoteurAutonomie,
    StatutBut,
    StockageButs,
    TypeEvenementBut,
)
from kairos.causal import MoteurCausal, StockageCausal


class AutonomyGoalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.goal_store = StockageButs(self.root / "goals.db")
        self.causal_store = StockageCausal(self.root / "causal.db")
        self.kernel = Kernel()
        self.causal = MoteurCausal(
            kernel=self.kernel, stockage=self.causal_store
        )
        self.engine = MoteurAutonomie(
            causal=self.causal, stockage=self.goal_store
        )

    def tearDown(self) -> None:
        self.kernel.close()
        self.causal_store.close()
        self.goal_store.close()
        self.temp.cleanup()

    def test_known_goal_completes_from_causal_evidence(self) -> None:
        result = self.engine.lancer("cherche atome")
        self.assertEqual(StatutBut.COMPLETED, result.but.statut)
        self.assertIsNotNone(result.but.dernier_episode_id)
        self.assertTrue(result.episode["evaluation"]["objectif_atteint"])
        self.assertIn(
            "goal.completed",
            [item["event_type"] for item in result.evenements],
        )

    def test_unknown_information_blocks_instead_of_claiming_success(self) -> None:
        result = self.engine.lancer("cherche xylophore")
        self.assertEqual(StatutBut.BLOCKED, result.but.statut)
        self.assertEqual("information_not_found", result.but.derniere_raison)
        self.assertTrue(result.episode["evaluation"]["succes_technique"])
        self.assertFalse(result.episode["evaluation"]["objectif_atteint"])

    def test_incomplete_goal_is_blocked_without_causal_execution(self) -> None:
        result = self.engine.lancer("cherche")
        self.assertEqual(StatutBut.BLOCKED, result.but.statut)
        self.assertIsNone(result.episode)
        self.assertIsNone(result.but.dernier_episode_id)
        self.assertIn("route_blocked", result.but.derniere_raison)

    def test_pending_goal_survives_restart_and_resumes(self) -> None:
        goal = self.engine.creer_but("cherche atome")
        goal_id = goal.id
        self.goal_store.close()
        reopened = StockageButs(self.root / "goals.db")
        resumed = MoteurAutonomie(causal=self.causal, stockage=reopened)
        result = resumed.executer_prochaine_etape(goal_id)
        self.assertEqual(StatutBut.COMPLETED, result.but.statut)
        self.assertIn(
            "goal.activated",
            [item["event_type"] for item in result.evenements],
        )
        reopened.close()
        self.goal_store = StockageButs(self.root / "goals.db")

    def test_attention_selects_highest_effective_priority(self) -> None:
        low = self.engine.creer_but("cherche atome", priorite=20)
        high = self.engine.creer_but("cherche fonction", priorite=90)
        choice = self.engine.selectionner()
        self.assertEqual(high.id, choice.goal_id)
        self.assertNotEqual(low.id, choice.goal_id)
        self.assertIn("priorité=90", choice.raisons)

    def test_budget_stops_repeated_execution_errors(self) -> None:
        def fail(_: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("failure injected")

        self.kernel.routeur.registre._handlers["memory.search"] = fail
        result = self.engine.lancer("cherche atome", max_etapes=2)
        self.assertEqual(StatutBut.BLOCKED, result.but.statut)
        self.assertEqual(2, result.but.etapes_utilisees)
        self.assertEqual("budget_exhausted", result.but.derniere_raison)
        events = [item["event_type"] for item in result.evenements]
        self.assertEqual(2, events.count("step.started"))
        self.assertIn("budget.exhausted", events)

    def test_invalidation_prevents_future_execution(self) -> None:
        goal = self.engine.creer_but("cherche atome")
        invalidated = self.engine.invalider(
            goal.id, "la mission utilisateur a changé"
        )
        self.assertEqual(StatutBut.INVALIDATED, invalidated.statut)
        with self.assertRaises(ValueError):
            self.engine.executer_prochaine_etape(goal.id)

    def test_event_log_is_ordered_and_append_only(self) -> None:
        goal = self.engine.creer_but("cherche atome")
        self.engine.executer_prochaine_etape(goal.id)
        events = self.goal_store.evenements(goal.id)
        sequences = [item["sequence"] for item in events]
        self.assertEqual(sorted(sequences), sequences)
        self.assertEqual("goal.created", events[0]["event_type"])
        self.assertEqual("goal.completed", events[-1]["event_type"])

    def test_storage_refuses_skipped_state_transition(self) -> None:
        goal = self.engine.creer_but("cherche atome")
        with self.assertRaises(ValueError):
            self.goal_store.transition(
                goal.id,
                StatutBut.COMPLETED,
                TypeEvenementBut.COMPLETED,
                {"reason": "forbidden shortcut"},
            )

    def test_attention_is_read_only_over_causal_memory(self) -> None:
        goal = self.engine.creer_but("cherche atome")
        choice = GestionnaireAttention.choisir([goal])
        self.assertEqual(goal.id, choice.goal_id)
        self.assertIsNone(self.causal_store.dernier())
        self.assertEqual(0, goal.etapes_utilisees)


if __name__ == "__main__":
    unittest.main()
