"""Barrière V0.13 : SECAU réel dans une mémoire de laboratoire."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kairos.memory import MemoryRepository
from kairos.self_correction import SelfCorrectionLab


def add_research(
    repository: MemoryRepository,
    name: str,
    *,
    two_domains: bool,
) -> str:
    urls = [
        f"https://science.example/{name}",
        (
            f"https://dictionary.example/{name}"
            if two_domains
            else f"https://science.example/{name}-2"
        ),
    ]
    claims = [
        f"Le concept {name} est associé à une définition vérifiable.",
        f"{name} désigne un concept décrit par une seconde source.",
    ]
    evidence = [
        repository.add_evidence("web", url, claim, 75)
        for url, claim in zip(urls, claims)
    ]
    return repository.add_hypothesis(
        {
            "created_from_experience_id": "self_correction_benchmark",
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


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config_dir = root / "data" / "cognition"
        config_dir.mkdir(parents=True)
        (config_dir / "self_correction.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "mode": "isolated_research_lab",
                    "max_cycles": 5,
                    "max_candidates": 20,
                    "max_seconds": 5,
                    "auto_promote_in_lab": True,
                    "production_commit": False,
                    "permissions": {
                        "network": False,
                        "shell": False,
                        "process": False,
                        "hardware": False,
                        "production_memory_write": False,
                        "laboratory_memory_write": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        source_path = root / "memory" / "cognition.db"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source = MemoryRepository(source_path)
        complete = add_research(source, "xylophore", two_domains=True)
        incomplete = add_research(source, "incomplet", two_domains=False)
        generic = source.add_hypothesis(
            {
                "created_from_experience_id": "generic",
                "name": "sans_contrat",
                "definition": "candidat sans test exécutable",
                "evidence_ids": [],
                "score": 20,
            }
        )
        source.close()

        lab = SelfCorrectionLab(root)
        result = lab.run(source_path)
        production = MemoryRepository(source_path)
        laboratory = MemoryRepository(result.laboratory_path)
        audits = laboratory.audit_events()
        reviews = [
            event for event in audits if event["event"] == "SECAU_REVIEWED"
        ]
        checks = {
            "production_unchanged": result.production_unchanged,
            "two_real_secau_calls": result.secau_calls == 2,
            "complete_promoted_in_lab": result.verdicts.get("promote") == 1,
            "incomplete_waits": (
                result.verdicts.get("needs_more_evidence") == 1
            ),
            "unknown_contract_exposed": (
                len(result.skipped) == 1
                and result.skipped[0]["hypothesis"] == generic
            ),
            "production_complete_still_candidate": (
                production.hypothesis(complete)["status"] == "candidate"
            ),
            "production_incomplete_still_candidate": (
                production.hypothesis(incomplete)["status"] == "candidate"
            ),
            "production_has_no_promoted_concept": (
                production.search({"text": "xylophore"}) == []
            ),
            "lab_has_promoted_concept": (
                len(laboratory.search({"text": "xylophore"})) == 1
            ),
            "secau_audit_observable": len(reviews) == 2,
            "cycle_bounded": result.cycles <= 5,
            "report_persisted": Path(result.report_path).is_file(),
            "no_background_process": (
                lab.status()["background_process"] is False
            ),
        }
        production.close()
        laboratory.close()
        passed = sum(checks.values())
        total = len(checks)
        print(f"SELF_CORRECTION_BENCHMARK: {passed}/{total}")
        print(f"SECAU_INTERNAL_CALLS: {result.secau_calls}")
        print(f"PRODUCTION_MUTATIONS: {0 if result.production_unchanged else 1}")
        for name, ok in checks.items():
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
