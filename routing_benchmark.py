"""Barrière mesurable pour ActionCore et le routeur déclaratif."""

from __future__ import annotations

from kairos import Kernel
from kairos.routing import RouteurDynamique, StatutRoute


def main() -> int:
    routeur = RouteurDynamique()
    cas = {
        "chercher": "information.search",
        "lire": "information.read",
        "relire": "information.reread",
        "verifier": "information.verify",
        "expliquer": "response.explain",
        "comparer": "information.compare",
        "tester": "cognition.test",
        "corriger": "learning.correct",
        "planifier": "cognition.plan",
        "poser": "response.ask",
        "remercier": "response.thank",
        "saluer": "response.greet",
        "memoriser": "learning.memorize",
    }
    correctes = 0
    for action, route_attendue in cas.items():
        plan = routeur.planifier(action, "cible")
        correctes += int(plan.id == route_attendue)
        if plan.statut is not StatutRoute.BLOCKED:
            print(f"ROUTING_FAILED: {action} exécutable sans capacités")
            return 1

    composee = routeur.planifier("enqueter", "quark")
    composition_sure = (
        composee.id == "generated.enqueter"
        and composee.generee
        and composee.statut is StatutRoute.BLOCKED
    )
    decision = Kernel().traiter("cherche toi-même atome")
    ancrage_self = (
        decision.analyse.action.valeur == "chercher"
        and decision.analyse.cible.valeur == "atome"
        and decision.routage is not None
        and decision.routage["id"] == "information.search"
    )
    total = len(cas) + 2
    reussis = correctes + int(composition_sure) + int(ancrage_self)
    taux = round(100 * reussis / total, 2)
    print(f"ROUTING_BENCHMARK: {reussis}/{total} ({taux}%)")
    print("FALSE_ROUTE_EXECUTIONS: 0")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
