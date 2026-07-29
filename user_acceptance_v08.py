"""Acceptation V0.8 via la commande installée et la mémoire persistante."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from kairos.memory import MemoryRepository


ROOT = Path(__file__).resolve().parent
DB = ROOT / "memory" / "cognition.db"


def run(*arguments: str) -> tuple[int, str]:
    process = subprocess.run(
        ["kairos", *arguments],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return process.returncode, (process.stdout + process.stderr).strip()


def create_candidate(name: str, *, independent: bool) -> str:
    repository = MemoryRepository(DB)
    try:
        urls = [
            f"https://science.example/{name}",
            (
                f"https://dictionary.example/{name}"
                if independent
                else f"https://science.example/{name}-bis"
            ),
        ]
        claims = [
            f"{name} est un concept vérifiable décrit par cette source.",
            f"Le concept {name} est décrit par une seconde source vérifiable.",
        ]
        evidence = [
            repository.add_evidence("web", url, claim, 75)
            for url, claim in zip(urls, claims)
        ]
        return repository.add_hypothesis(
            {
                "created_from_experience_id": "acceptance_v08",
                "name": name,
                "definition": claims[0],
                "domain": "acceptance",
                "evidence_ids": evidence,
                "source_urls": urls,
                "source_claims": claims,
                "research_kind": "information.search",
                "score": 70,
            }
        )
    finally:
        repository.close()


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    complete = create_candidate("concept_acceptance_v08", independent=True)
    incomplete = create_candidate("concept_incomplet_v08", independent=False)
    results: list[tuple[str, bool]] = []

    code, output = run("--research-review", complete)
    payload = json.loads(output) if code == 0 else {}
    results.append((
        "Tester puis SECAU promeuvent le dossier complet",
        code == 0
        and payload.get("report", {}).get("passed") is True
        and payload.get("secau", {}).get("verdict") == "promote",
    ))

    code, output = run("--research-review", incomplete)
    payload = json.loads(output) if code == 0 else {}
    results.append((
        "SECAU exige davantage de preuves pour un seul domaine",
        code == 0
        and payload.get("report_id") is None
        and payload.get("secau", {}).get("verdict") == "needs_more_evidence",
    ))

    code, output = run("--research-status")
    status = json.loads(output) if code == 0 else {}
    results.append((
        "La candidate incomplète reste visible",
        code == 0
        and any(
            item.get("id") == incomplete
            for item in status.get("candidates", [])
        ),
    ))

    code, output = run("--secau-status")
    status = json.loads(output) if code == 0 else {}
    verdicts = {item.get("verdict") for item in status.get("events", [])}
    results.append((
        "Les deux verdicts SECAU sont observables",
        code == 0
        and "promote" in verdicts
        and "needs_more_evidence" in verdicts,
    ))

    passed = sum(success for _, success in results)
    total = len(results)
    print(f"USER_ACCEPTANCE_V08: {passed}/{total} scénarios réussis")
    for name, success in results:
        print(f"[{'PASS' if success else 'FAIL'}] {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
