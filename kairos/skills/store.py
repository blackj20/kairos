"""Registre SQLite des candidates, rapports et audits de Skill Factory."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import CandidateRecord, ValidationReport


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillFactoryStore:
    """Persistance indépendante du registre des versions actives."""

    STATUTS = {
        "generated",
        "validated",
        "quarantined",
        "activated",
        "superseded",
        "archived",
    }

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._creer_schema()

    def _creer_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS skill_candidates (
              id TEXT PRIMARY KEY,
              skill_id TEXT NOT NULL,
              version TEXT NOT NULL,
              plan_id TEXT NOT NULL,
              group_id TEXT NOT NULL,
              digest TEXT NOT NULL,
              path TEXT NOT NULL,
              status TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(skill_id, version)
            );
            CREATE TABLE IF NOT EXISTS skill_reports (
              id TEXT PRIMARY KEY,
              candidate_id TEXT NOT NULL,
              digest TEXT NOT NULL,
              passed INTEGER NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(candidate_id) REFERENCES skill_candidates(id)
            );
            CREATE TABLE IF NOT EXISTS skill_factory_audit (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              event TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def save_candidate(self, candidate: CandidateRecord) -> CandidateRecord:
        if candidate.status not in self.STATUTS:
            raise ValueError(f"Statut candidate invalide : {candidate.status}")
        payload = candidate.vers_dict()
        now = _maintenant()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO skill_candidates
                   (id, skill_id, version, plan_id, group_id, digest, path,
                    status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate.id,
                    candidate.skill_id,
                    candidate.version,
                    candidate.plan_id,
                    candidate.group_id,
                    candidate.digest,
                    candidate.path,
                    candidate.status,
                    json.dumps(payload, ensure_ascii=False),
                    candidate.created_at,
                    now,
                ),
            )
            self._audit(
                db,
                "CANDIDATE_GENERATED",
                {
                    "candidate_id": candidate.id,
                    "skill_id": candidate.skill_id,
                    "version": candidate.version,
                    "digest": candidate.digest,
                    "plan_id": candidate.plan_id,
                },
            )
        return candidate

    def candidate(self, candidate_id: str) -> CandidateRecord | None:
        row = self.connection.execute(
            "SELECT payload_json, status FROM skill_candidates WHERE id=?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["status"] = row["status"]
        return CandidateRecord.depuis_dict(payload)

    def candidates(self, status: str | None = None) -> tuple[CandidateRecord, ...]:
        sql = "SELECT payload_json, status FROM skill_candidates"
        params: tuple[Any, ...] = ()
        if status is not None:
            sql += " WHERE status=?"
            params = (status,)
        sql += " ORDER BY created_at"
        resultats: list[CandidateRecord] = []
        for row in self.connection.execute(sql, params):
            payload = json.loads(row["payload_json"])
            payload["status"] = row["status"]
            resultats.append(CandidateRecord.depuis_dict(payload))
        return tuple(resultats)

    def change_candidate_status(
        self,
        candidate_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        if status not in self.STATUTS:
            raise ValueError(f"Statut candidate invalide : {status}")
        candidate = self.candidate(candidate_id)
        if candidate is None:
            raise KeyError(candidate_id)
        payload = {**candidate.vers_dict(), "status": status}
        with self.transaction() as db:
            db.execute(
                """UPDATE skill_candidates
                   SET status=?, payload_json=?, updated_at=? WHERE id=?""",
                (
                    status,
                    json.dumps(payload, ensure_ascii=False),
                    _maintenant(),
                    candidate_id,
                ),
            )
            self._audit(
                db,
                "CANDIDATE_STATUS_CHANGED",
                {
                    "candidate_id": candidate_id,
                    "status": status,
                    "details": details or {},
                },
            )

    def save_report(self, report: ValidationReport) -> ValidationReport:
        if self.candidate(report.candidate_id) is None:
            raise KeyError(report.candidate_id)
        with self.transaction() as db:
            db.execute(
                """INSERT INTO skill_reports
                   (id, candidate_id, digest, passed, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    report.id,
                    report.candidate_id,
                    report.digest,
                    int(report.passed),
                    json.dumps(report.vers_dict(), ensure_ascii=False),
                    report.created_at,
                ),
            )
            self._audit(
                db,
                "CANDIDATE_VALIDATED",
                {
                    "candidate_id": report.candidate_id,
                    "report_id": report.id,
                    "passed": report.passed,
                    "digest": report.digest,
                },
            )
        return report

    def report(self, report_id: str) -> ValidationReport | None:
        row = self.connection.execute(
            "SELECT payload_json FROM skill_reports WHERE id=?",
            (report_id,),
        ).fetchone()
        if row is None:
            return None
        return ValidationReport.depuis_dict(json.loads(row["payload_json"]))

    def reports(self, candidate_id: str) -> tuple[ValidationReport, ...]:
        return tuple(
            ValidationReport.depuis_dict(json.loads(row["payload_json"]))
            for row in self.connection.execute(
                """SELECT payload_json FROM skill_reports
                   WHERE candidate_id=? ORDER BY created_at""",
                (candidate_id,),
            )
        )

    def audit(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "event": row["event"],
                **json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in self.connection.execute(
                "SELECT * FROM skill_factory_audit ORDER BY sequence"
            )
        )

    @staticmethod
    def _audit(db: sqlite3.Connection, event: str, payload: dict[str, Any]) -> None:
        db.execute(
            """INSERT INTO skill_factory_audit
               (event, payload_json, created_at) VALUES (?, ?, ?)""",
            (event, json.dumps(payload, ensure_ascii=False), _maintenant()),
        )

    def close(self) -> None:
        self.connection.close()
