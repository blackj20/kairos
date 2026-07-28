"""Mesure reproductible d'un candidat."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..memory import MemoryRepository


class Tester:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    @staticmethod
    def _run_case(case: Callable[[], bool]) -> tuple[bool, str | None]:
        """Transforme une exception de test en échec explicite et traçable."""

        try:
            return bool(case()), None
        except Exception as error:  # Le rapport doit survivre à un cas défectueux.
            return False, f"{type(error).__name__}: {error}"

    def test(
        self,
        subject_id: str,
        original: Callable[[], bool],
        paraphrases: Iterable[Callable[[], bool]],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> tuple[str, dict[str, Any]]:
        original_ok, original_error = self._run_case(original)
        paraphrase_runs = [self._run_case(case) for case in paraphrases]
        regression_runs = [self._run_case(case) for case in regressions]
        paraphrase_results = [result for result, _ in paraphrase_runs]
        regression_results = [result for result, _ in regression_runs]
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
            "errors": {
                "original": original_error,
                "paraphrases": [error for _, error in paraphrase_runs],
                "regressions": [error for _, error in regression_runs],
            },
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

        def resolve(case: str) -> tuple[str | None, str | None]:
            try:
                return resolver(case), None
            except Exception as error:
                return None, f"{type(error).__name__}: {error}"

        positive_runs = [resolve(case) for case in examples]
        negative_runs = [resolve(case) for case in counterexamples]
        positive_results = [value == target for value, _ in positive_runs]
        negative_results = [value != target and error is None for value, error in negative_runs]
        regression_runs = [self._run_case(case) for case in regressions]
        regression_results = [result for result, _ in regression_runs]
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
            "errors": {
                "examples": [error for _, error in positive_runs],
                "counterexamples": [error for _, error in negative_runs],
                "regressions": [error for _, error in regression_runs],
            },
        }
        return self.repository.save_report(subject_id, report), report
