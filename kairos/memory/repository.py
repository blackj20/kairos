"""Dépôt SQLite : hypothèses, preuves, concepts, rapports et audit."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryRepository:
    """Implémentation locale avec écritures atomiques et provenance obligatoire."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence (
              id TEXT PRIMARY KEY, source_type TEXT NOT NULL,
              source_ref TEXT NOT NULL, content_hash TEXT NOT NULL,
              trust_score INTEGER NOT NULL CHECK(trust_score BETWEEN 0 AND 100),
              collected_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hypotheses (
              id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
              status TEXT NOT NULL, score INTEGER NOT NULL,
              created_from_experience_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS concepts (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, domain TEXT NOT NULL,
              definition TEXT, mastery_score INTEGER NOT NULL,
              status TEXT NOT NULL, version INTEGER NOT NULL,
              evidence_ids_json TEXT NOT NULL, rollback_payload_json TEXT
            );
            CREATE TABLE IF NOT EXISTS test_reports (
              id TEXT PRIMARY KEY, subject_id TEXT NOT NULL,
              passed INTEGER NOT NULL, report_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS semantic_relations (
              id TEXT PRIMARY KEY, source TEXT NOT NULL,
              relation_type TEXT NOT NULL, target TEXT NOT NULL,
              status TEXT NOT NULL, mastery_score INTEGER NOT NULL,
              evidence_ids_json TEXT NOT NULL, examples_json TEXT NOT NULL,
              counterexamples_json TEXT NOT NULL, version INTEGER NOT NULL,
              consecutive_errors INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS usage_events (
              id TEXT PRIMARY KEY, relation_id TEXT NOT NULL,
              success INTEGER NOT NULL, request TEXT NOT NULL,
              details_json TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(relation_id) REFERENCES semantic_relations(id)
            );
            CREATE TABLE IF NOT EXISTS audit (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              event TEXT NOT NULL, payload_json TEXT NOT NULL,
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

    def add_evidence(
        self, source_type: str, source_ref: str, content: str, trust_score: int
    ) -> str:
        if not source_ref.strip() or not content.strip():
            raise ValueError("Une preuve exige une source et un contenu.")
        evidence_id = f"evidence_{uuid.uuid4().hex}"
        digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
        with self.transaction() as db:
            db.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?)",
                (evidence_id, source_type, source_ref, digest, trust_score, _now()),
            )
            self._audit(db, "EVIDENCE_ADDED", {"id": evidence_id})
        return evidence_id

    def add_hypothesis(self, hypothesis: dict[str, Any]) -> str:
        experience_id = str(hypothesis.get("created_from_experience_id", "")).strip()
        if not experience_id:
            raise ValueError("Une hypothèse doit référencer une expérience.")
        hypothesis_id = str(hypothesis.get("id") or f"hypothesis_{uuid.uuid4().hex}")
        score = int(hypothesis.get("score", 0))
        payload = dict(hypothesis)
        payload.pop("id", None)
        with self.transaction() as db:
            db.execute(
                "INSERT INTO hypotheses VALUES (?, ?, 'candidate', ?, ?, ?)",
                (hypothesis_id, json.dumps(payload, ensure_ascii=False), score,
                 experience_id, _now()),
            )
            self._audit(db, "HYPOTHESIS_CREATED", {"id": hypothesis_id})
        return hypothesis_id

    def search(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        term = f"%{str(query.get('text', '')).casefold()}%"
        domain = query.get("domain")
        sql = "SELECT * FROM concepts WHERE status='confirmed' AND lower(name) LIKE ?"
        params: list[Any] = [term]
        if domain:
            sql += " AND domain=?"
            params.append(domain)
        return [dict(row) for row in self.connection.execute(sql, params)]

    def candidate_for(self, name: str) -> dict[str, Any] | None:
        """Réutilise une hypothèse candidate au lieu de la dupliquer."""

        cible = name.casefold().strip()
        rows = self.connection.execute(
            "SELECT * FROM hypotheses WHERE status='candidate' "
            "ORDER BY created_at DESC"
        )
        for row in rows:
            payload = json.loads(row["payload_json"])
            if str(payload.get("name", "")).casefold().strip() == cible:
                return {**dict(row), "payload": payload}
        return None

    def evidence(self, evidence_id: str) -> dict[str, Any] | None:
        """Expose uniquement les métadonnées et l'empreinte d'une preuve."""

        row = self.connection.execute(
            "SELECT * FROM evidence WHERE id=?", (evidence_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def evidence_matches(
        self,
        evidence_id: str,
        *,
        source_ref: str,
        content: str,
    ) -> bool:
        """Vérifie simultanément provenance et intégrité SHA-256."""

        row = self.evidence(evidence_id)
        if row is None or str(row["source_ref"]) != source_ref:
            return False
        digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
        return str(row["content_hash"]) == digest

    def research_candidates(self) -> list[dict[str, Any]]:
        """Liste les hypothèses de recherche encore candidates."""

        candidates: list[dict[str, Any]] = []
        rows = self.connection.execute(
            "SELECT * FROM hypotheses WHERE status='candidate' "
            "ORDER BY created_at"
        )
        for row in rows:
            payload = json.loads(row["payload_json"])
            if payload.get("research_kind") == "information.search":
                candidates.append({**dict(row), "payload": payload})
        return candidates

    def save_report(self, subject_id: str, report: dict[str, Any]) -> str:
        report_id = f"report_{uuid.uuid4().hex}"
        with self.transaction() as db:
            db.execute(
                "INSERT INTO test_reports VALUES (?, ?, ?, ?, ?)",
                (report_id, subject_id, int(bool(report.get("passed"))),
                 json.dumps(report, ensure_ascii=False), _now()),
            )
            self._audit(db, "TEST_RECORDED", {"id": report_id, "subject": subject_id})
        return report_id

    def promote(self, hypothesis_id: str, report_id: str) -> str:
        hypothesis = self.connection.execute(
            "SELECT * FROM hypotheses WHERE id=?", (hypothesis_id,)
        ).fetchone()
        report = self.connection.execute(
            "SELECT * FROM test_reports WHERE id=?", (report_id,)
        ).fetchone()
        if hypothesis is None or report is None or not report["passed"]:
            raise ValueError("Promotion impossible sans hypothèse et rapport réussi.")
        payload = json.loads(hypothesis["payload_json"])
        evidence_ids = payload.get("evidence_ids", [])
        if not evidence_ids:
            raise ValueError("Promotion impossible sans provenance.")
        found = self.connection.execute(
            f"SELECT count(*) FROM evidence WHERE id IN ({','.join('?' * len(evidence_ids))})",
            evidence_ids,
        ).fetchone()[0]
        if found != len(evidence_ids):
            raise ValueError("Une preuve référencée est absente.")
        concept_id = str(payload.get("concept_id") or f"concept_{uuid.uuid4().hex}")
        with self.transaction() as db:
            db.execute(
                """INSERT INTO concepts VALUES (?, ?, ?, ?, 100, 'confirmed', 1, ?, NULL)""",
                (concept_id, payload["name"], payload.get("domain", "general"),
                 payload.get("definition"), json.dumps(evidence_ids)),
            )
            db.execute(
                "UPDATE hypotheses SET status='promoted' WHERE id=?", (hypothesis_id,)
            )
            self._audit(db, "KNOWLEDGE_PROMOTED",
                        {"hypothesis": hypothesis_id, "concept": concept_id,
                         "report": report_id})
        return concept_id

    def hypothesis(self, hypothesis_id: str) -> dict[str, Any] | None:
        """Retourne une hypothèse sérialisée pour les validateurs spécialisés."""

        row = self.connection.execute(
            "SELECT * FROM hypotheses WHERE id=?", (hypothesis_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            **dict(row),
            "payload": json.loads(row["payload_json"]),
        }

    def report(self, report_id: str) -> dict[str, Any] | None:
        """Retourne un rapport et son contenu structuré."""

        row = self.connection.execute(
            "SELECT * FROM test_reports WHERE id=?", (report_id,)
        ).fetchone()
        if row is None:
            return None
        return {**dict(row), "report": json.loads(row["report_json"])}

    def promote_relation(self, hypothesis_id: str, report_id: str) -> str:
        """Promeut une relation testée avec exemples et contre-exemples."""

        hypothesis = self.hypothesis(hypothesis_id)
        report = self.report(report_id)
        if hypothesis is None or report is None or not report["passed"]:
            raise ValueError("Relation non promouvable sans rapport réussi.")
        payload = hypothesis["payload"]
        evidence_ids = payload.get("evidence_ids", [])
        examples = payload.get("examples", [])
        counterexamples = payload.get("counterexamples", [])
        if len(evidence_ids) < 2:
            raise ValueError("Une relation exige au moins deux preuves.")
        if len(examples) < 3 or len(counterexamples) < 2:
            raise ValueError(
                "Une relation exige trois exemples et deux contre-exemples."
            )
        found = self.connection.execute(
            f"SELECT count(*) FROM evidence WHERE id IN ({','.join('?' * len(evidence_ids))})",
            evidence_ids,
        ).fetchone()[0]
        if found != len(evidence_ids):
            raise ValueError("Une preuve de relation est absente.")
        relation_id = f"relation_{uuid.uuid4().hex}"
        with self.transaction() as db:
            db.execute(
                """INSERT INTO semantic_relations
                   VALUES (?, ?, ?, ?, 'confirmed', 70, ?, ?, ?, 1, 0)""",
                (
                    relation_id,
                    payload["source"],
                    payload["relation"],
                    payload["target"],
                    json.dumps(evidence_ids),
                    json.dumps(examples, ensure_ascii=False),
                    json.dumps(counterexamples, ensure_ascii=False),
                ),
            )
            db.execute(
                "UPDATE hypotheses SET status='promoted' WHERE id=?",
                (hypothesis_id,),
            )
            self._audit(
                db,
                "RELATION_PROMOTED",
                {
                    "relation": relation_id,
                    "hypothesis": hypothesis_id,
                    "report": report_id,
                },
            )
        return relation_id

    def relation(self, relation_id: str) -> dict[str, Any] | None:
        """Lit l'état courant d'une relation confirmée ou en quarantaine."""

        row = self.connection.execute(
            "SELECT * FROM semantic_relations WHERE id=?", (relation_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def record_relation_use(
        self,
        relation_id: str,
        *,
        success: bool,
        request: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fait évoluer la maîtrise et met en quarantaine après trois erreurs."""

        relation = self.relation(relation_id)
        if relation is None:
            raise KeyError(relation_id)
        errors = 0 if success else int(relation["consecutive_errors"]) + 1
        score = int(relation["mastery_score"]) + (5 if success else -15)
        score = max(0, min(100, score))
        status = "quarantined" if errors >= 3 else relation["status"]
        event_id = f"usage_{uuid.uuid4().hex}"
        with self.transaction() as db:
            db.execute(
                "INSERT INTO usage_events VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    relation_id,
                    int(success),
                    request,
                    json.dumps(details or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            db.execute(
                """UPDATE semantic_relations
                   SET mastery_score=?, consecutive_errors=?, status=?
                   WHERE id=?""",
                (score, errors, status, relation_id),
            )
            self._audit(
                db,
                "RELATION_USED",
                {
                    "relation": relation_id,
                    "success": success,
                    "score": score,
                    "status": status,
                },
            )
        updated = self.relation(relation_id)
        assert updated is not None
        return updated

    def relation_usage(self, relation_id: str) -> list[dict[str, Any]]:
        """Expose l'historique immuable des réussites et erreurs."""

        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM usage_events WHERE relation_id=? ORDER BY created_at",
                (relation_id,),
            )
        ]

    def reject(self, hypothesis_id: str, reason: str) -> None:
        with self.transaction() as db:
            changed = db.execute(
                "UPDATE hypotheses SET status='rejected' WHERE id=?", (hypothesis_id,)
            ).rowcount
            if not changed:
                raise KeyError(hypothesis_id)
            self._audit(db, "HYPOTHESIS_REJECTED",
                        {"id": hypothesis_id, "reason": reason})

    def record_audit(self, event: str, payload: dict[str, Any]) -> None:
        """Expose une écriture d'audit atomique aux organes de contrôle."""

        if not event.strip():
            raise ValueError("Un événement d'audit doit avoir un nom.")
        with self.transaction() as db:
            self._audit(db, event, payload)

    def audit_events(self) -> list[dict[str, Any]]:
        return [
            {"event": row["event"], **json.loads(row["payload_json"])}
            for row in self.connection.execute("SELECT * FROM audit ORDER BY sequence")
        ]

    @staticmethod
    def _audit(db: sqlite3.Connection, event: str, payload: dict[str, Any]) -> None:
        db.execute(
            "INSERT INTO audit(event, payload_json, created_at) VALUES (?, ?, ?)",
            (event, json.dumps(payload, ensure_ascii=False), _now()),
        )

    def close(self) -> None:
        self.connection.close()
