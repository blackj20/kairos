"""Barrière V0.16 pour les hypothèses issues des interactions."""

from __future__ import annotations

from kairos import Kernel
from kairos.hypotheses import GestionnaireHypotheses
from kairos.memory import MemoryRepository


def main() -> int:
    repository = MemoryRepository(":memory:")
    kernel = Kernel(cognitive_repository=repository)
    checks: dict[str, bool] = {}

    decision = kernel.traiter("deploie python")
    checks["question_created"] = decision.question_id is not None
    experience = kernel.repondre_a(str(decision.question_id), "installer")
    info = experience.resolution.get("hypothesis", {})
    hypothesis = repository.hypothesis(str(info.get("id", "")))
    checks["hypothesis_created"] = bool(info.get("creee"))
    checks["candidate_status"] = bool(
        hypothesis and hypothesis["status"] == "candidate"
    )
    checks["trace_to_experience"] = bool(
        hypothesis
        and hypothesis["created_from_experience_id"] == experience.id
    )
    checks["missing_visible"] = tuple(info.get("manques", ())) == (
        "sources",
        "tests",
        "validation_secau",
    )
    checks["no_promotion"] = repository.search({"text": "deploie"}) == []
    checks["no_lexicon_mutation"] = (
        kernel.comprendre.connaissances.relations_verbes.obtenir("deploie")
        is None
    )

    second = kernel.traiter("deploie docker")
    repeated = kernel.repondre_a(str(second.question_id), "installer")
    checks["candidate_reused"] = (
        repeated.resolution["hypothesis"]["id"] == info["id"]
        and not repeated.resolution["hypothesis"]["creee"]
    )

    target_question = kernel.traiter("installe")
    target = kernel.repondre_a(str(target_question.question_id), "python")
    checks["target_not_hypothesis"] = "hypothesis" not in target.resolution

    status = GestionnaireHypotheses(repository).statut(str(info["id"]))
    checks["status_readable"] = (
        status["hypothesis"]["id"] == info["id"]
        and status["missing"] == [
            "sources",
            "tests",
            "validation_secau",
        ]
    )
    checks["single_candidate"] = len(repository.candidate_hypotheses()) == 1
    checks["audit_trace"] = any(
        event["event"] == "HYPOTHESIS_CREATED"
        for event in repository.audit_events()
    )

    total = len(checks)
    passed = sum(checks.values())
    print(f"HYPOTHESIS_INTERACTION_BENCHMARK: {passed}/{total}")
    print(f"FALSE_HYPOTHESIS_PROMOTIONS: {0 if checks['no_promotion'] else 1}")
    print(
        "OPERATIONAL_ANSWERS_MISCLASSIFIED: "
        f"{0 if checks['target_not_hypothesis'] else 1}"
    )
    for name, ok in checks.items():
        if not ok:
            print(f"FAILED: {name}")
    repository.close()
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
