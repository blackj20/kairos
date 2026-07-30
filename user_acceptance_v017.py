"""Acceptation V0.17 : apprendre naturellement depuis une vraie conversation."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "memory"
ISOLATED = (
    "cognition.db",
    "pending_questions.json",
    "experiences.json",
    "learning_events.json",
)


def run(args: list[str], *, input_text: str | None = None) -> tuple[int, str]:
    process = subprocess.run(
        ["kairos", *args],
        input=input_text,
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=30,
        check=False,
    )
    return process.returncode, (process.stdout + process.stderr).strip()


def parse(args: list[str]) -> tuple[int, dict[str, Any], str]:
    code, output = run(args)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        payload = {}
    return code, payload, output


def main() -> int:
    MEMORY.mkdir(parents=True, exist_ok=True)
    backup = MEMORY / "v017_acceptance_backup"
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir()
    for name in ISOLATED:
        path = MEMORY / name
        if path.exists():
            path.replace(backup / name)

    checks: dict[str, bool] = {}
    try:
        code, help_output = run(["--help"])
        checks["help"] = (
            code == 0
            and "--learning-status" in help_output
            and "--hypothesis-status" in help_output
        )

        code, dialogue = run(
            [],
            input_text=(
                "c'est quoi un xylophore ?\n"
                "un xylophore est un instrument musical\n"
                "xylophone, marimba, balafon\n"
                "piano, guitare\n"
                "cherche toi-même\n"
                "statut apprentissage\n"
                "quit\n"
            ),
        )
        checks["conversation_success"] = code == 0
        checks["unknown_admitted"] = "Je ne connais pas encore" in dialogue
        checks["natural_explanation_requested"] = (
            "Explique-le naturellement" in dialogue
        )
        checks["hypothesis_created"] = "Hypothèse créée" in dialogue
        checks["link_created_automatically"] = (
            "J'ai déjà créé 1 lien(s) candidat(s)" in dialogue
        )
        checks["no_redundant_relation_question"] = (
            "Donne 3 exemple(s) concret(s)" in dialogue
        )
        checks["counterexample_question"] = (
            "ne doit pas avoir ce sens" in dialogue
        )
        checks["source_question"] = "Où puis-je vérifier" in dialogue
        checks["structured_not_promoted"] = (
            "Le dossier est structuré" in dialogue
            and "Tester" in dialogue
            and "SECAU" in dialogue
        )
        checks["gain_is_visible"] = (
            "Gain" in dialogue
            and "25%" in dialogue
            and "20%" in dialogue
        )

        code, status, _ = parse(["--learning-status"])
        candidates = status.get("candidates", [])
        checks["learning_status"] = (
            code == 0
            and status.get("active") is False
            and len(candidates) == 1
        )
        checks["structure_score"] = bool(
            candidates
            and candidates[0].get("structure_score") == 100
        )
        checks["research_next"] = bool(
            candidates
            and "sources" in candidates[0].get("missing", [])
        )

        code, hypotheses, _ = parse(["--hypothesis-status"])
        items = hypotheses.get("candidates", [])
        hypothesis_id = str(items[0].get("id", "")) if items else ""
        checks["single_candidate"] = (
            code == 0
            and hypotheses.get("count") == 1
            and bool(hypothesis_id)
        )
        checks["candidate_not_promoted"] = bool(
            items and items[0].get("status") == "candidate"
        )
        checks["next_action"] = bool(
            items and items[0].get("next_action") == "research_and_test"
        )

        code, exact, _ = parse(
            [
                "--hypothesis-status",
                "--hypothesis-id",
                hypothesis_id,
            ]
        )
        payload = exact.get("hypothesis", {}).get("payload", {})
        relations = payload.get("relation_candidates", [])
        checks["exact_link_persisted"] = (
            code == 0
            and bool(relations)
            and relations[0].get("relation") == "est_un"
            and relations[0].get("target") == "instrument musical"
        )
        checks["examples_persisted"] = (
            len(payload.get("examples", [])) == 3
            and len(payload.get("counterexamples", [])) == 2
        )
        checks["restart_persistence"] = (
            exact.get("hypothesis", {}).get("status") == "candidate"
            and payload.get("active_learning", {}).get("status")
            == "ready_for_research"
        )
        checks["database_created"] = (MEMORY / "cognition.db").exists()
    finally:
        for name in ISOLATED:
            path = MEMORY / name
            if path.exists():
                path.unlink()
            saved = backup / name
            if saved.exists():
                saved.replace(path)
        shutil.rmtree(backup, ignore_errors=True)

    passed = sum(checks.values())
    total = len(checks)
    print(f"USER_ACCEPTANCE_V017: {passed}/{total} scénarios réussis")
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
