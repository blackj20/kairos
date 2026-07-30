"""Acceptation V0.13 depuis la commande réellement installée."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from kairos.memory import MemoryRepository


def main() -> int:
    root = Path(__file__).resolve().parent
    memory = root / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    source_path = memory / "cognition.db"
    repository = MemoryRepository(source_path)
    name = "labdemo"
    urls = [
        "https://science.example/labdemo",
        "https://dictionary.example/labdemo",
    ]
    claims = [
        "Labdemo est un concept créé pour l'acceptation du laboratoire.",
        "Le concept labdemo vérifie une self-correction isolée.",
    ]
    evidence = [
        repository.add_evidence("web", url, claim, 75)
        for url, claim in zip(urls, claims)
    ]
    hypothesis_id = repository.add_hypothesis(
        {
            "created_from_experience_id": "acceptance_v013",
            "name": name,
            "domain": "general",
            "definition": claims[0],
            "evidence_ids": evidence,
            "source_urls": urls,
            "source_claims": claims,
            "research_kind": "information.search",
            "score": 70,
        }
    )
    repository.close()

    executable = shutil.which("kairos")
    checks: dict[str, bool] = {
        "installed_command_exists": executable is not None,
    }
    if executable is None:
        print("USER_ACCEPTANCE_V013: 0/1")
        return 1

    launched = subprocess.run(
        [executable, "self-correction=on"],
        check=False,
        capture_output=True,
        text=True,
    )
    checks["command_exits_zero"] = launched.returncode == 0
    try:
        result = json.loads(launched.stdout)
    except json.JSONDecodeError:
        result = {}
    checks["real_secau_call"] = int(result.get("secau_calls", 0)) >= 1
    checks["promotion_only_in_lab"] = (
        result.get("verdicts", {}).get("promote", 0) >= 1
        and result.get("production_unchanged") is True
    )

    production = MemoryRepository(source_path)
    hypothesis = production.hypothesis(hypothesis_id)
    checks["production_candidate_unchanged"] = (
        hypothesis is not None and hypothesis["status"] == "candidate"
    )
    checks["production_has_no_lab_concept"] = (
        production.search({"text": name}) == []
    )
    production.close()

    lab_path = Path(str(result.get("laboratory_path", "")))
    if lab_path.is_file():
        laboratory = MemoryRepository(lab_path)
        checks["laboratory_contains_promotion"] = (
            len(laboratory.search({"text": name})) == 1
        )
        laboratory.close()
    else:
        checks["laboratory_contains_promotion"] = False

    status = subprocess.run(
        [executable, "self-correction=status"],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        status_payload = json.loads(status.stdout)
    except json.JSONDecodeError:
        status_payload = {}
    checks["status_observes_same_run"] = (
        status.returncode == 0
        and status_payload.get("run_id") == result.get("run_id")
        and status_payload.get("background_process") is False
    )

    passed = sum(checks.values())
    total = len(checks)
    print(f"USER_ACCEPTANCE_V013: {passed}/{total} scénarios réussis")
    for name_check, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name_check}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
