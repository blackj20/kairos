"""Acceptation utilisateur V0.15 via la commande installée."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
GOALS_DB = ROOT / "memory" / "goals.db"


def run(*args: str) -> tuple[int, str]:
    process = subprocess.run(
        ["kairos", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return process.returncode, (process.stdout + process.stderr).strip()


def payload(*args: str) -> tuple[int, dict[str, Any], str]:
    code, output = run(*args)
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = {}
    return code, parsed, output


def main() -> int:
    GOALS_DB.unlink(missing_ok=True)
    checks: dict[str, bool] = {}

    code, help_output = run("--help")
    checks["help"] = code == 0 and "--goal-run" in help_output

    code, known, _ = payload("--goal-run", "cherche atome")
    checks["known_completed"] = (
        code == 0 and known.get("goal", {}).get("statut") == "completed"
    )
    checks["known_episode"] = bool(known.get("goal", {}).get("dernier_episode_id"))
    checks["known_causal_goal"] = bool(
        known.get("episode", {})
        .get("evaluation", {})
        .get("objectif_atteint")
    )

    code, unknown, _ = payload("--goal-run", "cherche xylophore")
    checks["unknown_blocked"] = (
        code == 0 and unknown.get("goal", {}).get("statut") == "blocked"
    )
    checks["technical_not_goal"] = bool(
        unknown.get("episode", {})
        .get("evaluation", {})
        .get("succes_technique")
        and not unknown.get("episode", {})
        .get("evaluation", {})
        .get("objectif_atteint")
    )

    code, incomplete, _ = payload("--goal-run", "cherche")
    checks["incomplete_no_execution"] = (
        code == 0
        and incomplete.get("goal", {}).get("statut") == "blocked"
        and incomplete.get("episode") is None
    )

    code, created, _ = payload(
        "--goal-create",
        "cherche atome",
        "--goal-priority",
        "80",
        "--goal-max-steps",
        "2",
    )
    goal_id = str(created.get("goal", {}).get("id", ""))
    checks["create_pending"] = (
        code == 0
        and bool(goal_id)
        and created.get("goal", {}).get("statut") == "pending"
    )

    code, status, _ = payload("--goal-status", "--goal-id", goal_id)
    checks["persistent_status"] = (
        code == 0 and status.get("goal", {}).get("id") == goal_id
    )

    code, stepped, _ = payload("--goal-step", goal_id)
    checks["restart_step_completed"] = (
        code == 0 and stepped.get("goal", {}).get("statut") == "completed"
    )
    events = stepped.get("events", [])
    checks["events_ordered"] = (
        bool(events)
        and [item["sequence"] for item in events]
        == sorted(item["sequence"] for item in events)
    )
    checks["attention_explained"] = len(
        stepped.get("attention", {}).get("raisons", [])
    ) >= 3

    code, candidate, _ = payload("--goal-create", "cherche boucle")
    invalid_id = str(candidate.get("goal", {}).get("id", ""))
    code, invalidated, _ = payload(
        "--goal-invalidate",
        invalid_id,
        "--reason",
        "objectif remplacé",
    )
    checks["invalidation"] = (
        code == 0
        and invalidated.get("goal", {}).get("statut") == "invalidated"
    )
    code, _, output = payload("--goal-step", invalid_id)
    checks["terminal_not_executed"] = code != 0 and "terminal" in output
    checks["persistent_database"] = GOALS_DB.exists()

    passed = sum(checks.values())
    total = len(checks)
    print(f"USER_ACCEPTANCE_V015: {passed}/{total} scénarios réussis")
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
