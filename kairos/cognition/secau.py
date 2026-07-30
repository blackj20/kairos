"""Audit final observable avant promotion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
    hypothesis_id: str | None = None
    report_id: str | None = None

    def vers_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload


class Secau:
    PROTECTED = {"identity", "objective", "permissions", "security_policy", "creator"}

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    @staticmethod
    def _report_matches_subject(report: dict[str, Any], subject_id: str) -> bool:
        """Empêche qu'un rapport réussi pour A valide par erreur le candidat B."""

        return str(report.get("subject_id", "")) == subject_id

    def _resultat(
        self,
        verdict: SecauVerdict,
        raison: str,
        hypothesis_id: str,
        report_id: str | None,
        concept_id: str | None = None,
    ) -> SecauResult:
        resultat = SecauResult(
            verdict=verdict,
            reason=raison,
            concept_id=concept_id,
            hypothesis_id=hypothesis_id,
            report_id=report_id,
        )
        self.repository.record_audit(
            "SECAU_REVIEWED",
            {
                "hypothesis": hypothesis_id,
                "report": report_id,
                "verdict": verdict.value,
                "reason": raison,
                "concept": concept_id,
            },
        )
        return resultat

    def review(
        self, hypothesis_id: str, report_id: str, payload: dict[str, Any]
    ) -> SecauResult:
        hypothesis = self.repository.hypothesis(hypothesis_id)
        report = self.repository.report(report_id)
        if hypothesis is None or report is None:
            return self._resultat(
                SecauVerdict.REJECT, "artefact absent", hypothesis_id, report_id
            )
        if hypothesis.get("status") != "candidate":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse déjà traitée",
                hypothesis_id,
                report_id,
            )
        if not self._report_matches_subject(report, hypothesis_id):
            return self._resultat(
                SecauVerdict.REJECT,
                "le rapport de test ne correspond pas à cette hypothèse",
                hypothesis_id,
                report_id,
            )
        if not bool(report.get("passed")):
            return self._resultat(
                SecauVerdict.REJECT,
                "tests échoués",
                hypothesis_id,
                report_id,
            )
        if self.PROTECTED.intersection(payload):
            return self._resultat(
                SecauVerdict.QUARANTINE,
                "donnée protégée",
                hypothesis_id,
                report_id,
            )
        if not payload.get("evidence_ids"):
            return self._resultat(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "provenance absente",
                hypothesis_id,
                report_id,
            )
        try:
            concept_id = self.repository.promote(hypothesis_id, report_id)
        except ValueError as error:
            return self._resultat(
                SecauVerdict.REJECT,
                str(error),
                hypothesis_id,
                report_id,
            )
        return self._resultat(
            SecauVerdict.PROMOTE,
            "contrôles réussis",
            hypothesis_id,
            report_id,
            concept_id,
        )

    def review_research(
        self,
        hypothesis_id: str,
        report_id: str | None,
        dossier: dict[str, Any],
    ) -> SecauResult:
        """Décide sur un concept recherché sans confondre cohérence et vérité."""

        hypothesis = self.repository.hypothesis(hypothesis_id)
        if hypothesis is None:
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse de recherche absente",
                hypothesis_id,
                report_id,
            )
        if hypothesis.get("status") != "candidate":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse déjà traitée",
                hypothesis_id,
                report_id,
            )
        payload = hypothesis["payload"]
        if payload.get("research_kind") != "information.search":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse étrangère à la recherche d'information",
                hypothesis_id,
                report_id,
            )
        if self.PROTECTED.intersection(payload):
            return self._resultat(
                SecauVerdict.QUARANTINE,
                "donnée protégée",
                hypothesis_id,
                report_id,
            )
        missing = tuple(dossier.get("missing", ()))
        if missing:
            return self._resultat(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "preuves insuffisantes : " + ", ".join(str(item) for item in missing),
                hypothesis_id,
                report_id,
            )
        if report_id is None:
            return self._resultat(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "rapport Tester absent",
                hypothesis_id,
                report_id,
            )
        report = self.repository.report(report_id)
        if report is None or not self._report_matches_subject(
            report, hypothesis_id
        ):
            return self._resultat(
                SecauVerdict.REJECT,
                "rapport Tester absent ou associé à une autre hypothèse",
                hypothesis_id,
                report_id,
            )
        if not bool(report.get("passed")):
            return self._resultat(
                SecauVerdict.REJECT,
                "contrôles de recherche échoués",
                hypothesis_id,
                report_id,
            )
        try:
            concept_id = self.repository.promote(hypothesis_id, report_id)
        except ValueError as error:
            return self._resultat(
                SecauVerdict.REJECT,
                str(error),
                hypothesis_id,
                report_id,
            )
        return self._resultat(
            SecauVerdict.PROMOTE,
            "concept confirmé après sources indépendantes et Tester",
            hypothesis_id,
            report_id,
            concept_id,
        )

    def review_causal(
        self,
        hypothesis_id: str,
        report_id: str,
    ) -> SecauResult:
        """Valide une amélioration mesurée sans la confondre avec une vérité."""

        hypothesis = self.repository.hypothesis(hypothesis_id)
        report = self.repository.report(report_id)
        if hypothesis is None or report is None:
            return self._resultat(
                SecauVerdict.REJECT,
                "artefact causal absent",
                hypothesis_id,
                report_id,
            )
        if hypothesis.get("status") != "candidate":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse causale déjà traitée",
                hypothesis_id,
                report_id,
            )
        if not self._report_matches_subject(report, hypothesis_id):
            return self._resultat(
                SecauVerdict.REJECT,
                "le rapport causal appartient à une autre hypothèse",
                hypothesis_id,
                report_id,
            )
        payload = dict(hypothesis["payload"])
        if payload.get("causal_kind") != "behavior.change":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse étrangère à l'expérience causale",
                hypothesis_id,
                report_id,
            )
        if self.PROTECTED.intersection(payload):
            return self._resultat(
                SecauVerdict.QUARANTINE,
                "donnée protégée",
                hypothesis_id,
                report_id,
            )
        donnees = dict(report.get("report") or {})
        if int(donnees.get("tested_episodes", 0)) < 5:
            return self._resultat(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "cinq épisodes inconnus observés sont obligatoires",
                hypothesis_id,
                report_id,
            )
        if not bool(report.get("passed")):
            return self._resultat(
                SecauVerdict.REJECT,
                "le changement n'améliore pas les résultats",
                hypothesis_id,
                report_id,
            )
        if int(donnees.get("improvement", 0)) <= 0:
            return self._resultat(
                SecauVerdict.REJECT,
                "aucune amélioration mesurée",
                hypothesis_id,
                report_id,
            )
        if int(donnees.get("regressions", 0)) != 0:
            return self._resultat(
                SecauVerdict.REJECT,
                "régression causale détectée",
                hypothesis_id,
                report_id,
            )
        try:
            self.repository.validate_causal_hypothesis(
                hypothesis_id, report_id
            )
        except ValueError as error:
            return self._resultat(
                SecauVerdict.REJECT,
                str(error),
                hypothesis_id,
                report_id,
            )
        return self._resultat(
            SecauVerdict.PROMOTE,
            "amélioration causale validée dans le laboratoire",
            hypothesis_id,
            report_id,
        )

    def review_relation(
        self,
        hypothesis_id: str,
        report_id: str,
    ) -> SecauResult:
        """Applique les portes SECAU propres aux relations sémantiques."""

        hypothesis = self.repository.hypothesis(hypothesis_id)
        report = self.repository.report(report_id)
        if hypothesis is None or report is None:
            return self._resultat(
                SecauVerdict.REJECT, "artefact absent", hypothesis_id, report_id
            )
        if hypothesis.get("status") != "candidate":
            return self._resultat(
                SecauVerdict.REJECT,
                "hypothèse déjà traitée",
                hypothesis_id,
                report_id,
            )
        if not self._report_matches_subject(report, hypothesis_id):
            return self._resultat(
                SecauVerdict.REJECT,
                "le rapport de test ne correspond pas à cette hypothèse",
                hypothesis_id,
                report_id,
            )
        payload = hypothesis["payload"]
        if self.PROTECTED.intersection(payload):
            return self._resultat(
                SecauVerdict.QUARANTINE,
                "donnée protégée",
                hypothesis_id,
                report_id,
            )
        if len(payload.get("evidence_ids", [])) < 2:
            return self._resultat(
                SecauVerdict.NEEDS_MORE_EVIDENCE,
                "deux preuves indépendantes sont obligatoires",
                hypothesis_id,
                report_id,
            )
        if not bool(report.get("passed")):
            return self._resultat(
                SecauVerdict.REJECT,
                "tests relationnels échoués",
                hypothesis_id,
                report_id,
            )
        try:
            relation_id = self.repository.promote_relation(
                hypothesis_id,
                report_id,
            )
        except ValueError as error:
            return self._resultat(
                SecauVerdict.REJECT,
                str(error),
                hypothesis_id,
                report_id,
            )
        return self._resultat(
            SecauVerdict.PROMOTE,
            "relation confirmée après preuves, exemples et régression",
            hypothesis_id,
            report_id,
            relation_id,
        )
