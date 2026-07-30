"""Acceptation V0.14 depuis la commande réellement installée."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def _digest(path: Path) -> str:
    if not path.exists():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(*args: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        ["kairos", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if not completed.stdout.strip():
        return completed.returncode, {"stderr": completed.stderr}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": completed.stdout, "stderr": completed.stderr}
    return completed.returncode, payload


def main() -> int:
    cognition = Path("memory/cognition.db")
    before = _digest(cognition)
    code_known, known = _run("--causal-run", "cherche atome")
    code_unknown, unknown = _run("--causal-run", "cherche xylophore")
    known_id = str(known.get("id", ""))
    code_replay, replay = _run("--causal-replay", known_id)
    code_status, status = _run("--causal-status")
    after = _digest(cognition)

    known_eval = dict(known.get("evaluation") or {})
    unknown_eval = dict(unknown.get("evaluation") or {})
    comparison = dict(replay.get("comparison") or {})
    last = dict(status.get("last_episode") or {})
    checks = {
        "installed_command_succeeds": code_known == 0,
        "known_goal_is_reached": bool(known_eval.get("objectif_atteint")),
        "known_result_is_complete": known_eval.get("score_resultat") == 100,
        "episode_is_persisted": bool(known_id),
        "unknown_command_succeeds_technically": code_unknown == 0 and bool(unknown_eval.get("succes_technique")),
        "unknown_goal_is_not_faked": not bool(unknown_eval.get("objectif_atteint")),
        "unknown_failure_is_localized": "information_not_found" in list(unknown_eval.get("erreurs") or []),
        "replay_command_succeeds": code_replay == 0,
        "replay_links_original": comparison.get("source_episode_id") == known_id,
        "replay_has_no_regression": comparison.get("regression") is False,
        "status_observes_last_replay": code_status == 0 and last.get("id") == comparison.get("replay_episode_id"),
        "cognitive_memory_is_unchanged": before == after,
    }
    passed = sum(checks.values())
    total = len(checks)
    print(f"USER_ACCEPTANCE_V014: {passed}/{total} scénarios réussis")
    for name, value in checks.items():
        print(f"[{'PASS' if value else 'FAIL'}] {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
