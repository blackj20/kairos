"""Audit final avant promotion."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..memory import MemoryRepository


class SecauVerdict(str, Enum):
    PROMOTE = "promote"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


@dataclass(frozen=True)
class SecauResult:
    verdict: SecauVerdict
    reason: str
    concept_id: str | None = None


class Secau:
    PROTECTED = {"identity", "objective", "permissions", "security_policy", "creator"}

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def review(
        self, hypothesis_id: str, report_id: str, payload: dict[str, Any]
    ) -> SecauResult:
        if self.PROTECTED.intersection(payload):
            return SecauResult(SecauVerdict.QUARANTINE, "donnée protégée")
        if not payload.get("evidence_ids"):
            return SecauResult(
                SecauVerdict.NEEDS_MORE_EVIDENCE, "provenance absente"
            )
        try:
            concept_id = self.repository.promote(hypothesis_id, report_id)
        except ValueError as error:
            return SecauResult(SecauVerdict.REJECT, str(error))
        return SecauResult(SecauVerdict.PROMOTE, "contrôles réussis", concept_id)

    def review_relation(
        self,
        hypothesis_id: str,
        report_id: str,
    ) -> SecauResult:
        """Applique les portes SECAU propres aux relations sémantiques."""

        hypothesis = self.repository.hypothesis(hypothesis_id)
        report = self.repository.report(report_id)
        if hypothesis is None or report is None:
            return SecauResult(SecauVerdict.REJECT, "artefact absent")
        payload = hypothesis["payload"]
        if self.PROTECTED.intersection(payload):
            return SecauResult(SecauVerdict.QUARANTINE, "donnée protégée")
        if len(payload.get("evidence_ids", [])) < 2:
            return SecauResult(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "deux preuves indépendantes sont obligatoires",
            )
        if not report["passed"]:
            return SecauResult(SecauVerdict.REJECT, "tests relationnels échoués")
        try:
            relation_id = self.repository.promote_relation(
                hypothesis_id,
                report_id,
            )
        except ValueError as error:
            return SecauResult(SecauVerdict.REJECT, str(error))
        return SecauResult(
            SecauVerdict.PROMOTE,
            "relation confirmée après preuves, exemples et régression",
            relation_id,
        )
