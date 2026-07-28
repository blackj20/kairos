"""Évaluation secondaire rédigée après le premier passage d'implémentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kairos import Kernel


def executer_holdout(chemin: Path | None = None) -> dict[str, Any]:
    racine = Path(__file__).resolve().parent
    chemin = chemin or racine / "benchmarks" / "holdout.json"
    with chemin.open("r", encoding="utf-8") as fichier:
        corpus = json.load(fichier)

    kernel = Kernel()
    echecs: list[dict[str, Any]] = []
    intention_correcte = 0
    route_correcte = 0
    fausses_executions = 0

    for cas in corpus["cases"]:
        decision = kernel.traiter(cas["text"])
        type_obtenu = decision.analyse.type_requete.valeur
        if type_obtenu == cas["expected_type"]:
            intention_correcte += 1
        if decision.route == cas["expected_route"]:
            route_correcte += 1
        if (
            decision.route == "competence"
            and cas["expected_route"] != "competence"
        ):
            fausses_executions += 1
        if (
            type_obtenu != cas["expected_type"]
            or decision.route != cas["expected_route"]
        ):
            echecs.append(
                {
                    "text": cas["text"],
                    "expected_type": cas["expected_type"],
                    "obtained_type": type_obtenu,
                    "expected_route": cas["expected_route"],
                    "obtained_route": decision.route,
                }
            )

    total = len(corpus["cases"])
    return {
        "total": total,
        "intention_accuracy": round(100 * intention_correcte / total, 2),
        "route_accuracy": round(100 * route_correcte / total, 2),
        "unsafe_false_executions": fausses_executions,
        "failures": echecs,
    }


def main() -> None:
    print(json.dumps(executer_holdout(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
