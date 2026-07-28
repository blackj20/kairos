"""Mesure reproductible d'un candidat."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..memory import MemoryRepository


class Tester:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def test(
        self,
        subject_id: str,
        original: Callable[[], bool],
        paraphrases: Iterable[Callable[[], bool]],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> tuple[str, dict[str, Any]]:
        original_ok = bool(original())
        paraphrase_results = [bool(case()) for case in paraphrases]
        regression_results = [bool(case()) for case in regressions]
        report = {
            "passed": (
                original_ok
                and len(paraphrase_results) >= 3
                and all(paraphrase_results)
                and all(regression_results)
            ),
            "original": original_ok,
            "paraphrases": paraphrase_results,
            "regressions": regression_results,
        }
        return self.repository.save_report(subject_id, report), report

    def test_relation(
        self,
        subject_id: str,
        candidate: dict[str, Any],
        resolver: Callable[[str], str | None],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> tuple[str, dict[str, Any]]:
        """Teste cas positifs, négatifs et régressions sans modifier le candidat."""

        target = str(candidate["target"])
        examples = list(candidate.get("examples", []))
        counterexamples = list(candidate.get("counterexamples", []))
        positive_results = [resolver(case) == target for case in examples]
        negative_results = [resolver(case) != target for case in counterexamples]
        regression_results = [bool(case()) for case in regressions]
        report = {
            "passed": (
                len(candidate.get("evidence_ids", [])) >= 2
                and len(examples) >= 3
                and len(counterexamples) >= 2
                and all(positive_results)
                and all(negative_results)
                and all(regression_results)
            ),
            "evidence_count": len(candidate.get("evidence_ids", [])),
            "examples": positive_results,
            "counterexamples": negative_results,
            "regressions": regression_results,
        }
        return self.repository.save_report(subject_id, report), report
