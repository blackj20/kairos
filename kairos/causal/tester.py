"""Tester spécialisé pour les hypothèses d'amélioration comportementale."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..memory import MemoryRepository


@dataclass(frozen=True, slots=True)
class RapportTestCausal:
    subject_id: str
    passed: bool
    tested_episodes: int
    baseline_success_rate: int
    candidate_success_rate: int
    improvement: int
    regressions: int
    missing: tuple[str, ...]

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


class TesterCausal:
    """Mesure une amélioration sur des épisodes inconnus et observés."""

    MIN_EPISODES = 5
    MIN_SUCCESS_RATE = 85

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def tester(self, hypothesis_id: str) -> tuple[str, RapportTestCausal]:
        hypothesis = self.repository.hypothesis(hypothesis_id)
        if hypothesis is None:
            raise KeyError(hypothesis_id)
        payload = dict(hypothesis["payload"])
        if payload.get("causal_kind") != "behavior.change":
            raise ValueError("Hypothèse étrangère au test causal.")
        samples = [
            dict(item)
            for item in payload.get("samples", [])
            if isinstance(item, dict)
            and bool(item.get("observed"))
            and bool(item.get("unseen"))
            and item.get("episode_id")
        ]
        total = len(samples)
        baseline = sum(bool(item.get("baseline_success")) for item in samples)
        candidate = sum(bool(item.get("candidate_success")) for item in samples)
        baseline_rate = round(100 * baseline / total) if total else 0
        candidate_rate = round(100 * candidate / total) if total else 0
        regressions = sum(
            bool(item.get("baseline_success"))
            and not bool(item.get("candidate_success"))
            for item in samples
        )
        missing: list[str] = []
        if total < self.MIN_EPISODES:
            missing.append("cinq épisodes inconnus observés")
        if candidate_rate < self.MIN_SUCCESS_RATE:
            missing.append("85 % de réussite après correction")
        if candidate_rate <= baseline_rate:
            missing.append("amélioration mesurable")
        if regressions:
            missing.append("zéro régression")
        report = RapportTestCausal(
            subject_id=hypothesis_id,
            passed=not missing,
            tested_episodes=total,
            baseline_success_rate=baseline_rate,
            candidate_success_rate=candidate_rate,
            improvement=candidate_rate - baseline_rate,
            regressions=regressions,
            missing=tuple(missing),
        )
        report_id = self.repository.save_report(
            hypothesis_id, report.vers_dict()
        )
        return report_id, report
