"""Tests du routage JSON vers capacités explicitement enregistrées."""

from __future__ import annotations

import unittest

from kairos import Kernel
from kairos.routing import RouteurDynamique, StatutRoute


class ActionRouterTests(unittest.TestCase):
    def test_known_route_reports_missing_capabilities(self) -> None:
        plan = RouteurDynamique().planifier("chercher", "atome")
        self.assertEqual(StatutRoute.BLOCKED, plan.statut)
        self.assertEqual("information.search", plan.id)
        self.assertIn("web.search", plan.capacites_manquantes)

    def test_complete_declared_route_executes_in_order(self) -> None:
        routeur = RouteurDynamique()
        appels: list[str] = []

        def handler(nom: str):
            def executer(contexte: dict[str, object]) -> dict[str, object]:
                appels.append(nom)
                return {nom: True}
            return executer

        permissions = {
            "memory.search": ("memory.read",),
            "web.search": ("network.read",),
            "sources.compare": (),
            "knowledge.propose": ("memory.candidate.write",),
            "response.explain": (),
        }
        for capacite, accordees in permissions.items():
            routeur.enregistrer_capacite(
                capacite,
                handler(capacite),
                permissions=accordees,
            )

        plan = routeur.planifier("chercher", "atome")
        self.assertEqual(StatutRoute.READY, plan.statut)
        resultat = routeur.executer(plan)
        self.assertEqual("information.search", resultat["route_id"])
        self.assertEqual(list(permissions), appels)
        self.assertEqual(5, len(resultat["trace"]))

    def test_missing_route_is_composed_as_candidate(self) -> None:
        routeur = RouteurDynamique()
        permissions = {
            "memory.search": ("memory.read",),
            "web.search": ("network.read",),
            "sources.compare": (),
            "knowledge.propose": ("memory.candidate.write",),
            "response.explain": (),
        }
        for capacite, accordees in permissions.items():
            routeur.enregistrer_capacite(
                capacite,
                lambda contexte: {},
                permissions=accordees,
            )

        plan = routeur.planifier("enqueter", "quark")
        self.assertEqual(StatutRoute.CANDIDATE, plan.statut)
        self.assertTrue(plan.generee)
        with self.assertRaises(PermissionError):
            routeur.executer(plan)

    def test_json_cannot_import_an_undeclared_handler(self) -> None:
        routeur = RouteurDynamique()
        with self.assertRaises(KeyError):
            routeur.enregistrer_capacite(
                "os.system", lambda contexte: {}, permissions=()
            )

    def test_capability_permissions_are_required(self) -> None:
        routeur = RouteurDynamique()
        with self.assertRaises(PermissionError):
            routeur.enregistrer_capacite(
                "web.search", lambda contexte: {}, permissions=()
            )

    def test_target_is_mandatory(self) -> None:
        plan = RouteurDynamique().planifier("chercher")
        self.assertEqual(StatutRoute.BLOCKED, plan.statut)
        self.assertIn("cible", plan.raison)

    def test_kernel_exposes_blocked_route_instead_of_empty_relation(self) -> None:
        decision = Kernel().traiter("cherche atome")
        self.assertEqual("chercher", decision.analyse.action.valeur)
        self.assertIsNotNone(decision.routage)
        assert decision.routage is not None
        self.assertEqual("information.search", decision.routage["id"])
        self.assertEqual("blocked", decision.routage["statut"])
        self.assertIn("Capacités manquantes", decision.reponse)

    def test_self_modifier_does_not_replace_the_target(self) -> None:
        decision = Kernel().traiter("cherche toi-même atome")
        self.assertEqual("chercher", decision.analyse.action.valeur)
        self.assertEqual("atome", decision.analyse.cible.valeur)
        self.assertIsNotNone(decision.routage)


if __name__ == "__main__":
    unittest.main()
