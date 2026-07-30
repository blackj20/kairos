"""Stockage SQLite append-only des épisodes et transitions causales."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .modeles import StatutEpisode


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StockageCausal:
    TRANSITIONS = {
        StatutEpisode.CREATED.value: StatutEpisode.PREDICTED.value,
        StatutEpisode.PREDICTED.value: StatutEpisode.EXECUTED.value,
        StatutEpisode.EXECUTED.value: StatutEpisode.OBSERVED.value,
        StatutEpisode.OBSERVED.value: StatutEpisode.EVALUATED.value,
    }
    CHAMPS = {
        StatutEpisode.PREDICTED.value: "prediction_json",
        StatutEpisode.EXECUTED.value: "execution_json",
        StatutEpisode.OBSERVED.value: "observation_json",
        StatutEpisode.EVALUATED.value: "evaluation_json",
    }

    def __init__(self, chemin: str | Path = ":memory:") -> None:
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(chemin))
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS causal_episodes (
              id TEXT PRIMARY KEY,
              request TEXT NOT NULL,
              action TEXT,
              target TEXT,
              route_id TEXT,
              status TEXT NOT NULL,
              replay_of TEXT,
              prediction_json TEXT,
              execution_json TEXT,
              observation_json TEXT,
              evaluation_json TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS causal_transitions (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              episode_id TEXT NOT NULL,
              previous_status TEXT,
              next_status TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(episode_id) REFERENCES causal_episodes(id)
            );
            """
        )
        self.connection.commit()

    def creer(
        self,
        requete: str,
        action: str | None,
        cible: str | None,
        route_id: str | None,
        *,
        replay_of: str | None = None,
    ) -> str:
        episode_id = f"causal_{uuid.uuid4().hex}"
        maintenant = _now()
        with self.connection:
            self.connection.execute(
                """INSERT INTO causal_episodes
                   (id, request, action, target, route_id, status, replay_of,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'created', ?, ?, ?)""",
                (
                    episode_id,
                    requete,
                    action,
                    cible,
                    route_id,
                    replay_of,
                    maintenant,
                    maintenant,
                ),
            )
            self.connection.execute(
                """INSERT INTO causal_transitions
                   (episode_id, previous_status, next_status, payload_json, created_at)
                   VALUES (?, NULL, 'created', '{}', ?)""",
                (episode_id, maintenant),
            )
        return episode_id

    def transition(
        self,
        episode_id: str,
        statut: StatutEpisode,
        payload: dict[str, Any],
    ) -> None:
        row = self.connection.execute(
            "SELECT status FROM causal_episodes WHERE id=?", (episode_id,)
        ).fetchone()
        if row is None:
            raise KeyError(episode_id)
        precedent = str(row["status"])
        suivant = statut.value
        if self.TRANSITIONS.get(precedent) != suivant:
            raise ValueError(
                f"Transition causale interdite : {precedent} → {suivant}"
            )
        champ = self.CHAMPS[suivant]
        serialise = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        maintenant = _now()
        with self.connection:
            self.connection.execute(
                f"UPDATE causal_episodes SET status=?, {champ}=?, updated_at=? WHERE id=?",
                (suivant, serialise, maintenant, episode_id),
            )
            self.connection.execute(
                """INSERT INTO causal_transitions
                   (episode_id, previous_status, next_status, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (episode_id, precedent, suivant, serialise, maintenant),
            )

    def episode(self, episode_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM causal_episodes WHERE id=?", (episode_id,)
        ).fetchone()
        return self._decoder(row) if row is not None else None

    def dernier(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM causal_episodes ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return self._decoder(row) if row is not None else None

    def transitions(self, episode_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT sequence, previous_status, next_status, payload_json, created_at
               FROM causal_transitions WHERE episode_id=? ORDER BY sequence""",
            (episode_id,),
        )
        return [
            {
                **dict(row),
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    @staticmethod
    def _decoder(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        for champ in (
            "prediction_json",
            "execution_json",
            "observation_json",
            "evaluation_json",
        ):
            valeur = payload.pop(champ)
            payload[champ.removesuffix("_json")] = (
                json.loads(valeur) if valeur else None
            )
        return payload

    def close(self) -> None:
        self.connection.close()
