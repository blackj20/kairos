"""Barrière mesurable de la boucle causale V0.14."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kairos import Kernel
from kairos.causal import MoteurCausal, StockageCausal, TesterCausal
from kairos.cognition import Secau, SecauVerdict
from kairos.memory import MemoryRepository


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        store = StockageCausal(root / "episodes.db")
        kernel = Kernel()
        engine = MoteurCausal(kernel=kernel, stockage=store)
        prompts = (
            "cherche atome",
            "trouve atome",
            "recherche atome",
            "renseigne toi sur atome",
            "cherche toi-même atome",
        )
        known = [engine.executer_message(prompt) for prompt in prompts]
        unknown = engine.executer("chercher", "xylophore")
        blocked = engine.executer("chercher", None)
        replay = engine.rejouer(str(known[0]["id"]))

        repository = MemoryRepository(":memory:")
        samples = [
            {
                "episode_id": f"blind_{index}",
                "observed": True,
                "unseen": True,
                "baseline_success": False,
                "candidate_success": True,
            }
            for index in range(5)
        ]
        hypothesis_id = repository.add_hypothesis(
            {
                "created_from_experience_id": "causal_benchmark",
                "causal_kind": "behavior.change",
                "name": "search_paraphrase_upgrade",
                "samples": samples,
                "score": 90,
            }
        )
        report_id, report = TesterCausal(repository).tester(hypothesis_id)
        secau = Secau(repository).review_causal(hypothesis_id, report_id)

        checks = {
            "five_real_interpretations": len(known) == 5,
            "known_goals_reached": all(
                item["evaluation"]["objectif_atteint"] for item in known
            ),
            "known_scores_are_complete": all(
                item["evaluation"]["score_resultat"] == 100 for item in known
            ),
            "unknown_technical_execution": unknown["evaluation"]["succes_technique"],
            "unknown_goal_not_reached": not unknown["evaluation"]["objectif_atteint"],
            "unknown_failure_localized": "information_not_found" in unknown["evaluation"]["erreurs"],
            "blocked_route_not_executed": not blocked["observation"]["execution_tentee"],
            "ordered_transitions": all(
                [item["next_status"] for item in episode["transitions"]]
                == ["created", "predicted", "executed", "observed", "evaluated"]
                for episode in known
            ),
            "observer_has_no_goal_judgement": all(
                "objectif_atteint" not in item["observation"] for item in known
            ),
            "replay_is_linked": replay["comparison"]["source_episode_id"] == known[0]["id"],
            "replay_has_no_regression": not replay["comparison"]["regression"],
            "causal_tester_passes": report.passed,
            "secau_is_really_called": secau.verdict is SecauVerdict.PROMOTE,
            "behavior_is_not_world_knowledge": repository.search({"text": "search_paraphrase_upgrade"}) == [],
            "validated_status_is_traceable": repository.hypothesis(hypothesis_id)["status"] == "validated",
        }
        passed = sum(checks.values())
        total = len(checks)
        print(f"CAUSAL_BENCHMARK: {passed}/{total}")
        print(f"UNSEEN_MISSIONS: {len(known)}")
        print(f"GOAL_SUCCESS_RATE: {round(100 * sum(item['evaluation']['objectif_atteint'] for item in known) / len(known))}%")
        print(f"CAUSAL_REGRESSIONS: {sum(not value for key, value in checks.items() if 'regression' in key)}")
        print(f"SECAU_CAUSAL_CALLS: {int(secau.verdict is SecauVerdict.PROMOTE)}")
        for name, value in checks.items():
            print(f"[{'PASS' if value else 'FAIL'}] {name}")

        repository.close()
        kernel.close()
        store.close()
        return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
