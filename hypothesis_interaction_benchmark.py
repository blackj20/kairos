"""Barrière V0.16 pour les hypothèses issues des interactions."""

from __future__ import annotations

from kairos import Kernel
from kairos.decision import EvenementExperience
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

    noun_experience = EvenementExperience(
        id="experience_noun",
        question_id="question_noun",
        requete_originale="c'est quoi un xylophore ?",
        question="Je ne connais pas encore le sens de « xylophore » ici.",
        reponse="un xylophore est un instrument musical en bois",
        champ="sens",
        resolution={
            "field": "sens",
            "value": "un instrument musical en bois",
            "status": "hypothesis",
        },
        analyse_reponse={"jetons_inconnus": []},
        statut="recorded_not_confirmed",
        cree_le="2026-07-30T00:00:00+00:00",
    )
    noun_result = kernel.hypotheses.depuis_experience(
        noun_experience,
        acteur="creator",
    )
    noun_info = noun_result.vers_dict()
    noun_hypothesis = repository.hypothesis(noun_result.id)
    checks["noun_named_from_question"] = noun_info.get("nom") == "xylophore"
    checks["noun_is_explanation"] = bool(
        noun_hypothesis
        and noun_hypothesis["payload"].get("learning_kind")
        == "interaction.user_explanation"
    )
    checks["noun_not_verb_equivalence"] = bool(
        noun_hypothesis
        and "relation_candidate" not in noun_hypothesis["payload"]
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
    checks["expected_candidates"] = len(repository.candidate_hypotheses()) == 2
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
