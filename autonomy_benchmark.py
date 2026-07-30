"""Barrière mesurable V0.15 pour buts, événements et attention."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kairos import Kernel
from kairos.autonomie import MoteurAutonomie, StatutBut, StockageButs
from kairos.causal import MoteurCausal, StockageCausal


def main() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        goals = StockageButs(root / "goals.db")
        causal_store = StockageCausal(root / "causal.db")
        kernel = Kernel()
        causal = MoteurCausal(kernel=kernel, stockage=causal_store)
        engine = MoteurAutonomie(causal=causal, stockage=goals)

        known = engine.lancer("cherche atome")
        checks["known_completed"] = known.but.statut is StatutBut.COMPLETED
        checks["known_has_episode"] = known.but.dernier_episode_id is not None
        checks["goal_from_evidence"] = bool(
            known.episode["evaluation"]["objectif_atteint"]
        )

        unknown = engine.lancer("cherche xylophore")
        checks["unknown_blocked"] = unknown.but.statut is StatutBut.BLOCKED
        checks["technical_not_goal"] = bool(
            unknown.episode["evaluation"]["succes_technique"]
            and not unknown.episode["evaluation"]["objectif_atteint"]
        )

        incomplete = engine.lancer("cherche")
        checks["incomplete_no_execution"] = (
            incomplete.but.statut is StatutBut.BLOCKED
            and incomplete.episode is None
        )

        low = engine.creer_but("cherche fonction", priorite=10)
        high = engine.creer_but("cherche boucle", priorite=90)
        choice = engine.selectionner()
        checks["attention_priority"] = choice is not None and choice.goal_id == high.id
        checks["attention_explained"] = bool(choice and len(choice.raisons) >= 3)

        invalidated = engine.invalider(low.id, "objectif remplacé")
        checks["invalidation_terminal"] = invalidated.statut is StatutBut.INVALIDATED

        persistent = engine.creer_but("cherche atome")
        persistent_id = persistent.id
        goals.close()
        goals = StockageButs(root / "goals.db")
        resumed = MoteurAutonomie(causal=causal, stockage=goals)
        after_restart = resumed.executer_prochaine_etape(persistent_id)
        checks["restart_resume"] = after_restart.but.statut is StatutBut.COMPLETED

        def fail(_: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("benchmark failure")

        kernel.routeur.registre._handlers["memory.search"] = fail
        budget = resumed.lancer("cherche atome", max_etapes=2)
        checks["budget_enforced"] = (
            budget.but.statut is StatutBut.BLOCKED
            and budget.but.etapes_utilisees == 2
        )
        checks["no_infinite_retry"] = (
            [item["event_type"] for item in budget.evenements].count(
                "step.started"
            )
            == 2
        )
        checks["events_append_only"] = (
            [item["sequence"] for item in budget.evenements]
            == sorted(item["sequence"] for item in budget.evenements)
        )
        checks["no_false_completion"] = all(
            result.but.statut is not StatutBut.COMPLETED
            for result in (unknown, incomplete, budget)
        )
        checks["no_hidden_daemon"] = not hasattr(resumed, "start_background")

        kernel.close()
        causal_store.close()
        goals.close()

    passed = sum(checks.values())
    total = len(checks)
    print(f"AUTONOMY_BENCHMARK: {passed}/{total}")
    print("GOAL_COMPLETION_KNOWN: 100%" if checks["known_completed"] else "GOAL_COMPLETION_KNOWN: 0%")
    print(f"UNSAFE_FALSE_COMPLETIONS: {0 if checks['no_false_completion'] else 1}")
    print(f"UNBOUNDED_LOOPS: {0 if checks['no_infinite_retry'] else 1}")
    if passed != total:
        for name, ok in checks.items():
            if not ok:
                print(f"FAILED: {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
