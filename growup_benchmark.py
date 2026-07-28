"""Benchmark holdout du regroupement et de la traçabilité GrowUp."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from kairos.growup import ObservationApprentissage, Regroupement


def executer_benchmark(chemin: Path | None = None) -> dict[str, Any]:
    racine = Path(__file__).resolve().parent
    chemin = chemin or racine / "benchmarks" / "growup.json"
    corpus = json.loads(chemin.read_text(encoding="utf-8"))
    items = corpus["observations"]
    observations = tuple(
        ObservationApprentissage(
            id=item["id"],
            source_type=item["source_type"],
            requete=item["requete"],
            champ=item["champ"],
            focus=item.get("focus"),
            occurrences=int(item.get("occurrences", 1)),
            resolution=dict(item.get("resolution", {})),
        )
        for item in items
    )
    groupes = Regroupement().regrouper(observations)

    affectations: dict[str, list[str]] = {item["id"]: [] for item in items}
    groupes_par_id = {groupe.id: groupe for groupe in groupes}
    for groupe in groupes:
        for observation_id in groupe.observation_ids:
            affectations.setdefault(observation_id, []).append(groupe.id)

    total_paires = 0
    paires_correctes = 0
    clusters = {item["id"]: item["cluster"] for item in items}
    for gauche, droite in itertools.combinations(items, 2):
        total_paires += 1
        meme_attendu = gauche["cluster"] == droite["cluster"]
        groupes_gauche = affectations.get(gauche["id"], [])
        groupes_droite = affectations.get(droite["id"], [])
        meme_obtenu = (
            len(groupes_gauche) == 1
            and len(groupes_droite) == 1
            and groupes_gauche[0] == groupes_droite[0]
        )
        if meme_attendu == meme_obtenu:
            paires_correctes += 1

    pairwise = 100.0 * paires_correctes / total_paires if total_paires else 100.0
    traces_correctes = sum(
        1 for item in items if len(affectations.get(item["id"], [])) == 1
    )
    traceability = 100.0 * traces_correctes / len(items) if items else 100.0

    occurrences_correctes = 0
    details_occurrences: list[dict[str, Any]] = []
    for cluster, attendu in corpus["expected_occurrences"].items():
        ids = [item["id"] for item in items if item["cluster"] == cluster]
        groupes_cluster = {
            affectations[item_id][0]
            for item_id in ids
            if len(affectations.get(item_id, [])) == 1
        }
        obtenu = None
        if len(groupes_cluster) == 1:
            obtenu = groupes_par_id[next(iter(groupes_cluster))].occurrences
        correct = obtenu == attendu
        occurrences_correctes += int(correct)
        details_occurrences.append(
            {"cluster": cluster, "expected": attendu, "obtained": obtenu, "ok": correct}
        )
    occurrence_accuracy = (
        100.0 * occurrences_correctes / len(corpus["expected_occurrences"])
    )

    criteres = corpus["criteria"]
    groupe_count_ok = len(groupes) == criteres["expected_group_count"]
    valide = (
        pairwise >= criteres["pairwise_grouping_accuracy_min"]
        and traceability >= criteres["traceability_accuracy_min"]
        and occurrence_accuracy >= criteres["occurrence_accuracy_min"]
        and groupe_count_ok
    )
    return {
        "growup_validated": valide,
        "observations": len(items),
        "groups": len(groupes),
        "pairwise_grouping_accuracy": round(pairwise, 2),
        "traceability_accuracy": round(traceability, 2),
        "occurrence_accuracy": round(occurrence_accuracy, 2),
        "group_count_ok": groupe_count_ok,
        "criteria": criteres,
        "occurrence_details": details_occurrences,
        "clusters": clusters,
    }


def main() -> None:
    resultat = executer_benchmark()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    if not resultat["growup_validated"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
