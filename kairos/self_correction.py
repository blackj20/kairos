"""Laboratoire isolé pour observer la self-correction réelle de Kairos."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cognition import Secau
from .causal import TesterCausal
from .information import ConsolidateurRecherche
from .memory import MemoryRepository


def _now_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"self_correction_{stamp}_{uuid.uuid4().hex[:8]}"


def _digest(path: Path) -> str:
    if not path.exists():
        return "absent"
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SelfCorrectionResult:
    run_id: str
    mode: str
    state: str
    cycles: int
    candidates_seen: int
    verdicts: dict[str, int]
    skipped: tuple[dict[str, str], ...]
    errors: tuple[dict[str, str], ...]
    before: dict[str, int]
    after_lab: dict[str, int]
    production_unchanged: bool
    stopped_by: str
    laboratory_path: str
    report_path: str
    secau_calls: int

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfCorrectionLab:
    """Exécute Tester et SECAU dans une copie jetable de la mémoire."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = racine or Path(__file__).resolve().parent.parent
        self.config = self._lire_config()

    @property
    def dossier(self) -> Path:
        return self.racine / "memory" / "self_correction_runs"

    def run(self, source_path: Path | None = None) -> SelfCorrectionResult:
        source_path = source_path or self.racine / "memory" / "cognition.db"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        self.dossier.mkdir(parents=True, exist_ok=True)
        run_id = _now_id()
        lab_path = self.dossier / f"{run_id}.db"
        report_path = self.dossier / f"{run_id}.json"

        source = MemoryRepository(source_path)
        before = source.cognitive_counts()
        lab = MemoryRepository(lab_path)
        source.connection.backup(lab.connection)
        source.close()
        production_digest = _digest(source_path)

        lab.record_audit(
            "SELF_CORRECTION_STARTED",
            {
                "run": run_id,
                "mode": self.config["mode"],
                "production_commit": False,
            },
        )
        started = time.monotonic()
        seen: set[str] = set()
        verdicts: dict[str, int] = {}
        skipped: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        cycles = 0
        secau_calls = 0
        stopped_by = "stable"

        max_cycles = int(self.config["max_cycles"])
        max_candidates = int(self.config["max_candidates"])
        max_seconds = float(self.config["max_seconds"])
        for cycle in range(max_cycles):
            if time.monotonic() - started >= max_seconds:
                stopped_by = "time_limit"
                break
            pending = [
                candidate
                for candidate in lab.candidate_hypotheses()
                if str(candidate["id"]) not in seen
            ]
            if not pending:
                stopped_by = "stable"
                break
            cycles = cycle + 1
            for candidate in pending:
                if len(seen) >= max_candidates:
                    stopped_by = "candidate_limit"
                    break
                if time.monotonic() - started >= max_seconds:
                    stopped_by = "time_limit"
                    break
                hypothesis_id = str(candidate["id"])
                seen.add(hypothesis_id)
                payload = dict(candidate["payload"])
                try:
                    verdict = self._review_candidate(
                        lab,
                        hypothesis_id,
                        payload,
                    )
                    if verdict is None:
                        reason = "aucun contrat Tester ou rapport compatible"
                        skipped.append(
                            {"hypothesis": hypothesis_id, "reason": reason}
                        )
                        lab.record_audit(
                            "SELF_CORRECTION_SKIPPED",
                            {
                                "run": run_id,
                                "hypothesis": hypothesis_id,
                                "reason": reason,
                            },
                        )
                        continue
                    secau_calls += 1
                    verdicts[verdict] = verdicts.get(verdict, 0) + 1
                except Exception as error:
                    detail = f"{type(error).__name__}: {error}"
                    errors.append(
                        {"hypothesis": hypothesis_id, "error": detail}
                    )
                    lab.record_audit(
                        "SELF_CORRECTION_ERROR",
                        {
                            "run": run_id,
                            "hypothesis": hypothesis_id,
                            "error": detail,
                        },
                    )
            if stopped_by in {"candidate_limit", "time_limit"}:
                break
        else:
            stopped_by = "cycle_limit"

        after = lab.cognitive_counts()
        lab.record_audit(
            "SELF_CORRECTION_COMPLETED",
            {
                "run": run_id,
                "cycles": cycles,
                "seen": len(seen),
                "verdicts": verdicts,
                "skipped": len(skipped),
                "errors": len(errors),
                "stopped_by": stopped_by,
            },
        )
        lab.close()

        production_unchanged = production_digest == _digest(source_path)
        result = SelfCorrectionResult(
            run_id=run_id,
            mode=str(self.config["mode"]),
            state="completed",
            cycles=cycles,
            candidates_seen=len(seen),
            verdicts=verdicts,
            skipped=tuple(skipped),
            errors=tuple(errors),
            before=before,
            after_lab=after,
            production_unchanged=production_unchanged,
            stopped_by=stopped_by,
            laboratory_path=str(lab_path),
            report_path=str(report_path),
            secau_calls=secau_calls,
        )
        payload = result.vers_dict()
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.dossier / "latest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    def status(self) -> dict[str, Any]:
        latest = self.dossier / "latest.json"
        if not latest.exists():
            return {
                "state": "never_run",
                "mode": self.config["mode"],
                "background_process": False,
            }
        payload = json.loads(latest.read_text(encoding="utf-8"))
        payload["background_process"] = False
        return payload

    @staticmethod
    def off() -> dict[str, Any]:
        return {
            "state": "idle",
            "background_process": False,
            "detail": (
                "La self-correction est synchrone : aucun processus "
                "en arrière-plan n'est actif."
            ),
        }

    @staticmethod
    def parse_command(message: str) -> str | None:
        normalized = "".join(message.casefold().split())
        aliases = {
            "self-correction=on": "on",
            "self-correction=off": "off",
            "self-correction=status": "status",
            "self-correction=statut": "status",
            "selfcorrection=on": "on",
            "selfcorrection=off": "off",
            "selfcorrection=status": "status",
        }
        return aliases.get(normalized)

    def _review_candidate(
        self,
        repository: MemoryRepository,
        hypothesis_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        if payload.get("research_kind") == "information.search":
            result = ConsolidateurRecherche(repository).consolider(
                hypothesis_id
            )
            return result.secau.verdict.value

        if payload.get("causal_kind") == "behavior.change":
            report_id, _ = TesterCausal(repository).tester(hypothesis_id)
            return Secau(repository).review_causal(
                hypothesis_id, report_id
            ).verdict.value

        report = repository.latest_report_for(hypothesis_id)
        if report is None:
            return None
        secau = Secau(repository)
        if payload.get("kind") == "semantic_relation":
            return secau.review_relation(
                hypothesis_id,
                str(report["id"]),
            ).verdict.value
        return secau.review(
            hypothesis_id,
            str(report["id"]),
            payload,
        ).verdict.value

    def _lire_config(self) -> dict[str, Any]:
        path = self.racine / "data" / "cognition" / "self_correction.json"
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Configuration self-correction invalide : {path}"
            ) from error
        if config.get("production_commit") is not False:
            raise ValueError(
                "Le laboratoire ne peut pas écrire en mémoire principale."
            )
        if config.get("permissions", {}).get("production_memory_write"):
            raise ValueError(
                "La permission production_memory_write doit rester fermée."
            )
        for key in ("max_cycles", "max_candidates", "max_seconds"):
            if int(config.get(key, 0)) <= 0:
                raise ValueError(f"Limite self-correction invalide : {key}")
        return config
