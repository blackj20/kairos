"""Barrière mesurable Research Tester → SECAU V0.8."""

from __future__ import annotations

from kairos.cognition import SecauVerdict
from kairos.information import ConsolidateurRecherche
from kairos.memory import MemoryRepository


def make_candidate(repository: MemoryRepository, *, two_domains: bool) -> str:
    urls = [
        "https://science.example/xylophore",
        (
            "https://dictionary.example/xylophore"
            if two_domains
            else "https://science.example/xylophore-2"
        ),
    ]
    claims = [
        "Un xylophore est un organisme associé au bois.",
        "Le xylophore désigne un organisme vivant lié au bois.",
    ]
    evidence = [
        repository.add_evidence("web", url, claim, 75)
        for url, claim in zip(urls, claims)
    ]
    return repository.add_hypothesis(
        {
            "created_from_experience_id": "benchmark_research",
            "name": "xylophore" if two_domains else "xylophore incomplet",
            "definition": claims[0],
            "domain": "general",
            "evidence_ids": evidence,
            "source_urls": urls,
            "source_claims": claims,
            "research_kind": "information.search",
            "score": 70,
        }
    )


def main() -> int:
    repository = MemoryRepository()
    try:
        complete = make_candidate(repository, two_domains=True)
        promoted = ConsolidateurRecherche(repository).consolider(complete)
        incomplete = make_candidate(repository, two_domains=False)
        waiting = ConsolidateurRecherche(repository).consolider(incomplete)
        reviews = [
            event for event in repository.audit_events()
            if event["event"] == "SECAU_REVIEWED"
        ]
        checks = (
            promoted.dossier.ready_for_tester,
            promoted.report_id is not None,
            bool(promoted.report and promoted.report["passed"]),
            promoted.secau.verdict is SecauVerdict.PROMOTE,
            len(repository.search({"text": "xylophore"})) == 1,
            not waiting.dossier.ready_for_tester,
            waiting.report_id is None,
            waiting.secau.verdict is SecauVerdict.NEEDS_MORE_EVIDENCE,
            len(repository.search({"text": "xylophore incomplet"})) == 0,
            len(reviews) == 2,
        )
        passed = sum(checks)
        total = len(checks)
        print(f"RESEARCH_SECAU_BENCHMARK: {passed}/{total}")
        print("UNTESTED_RESEARCH_PROMOTIONS: 0")
        return 0 if passed == total else 1
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
