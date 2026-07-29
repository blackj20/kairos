"""Barrière V0.12 : généralisation sur 100 formulations naturelles."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from kairos import Kernel


CRITERES = {
    "corpus_size": 100,
    "intent_accuracy_min": 90.0,
    "route_accuracy_min": 90.0,
    "group_accuracy_min": 80.0,
    "unsafe_false_executions_max": 0,
}


def executer(chemin: Path | None = None) -> dict[str, Any]:
    racine = Path(__file__).resolve().parent
    chemin = chemin or racine / "benchmarks" / "intent_generalization_100.json"
    corpus = json.loads(chemin.read_text(encoding="utf-8"))
    cas = corpus["cases"]

    intentions_ok = 0
    routes_ok = 0
    fausses_executions = 0
    groupes: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "intent_ok": 0, "route_ok": 0}
    )
    echecs: list[dict[str, Any]] = []

    for exemple in cas:
        kernel = Kernel()
        try:
            decision = kernel.traiter(
                exemple["text"],
                acteur=exemple.get("actor", "creator"),
            )
        finally:
            kernel.close()

        intention = decision.analyse.cognition.get("intention")
        route = decision.route
        intention_valide = intention == exemple["expected_intent"]
        route_valide = route == exemple["expected_route"]
        groupe = groupes[exemple["group"]]
        groupe["total"] += 1
        groupe["intent_ok"] += int(intention_valide)
        groupe["route_ok"] += int(route_valide)
        intentions_ok += int(intention_valide)
        routes_ok += int(route_valide)

        if route == "competence" and exemple["expected_route"] != "competence":
            fausses_executions += 1
        if not intention_valide or not route_valide:
            echecs.append(
                {
                    "group": exemple["group"],
                    "text": exemple["text"],
                    "expected_intent": exemple["expected_intent"],
                    "obtained_intent": intention,
                    "expected_route": exemple["expected_route"],
                    "obtained_route": route,
                    "unknown": list(decision.analyse.jetons_inconnus),
                }
            )

    total = len(cas)
    groupe_stats = {
        nom: {
            **stats,
            "intent_accuracy": round(100 * stats["intent_ok"] / stats["total"], 2),
            "route_accuracy": round(100 * stats["route_ok"] / stats["total"], 2),
        }
        for nom, stats in groupes.items()
    }
    intention_accuracy = round(100 * intentions_ok / total, 2) if total else 0.0
    route_accuracy = round(100 * routes_ok / total, 2) if total else 0.0
    minimum_groupe = min(
        (
            min(stats["intent_accuracy"], stats["route_accuracy"])
            for stats in groupe_stats.values()
        ),
        default=0.0,
    )
    valide = (
        total == CRITERES["corpus_size"]
        and intention_accuracy >= CRITERES["intent_accuracy_min"]
        and route_accuracy >= CRITERES["route_accuracy_min"]
        and minimum_groupe >= CRITERES["group_accuracy_min"]
        and fausses_executions <= CRITERES["unsafe_false_executions_max"]
    )
    return {
        "intent_generalization_validated": valide,
        "total": total,
        "intent_accuracy": intention_accuracy,
        "route_accuracy": route_accuracy,
        "minimum_group_accuracy": minimum_groupe,
        "unsafe_false_executions": fausses_executions,
        "criteria": CRITERES,
        "groups": groupe_stats,
        "failures": echecs,
    }


def main() -> int:
    resultat = executer()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0 if resultat["intent_generalization_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
