"""Stockage SQLite des buts et journal append-only des événements."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .modeles import But, StatutBut, TypeEvenementBut


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StockageButs:
    TRANSITIONS = {
        StatutBut.PENDING: {
            StatutBut.ACTIVE,
            StatutBut.INVALIDATED,
            StatutBut.ABANDONED,
        },
        StatutBut.ACTIVE: {
            StatutBut.COMPLETED,
            StatutBut.BLOCKED,
            StatutBut.INVALIDATED,
            StatutBut.ABANDONED,
        },
    }

    def __init__(self, chemin: str | Path = ":memory:") -> None:
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(chemin))
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
              id TEXT PRIMARY KEY,
              mission TEXT NOT NULL,
              action TEXT,
              target TEXT,
              priority INTEGER NOT NULL,
              status TEXT NOT NULL,
              max_steps INTEGER NOT NULL,
              steps_used INTEGER NOT NULL DEFAULT 0,
              last_episode_id TEXT,
              last_reason TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goal_events (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              goal_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(goal_id) REFERENCES goals(id)
            );
            CREATE INDEX IF NOT EXISTS idx_goals_attention
              ON goals(status, priority DESC, updated_at ASC);
            """
        )
        self.connection.commit()

    def creer(
        self,
        mission: str,
        action: str | None,
        cible: str | None,
        *,
        priorite: int = 50,
        max_etapes: int = 3,
    ) -> But:
        mission = mission.strip()
        if not mission:
            raise ValueError("Un but exige une mission.")
        if not 0 <= priorite <= 100:
            raise ValueError("La priorité doit être comprise entre 0 et 100.")
        if not 1 <= max_etapes <= 20:
            raise ValueError("Le budget doit contenir entre 1 et 20 étapes.")
        goal_id = f"goal_{uuid.uuid4().hex}"
        maintenant = _now()
        with self.connection:
            self.connection.execute(
                """INSERT INTO goals
                   (id, mission, action, target, priority, status, max_steps,
                    steps_used, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?, 0, ?, ?)""",
                (
                    goal_id,
                    mission,
                    action,
                    cible,
                    priorite,
                    max_etapes,
                    maintenant,
                    maintenant,
                ),
            )
            self._ajouter_evenement(
                goal_id,
                TypeEvenementBut.CREATED,
                {
                    "mission": mission,
                    "action": action,
                    "target": cible,
                    "priority": priorite,
                    "max_steps": max_etapes,
                },
                maintenant,
            )
        resultat = self.but(goal_id)
        assert resultat is not None
        return resultat

    def but(self, goal_id: str) -> But | None:
        row = self.connection.execute(
            "SELECT * FROM goals WHERE id=?", (goal_id,)
        ).fetchone()
        return self._decoder_but(row) if row is not None else None

    def dernier(self) -> But | None:
        row = self.connection.execute(
            "SELECT * FROM goals ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return self._decoder_but(row) if row is not None else None

    def eligibles(self) -> list[But]:
        rows = self.connection.execute(
            """SELECT * FROM goals
               WHERE status IN ('pending', 'active')
               ORDER BY priority DESC, updated_at ASC, id ASC"""
        )
        return [self._decoder_but(row) for row in rows]

    def transition(
        self,
        goal_id: str,
        statut: StatutBut,
        evenement: TypeEvenementBut,
        payload: dict[str, Any] | None = None,
    ) -> But:
        courant = self.but(goal_id)
        if courant is None:
            raise KeyError(goal_id)
        if statut not in self.TRANSITIONS.get(courant.statut, set()):
            raise ValueError(
                f"Transition de but interdite : {courant.statut.value} → {statut.value}"
            )
        maintenant = _now()
        raison = str((payload or {}).get("reason") or "") or None
        with self.connection:
            self.connection.execute(
                """UPDATE goals SET status=?, last_reason=COALESCE(?, last_reason),
                   updated_at=? WHERE id=?""",
                (statut.value, raison, maintenant, goal_id),
            )
            self._ajouter_evenement(
                goal_id, evenement, payload or {}, maintenant
            )
        resultat = self.but(goal_id)
        assert resultat is not None
        return resultat

    def evenement(
        self,
        goal_id: str,
        evenement: TypeEvenementBut,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self.but(goal_id) is None:
            raise KeyError(goal_id)
        with self.connection:
            self._ajouter_evenement(
                goal_id, evenement, payload or {}, _now()
            )

    def commencer_etape(
        self,
        goal_id: str,
        choix: dict[str, Any],
    ) -> But:
        courant = self.but(goal_id)
        if courant is None:
            raise KeyError(goal_id)
        if courant.statut is not StatutBut.ACTIVE:
            raise ValueError("Une étape exige un but actif.")
        if courant.etapes_utilisees >= courant.max_etapes:
            raise ValueError("Le budget du but est épuisé.")
        maintenant = _now()
        with self.connection:
            self.connection.execute(
                """UPDATE goals SET steps_used=steps_used+1, updated_at=?
                   WHERE id=?""",
                (maintenant, goal_id),
            )
            self._ajouter_evenement(
                goal_id, TypeEvenementBut.STEP_STARTED, choix, maintenant
            )
        resultat = self.but(goal_id)
        assert resultat is not None
        return resultat

    def enregistrer_episode(
        self,
        goal_id: str,
        episode_id: str,
        evaluation: dict[str, Any],
    ) -> But:
        courant = self.but(goal_id)
        if courant is None:
            raise KeyError(goal_id)
        if courant.statut is not StatutBut.ACTIVE:
            raise ValueError("Un épisode ne peut être lié qu'à un but actif.")
        maintenant = _now()
        with self.connection:
            self.connection.execute(
                """UPDATE goals SET last_episode_id=?, updated_at=?
                   WHERE id=?""",
                (episode_id, maintenant, goal_id),
            )
            self._ajouter_evenement(
                goal_id,
                TypeEvenementBut.EPISODE_EVALUATED,
                {"episode_id": episode_id, "evaluation": evaluation},
                maintenant,
            )
        resultat = self.but(goal_id)
        assert resultat is not None
        return resultat

    def evenements(self, goal_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT sequence, event_type, payload_json, created_at
               FROM goal_events WHERE goal_id=? ORDER BY sequence""",
            (goal_id,),
        )
        return [
            {
                "sequence": int(row["sequence"]),
                "event_type": str(row["event_type"]),
                "payload": json.loads(row["payload_json"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def _ajouter_evenement(
        self,
        goal_id: str,
        evenement: TypeEvenementBut,
        payload: dict[str, Any],
        created_at: str,
    ) -> None:
        self.connection.execute(
            """INSERT INTO goal_events
               (goal_id, event_type, payload_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                goal_id,
                evenement.value,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )

    @staticmethod
    def _decoder_but(row: sqlite3.Row) -> But:
        return But(
            id=str(row["id"]),
            mission=str(row["mission"]),
            action=str(row["action"]) if row["action"] is not None else None,
            cible=str(row["target"]) if row["target"] is not None else None,
            priorite=int(row["priority"]),
            statut=StatutBut(str(row["status"])),
            max_etapes=int(row["max_steps"]),
            etapes_utilisees=int(row["steps_used"]),
            dernier_episode_id=(
                str(row["last_episode_id"])
                if row["last_episode_id"] is not None
                else None
            ),
            derniere_raison=(
                str(row["last_reason"])
                if row["last_reason"] is not None
                else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def close(self) -> None:
        self.connection.close()
