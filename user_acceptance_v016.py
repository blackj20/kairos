"""Acceptation utilisateur V0.16 : interaction simple et hypothèse persistante."""

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
    backup = MEMORY / "v016_acceptance_backup"
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
        checks["help"] = code == 0 and "--hypothesis-status" in help_output

        code, dialogue = run(
            [],
            input_text=(
                "deploie python\n"
                "installer\n"
                "mes hypotheses\n"
                "quit\n"
            ),
        )
        checks["interactive_success"] = code == 0
        checks["question_visible"] = "Quel sens" in dialogue
        checks["hypothesis_visible"] = "Hypothèse créée" in dialogue
        checks["missing_visible"] = all(
            item in dialogue
            for item in ("sources", "tests", "validation_secau")
        )
        checks["natural_status_command"] = '"count": 1' in dialogue

        code, status, _ = parse(["--hypothesis-status"])
        candidates = status.get("candidates", [])
        hypothesis_id = (
            str(candidates[0].get("id", ""))
            if isinstance(candidates, list) and candidates
            else ""
        )
        checks["candidate_persisted"] = (
            code == 0
            and status.get("count") == 1
            and bool(hypothesis_id)
        )
        checks["candidate_not_promoted"] = bool(
            candidates and candidates[0].get("status") == "candidate"
        )
        checks["next_action_visible"] = bool(
            candidates
            and candidates[0].get("next_action") == "collect_evidence"
        )

        code, exact, _ = parse(
            [
                "--hypothesis-status",
                "--hypothesis-id",
                hypothesis_id,
            ]
        )
        checks["exact_status"] = (
            code == 0
            and exact.get("hypothesis", {}).get("id") == hypothesis_id
        )
        checks["restart_persistence"] = (
            exact.get("hypothesis", {}).get("status") == "candidate"
        )

        code, target_dialogue = run(
            [],
            input_text="installe\npython\nquit\n",
        )
        checks["target_experience_clear"] = (
            code == 0
            and "ne contient pas encore d'explication" in target_dialogue
        )
        _, after_target, _ = parse(["--hypothesis-status"])
        checks["target_not_hypothesis"] = after_target.get("count") == 1
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
    print(f"USER_ACCEPTANCE_V016: {passed}/{total} scénarios réussis")
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
