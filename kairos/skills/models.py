"""Contrats immuables du cycle candidate → validation → activation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    """Candidate générée depuis un plan GrowUp promu."""

    id: str
    skill_id: str
    version: str
    plan_id: str
    group_id: str
    path: str
    digest: str
    status: str
    created_at: str

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, payload: dict[str, Any]) -> "CandidateRecord":
        return cls(
            id=str(payload["id"]),
            skill_id=str(payload["skill_id"]),
            version=str(payload["version"]),
            plan_id=str(payload["plan_id"]),
            group_id=str(payload["group_id"]),
            path=str(payload["path"]),
            digest=str(payload["digest"]),
            status=str(payload["status"]),
            created_at=str(payload["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Rapport lié cryptographiquement à une version candidate."""

    id: str
    candidate_id: str
    skill_id: str
    version: str
    digest: str
    passed: bool
    manifest_valid: bool
    permissions_valid: bool
    scan_passed: bool
    tests_passed: bool
    violations: tuple[str, ...]
    created_at: str
    details: dict[str, Any] = field(default_factory=dict)

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, payload: dict[str, Any]) -> "ValidationReport":
        return cls(
            id=str(payload["id"]),
            candidate_id=str(payload["candidate_id"]),
            skill_id=str(payload["skill_id"]),
            version=str(payload["version"]),
            digest=str(payload["digest"]),
            passed=bool(payload["passed"]),
            manifest_valid=bool(payload["manifest_valid"]),
            permissions_valid=bool(payload["permissions_valid"]),
            scan_passed=bool(payload["scan_passed"]),
            tests_passed=bool(payload["tests_passed"]),
            violations=tuple(payload.get("violations", ())),
            created_at=str(payload["created_at"]),
            details=dict(payload.get("details", {})),
        )


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Résultat d'une activation humaine et réversible."""

    skill_id: str
    version: str
    report_id: str
    digest: str
    active_path: str
    approved_by: str
    previous_version: str | None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
