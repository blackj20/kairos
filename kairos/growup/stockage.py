"""Registre SQLite des groupes, plans et exécutions GrowUp."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .modeles import GroupeApprentissage, PlanApprentissage


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


class StockageGrowUp:
    """Trace les décisions de GrowUp sans toucher aux épisodes sources."""

    TERMINAUX = {"promoted", "rejected", "quarantined"}

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._creer_schema()

    def _creer_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS growup_groups (
              id TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS growup_plans (
              id TEXT PRIMARY KEY,
              group_id TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(group_id) REFERENCES growup_groups(id)
            );
            CREATE TABLE IF NOT EXISTS growup_runs (
              id TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS growup_audit (
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

    def sauvegarder_groupe(self, groupe: GroupeApprentissage) -> None:
        payload = groupe.vers_dict()
        maintenant = _maintenant()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO growup_groups VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     payload_json=excluded.payload_json,
                     updated_at=excluded.updated_at""",
                (groupe.id, json.dumps(payload, ensure_ascii=False), maintenant),
            )
            self._audit(db, "GROUP_SCANNED", {"group_id": groupe.id})

    def sauvegarder_plan(self, plan: PlanApprentissage) -> PlanApprentissage:
        existant = self.connection.execute(
            "SELECT status FROM growup_plans WHERE id=?", (plan.id,)
        ).fetchone()
        statut = (
            str(existant["status"])
            if existant is not None and existant["status"] in self.TERMINAUX
            else plan.statut
        )
        payload = {**plan.vers_dict(), "statut": statut}
        maintenant = _maintenant()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO growup_plans
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     payload_json=excluded.payload_json,
                     status=excluded.status,
                     updated_at=excluded.updated_at""",
                (
                    plan.id,
                    plan.groupe_id,
                    json.dumps(payload, ensure_ascii=False),
                    statut,
                    maintenant,
                    maintenant,
                ),
            )
            self._audit(
                db,
                "PLAN_SAVED",
                {"plan_id": plan.id, "group_id": plan.groupe_id, "status": statut},
            )
        return PlanApprentissage.depuis_dict(payload)

    def sauvegarder_run(self, run_id: str, payload: dict[str, Any]) -> None:
        with self.transaction() as db:
            db.execute(
                "INSERT INTO growup_runs VALUES (?, ?, ?)",
                (run_id, json.dumps(payload, ensure_ascii=False), _maintenant()),
            )
            self._audit(db, "GROWUP_RUN_RECORDED", {"run_id": run_id})

    def groupe(self, groupe_id: str) -> GroupeApprentissage | None:
        row = self.connection.execute(
            "SELECT payload_json FROM growup_groups WHERE id=?", (groupe_id,)
        ).fetchone()
        if row is None:
            return None
        return GroupeApprentissage.depuis_dict(json.loads(row["payload_json"]))

    def plan(self, plan_id: str) -> PlanApprentissage | None:
        row = self.connection.execute(
            "SELECT payload_json, status FROM growup_plans WHERE id=?", (plan_id,)
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["statut"] = row["status"]
        return PlanApprentissage.depuis_dict(payload)

    def plans(self, statut: str | None = None) -> tuple[PlanApprentissage, ...]:
        sql = "SELECT payload_json, status FROM growup_plans"
        params: tuple[Any, ...] = ()
        if statut is not None:
            sql += " WHERE status=?"
            params = (statut,)
        sql += " ORDER BY updated_at DESC"
        resultats: list[PlanApprentissage] = []
        for row in self.connection.execute(sql, params):
            payload = json.loads(row["payload_json"])
            payload["statut"] = row["status"]
            resultats.append(PlanApprentissage.depuis_dict(payload))
        return tuple(resultats)

    def changer_statut_plan(
        self,
        plan_id: str,
        statut: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        plan = self.plan(plan_id)
        if plan is None:
            raise KeyError(plan_id)
        payload = {**plan.vers_dict(), "statut": statut}
        with self.transaction() as db:
            db.execute(
                """UPDATE growup_plans
                   SET payload_json=?, status=?, updated_at=? WHERE id=?""",
                (
                    json.dumps(payload, ensure_ascii=False),
                    statut,
                    _maintenant(),
                    plan_id,
                ),
            )
            self._audit(
                db,
                "PLAN_STATUS_CHANGED",
                {"plan_id": plan_id, "status": statut, "details": details or {}},
            )

    def runs(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "id": row["id"],
                **json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in self.connection.execute(
                "SELECT * FROM growup_runs ORDER BY created_at"
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
                "SELECT * FROM growup_audit ORDER BY sequence"
            )
        )

    @staticmethod
    def _audit(db: sqlite3.Connection, event: str, payload: dict[str, Any]) -> None:
        db.execute(
            "INSERT INTO growup_audit(event, payload_json, created_at) VALUES (?, ?, ?)",
            (event, json.dumps(payload, ensure_ascii=False), _maintenant()),
        )

    def close(self) -> None:
        self.connection.close()
