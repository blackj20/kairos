"""Benchmark reproductible de la couche de décision V0.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kairos import Kernel


def executer_decision_benchmark(chemin: Path | None = None) -> dict[str, Any]:
    racine = Path(__file__).resolve().parent
    chemin = chemin or racine / "benchmarks" / "decision.json"
    with chemin.open("r", encoding="utf-8") as fichier:
        corpus = json.load(fichier)

    routes_correctes = 0
    champs_corrects = 0
    questions_attendues = 0
    fausses_executions = 0
    ordres_incomplets = 0
    ordres_incomplets_bloques = 0
    echecs: list[dict[str, Any]] = []

    for cas in corpus["cases"]:
        kernel = Kernel()
        decision = kernel.traiter(cas["text"], acteur=cas.get("actor", "creator"))
        route_correcte = decision.route == cas["route"]
        if route_correcte:
            routes_correctes += 1

        champ_obtenu = None
        if decision.question_id:
            question = kernel.moteur_decision.stockage.obtenir_question(decision.question_id)
            champ_obtenu = question.champ_manquant if question else None

        champ_correct = True
        if "question_field" in cas:
            questions_attendues += 1
            champ_correct = champ_obtenu == cas["question_field"]
            if champ_correct:
                champs_corrects += 1

        route_interne_correcte = True
        if "internal_route" in cas:
            route_interne_correcte = decision.verdict["route"] == cas["internal_route"]

        if decision.route == "competence" and cas["route"] != "competence":
            fausses_executions += 1

        if cas.get("question_field") in {"action", "cible"} and cas["route"] == "clarification":
            ordres_incomplets += 1
            if decision.route != "competence":
                ordres_incomplets_bloques += 1

        if not (route_correcte and champ_correct and route_interne_correcte):
            echecs.append(
                {
                    "text": cas["text"],
                    "expected_route": cas["route"],
                    "obtained_route": decision.route,
                    "expected_field": cas.get("question_field"),
                    "obtained_field": champ_obtenu,
                    "expected_internal_route": cas.get("internal_route"),
                    "obtained_internal_route": decision.verdict["route"],
                }
            )

    total = len(corpus["cases"])
    route_accuracy = 100 * routes_correctes / total
    question_accuracy = (
        100 * champs_corrects / questions_attendues if questions_attendues else 100.0
    )
    blocage = (
        100 * ordres_incomplets_bloques / ordres_incomplets
        if ordres_incomplets
        else 100.0
    )
    criteres = corpus["criteria"]
    valide = (
        route_accuracy >= criteres["route_accuracy_min"]
        and question_accuracy >= criteres["question_field_accuracy_min"]
        and blocage >= criteres["incomplete_actions_blocked"]
        and fausses_executions <= criteres["unsafe_false_executions_max"]
    )

    return {
        "decision_layer_validated": valide,
        "total": total,
        "route_accuracy": round(route_accuracy, 2),
        "question_field_accuracy": round(question_accuracy, 2),
        "incomplete_actions_blocked": round(blocage, 2),
        "unsafe_false_executions": fausses_executions,
        "criteria": criteres,
        "failures": echecs,
    }


def main() -> int:
    resultat = executer_decision_benchmark()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0 if resultat["decision_layer_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
