"""Barrière V0.17 : apprentissage actif naturel et sans promotion."""

from __future__ import annotations

from kairos import ApprentissageActif, Kernel
from kairos.memory import MemoryRepository


def main() -> int:
    repository = MemoryRepository(":memory:")
    kernel = Kernel(cognitive_repository=repository)
    checks: dict[str, bool] = {}

    question = kernel.traiter("c'est quoi un xylophore ?")
    checks["unknown_opens_question"] = question.question_id is not None
    checks["question_is_useful"] = (
        "Explique-le naturellement" in question.reponse
        and "à quoi sert-il" in question.reponse
    )

    experience = kernel.repondre_a(
        str(question.question_id),
        "un xylophore est un instrument musical",
    )
    info = experience.resolution.get("hypothesis", {})
    hypothesis_id = str(info.get("id", ""))
    checks["answer_creates_hypothesis"] = bool(hypothesis_id)
    checks["candidate_only"] = bool(
        repository.hypothesis(hypothesis_id)
        and repository.hypothesis(hypothesis_id)["status"] == "candidate"
    )

    engine = ApprentissageActif(repository)
    start = engine.demarrer(hypothesis_id)
    checks["initial_link_created"] = bool(
        start.liens_crees
        and start.liens_crees[0]["relation"] == "est_un"
        and start.liens_crees[0]["target"] == "instrument musical"
    )
    checks["no_redundant_relation_question"] = bool(
        start.question
        and start.question.champ == "examples"
        and start.question.gain_attendu == 25
    )

    examples = engine.recevoir("xylophone, marimba, balafon")
    checks["counterexample_question_next"] = bool(
        examples.question
        and examples.question.champ == "counterexamples"
        and examples.question.gain_attendu == 20
    )
    counterexamples = engine.recevoir("piano, guitare")
    checks["source_question_next"] = bool(
        counterexamples.question
        and counterexamples.question.champ == "source"
        and counterexamples.question.gain_attendu == 15
    )
    final = engine.recevoir("cherche toi-même")
    hypothesis = repository.hypothesis(hypothesis_id)
    payload = hypothesis["payload"]
    checks["ready_for_research"] = final.statut == "ready_for_research"
    checks["three_examples"] = len(payload.get("examples", [])) == 3
    checks["two_counterexamples"] = len(payload.get("counterexamples", [])) == 2
    checks["self_research_route"] = (
        payload.get("source_strategy") == "self_research"
        and "route:information.search" in payload.get("source_leads", [])
    )
    checks["truth_checks_still_missing"] = all(
        item in payload.get("missing", [])
        for item in ("sources", "tests", "validation_secau")
    )
    checks["zero_promotion"] = (
        hypothesis["status"] == "candidate"
        and repository.search({"text": "xylophore"}) == []
    )
    status = engine.statut()
    checks["status_observable"] = (
        status["active"] is False
        and status["candidates"][0]["structure_score"] == 100
    )

    other_id = repository.add_hypothesis(
        {
            "created_from_experience_id": "experience_bounded",
            "name": "notionopaque",
            "definition": "explication sans structure relationnelle",
            "score": 30,
            "evidence_ids": [],
            "examples": [],
            "counterexamples": [],
        }
    )
    engine.demarrer(other_id)
    retry = engine.recevoir("ça dépend")
    blocked_forward = engine.recevoir("toujours impossible à relier")
    checks["one_relation_retry_only"] = bool(
        retry.question
        and retry.question.tentative == 2
        and blocked_forward.question
        and blocked_forward.question.champ == "examples"
    )

    engine.recevoir("exemple un, exemple deux, exemple trois")
    engine.recevoir("contre un, contre deux")
    ended = engine.recevoir("passe")
    other = repository.hypothesis(other_id)
    checks["missing_link_not_ready"] = (
        ended.statut == "needs_human_input"
        and other["payload"]["next_action"] == "await_creator"
    )
    checks["audit_complete"] = all(
        name in {event["event"] for event in repository.audit_events()}
        for name in (
            "ACTIVE_LEARNING_STARTED",
            "ACTIVE_LEARNING_QUESTION_ASKED",
            "ACTIVE_LEARNING_ANSWER_ACCEPTED",
            "ACTIVE_LEARNING_STRUCTURED",
            "ACTIVE_LEARNING_BLOCKED",
        )
    )
    checks["no_confirmed_concepts"] = repository.cognitive_counts()["concepts"] == 0

    total = len(checks)
    passed = sum(checks.values())
    print(f"ACTIVE_LEARNING_BENCHMARK: {passed}/{total}")
    print(f"USEFUL_QUESTION_RATE: {100 if checks['question_is_useful'] else 0}%")
    print(f"AUTONOMOUS_LINKS_CREATED: {len(start.liens_crees)}")
    print(f"FALSE_PROMOTIONS: {0 if checks['zero_promotion'] else 1}")
    print(f"UNBOUNDED_CLARIFICATIONS: {0 if checks['one_relation_retry_only'] else 1}")
    for name, ok in checks.items():
        if not ok:
            print(f"FAILED: {name}")
    repository.close()
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
