"""Mesure reproductible d'un candidat."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import re
import unicodedata
import urllib.parse
from typing import Any

from ..memory import MemoryRepository


class Tester:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    @staticmethod
    def _run_case(case: Callable[[], bool]) -> tuple[bool, str | None]:
        """Transforme une exception de test en échec explicite et traçable."""

        try:
            return bool(case()), None
        except Exception as error:  # Le rapport doit survivre à un cas défectueux.
            return False, f"{type(error).__name__}: {error}"

    def test(
        self,
        subject_id: str,
        original: Callable[[], bool],
        paraphrases: Iterable[Callable[[], bool]],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> tuple[str, dict[str, Any]]:
        original_ok, original_error = self._run_case(original)
        paraphrase_runs = [self._run_case(case) for case in paraphrases]
        regression_runs = [self._run_case(case) for case in regressions]
        paraphrase_results = [result for result, _ in paraphrase_runs]
        regression_results = [result for result, _ in regression_runs]
        report = {
            "passed": (
                original_ok
                and len(paraphrase_results) >= 3
                and all(paraphrase_results)
                and all(regression_results)
            ),
            "original": original_ok,
            "paraphrases": paraphrase_results,
            "regressions": regression_results,
            "errors": {
                "original": original_error,
                "paraphrases": [error for _, error in paraphrase_runs],
                "regressions": [error for _, error in regression_runs],
            },
        }
        return self.repository.save_report(subject_id, report), report

    def test_relation(
        self,
        subject_id: str,
        candidate: dict[str, Any],
        resolver: Callable[[str], str | None],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> tuple[str, dict[str, Any]]:
        """Teste cas positifs, négatifs et régressions sans modifier le candidat."""

        target = str(candidate["target"])
        examples = list(candidate.get("examples", []))
        counterexamples = list(candidate.get("counterexamples", []))

        def resolve(case: str) -> tuple[str | None, str | None]:
            try:
                return resolver(case), None
            except Exception as error:
                return None, f"{type(error).__name__}: {error}"

        positive_runs = [resolve(case) for case in examples]
        negative_runs = [resolve(case) for case in counterexamples]
        positive_results = [value == target for value, _ in positive_runs]
        negative_results = [value != target and error is None for value, error in negative_runs]
        regression_runs = [self._run_case(case) for case in regressions]
        regression_results = [result for result, _ in regression_runs]
        report = {
            "passed": (
                len(candidate.get("evidence_ids", [])) >= 2
                and len(examples) >= 3
                and len(counterexamples) >= 2
                and all(positive_results)
                and all(negative_results)
                and all(regression_results)
            ),
            "evidence_count": len(candidate.get("evidence_ids", [])),
            "examples": positive_results,
            "counterexamples": negative_results,
            "regressions": regression_results,
            "errors": {
                "examples": [error for _, error in positive_runs],
                "counterexamples": [error for _, error in negative_runs],
                "regressions": [error for _, error in regression_runs],
            },
        }
        return self.repository.save_report(subject_id, report), report


    @staticmethod
    def _research_words(text: str) -> set[str]:
        normalized = unicodedata.normalize("NFKD", text.casefold())
        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        return set(re.findall(r"[a-z0-9]{3,}", normalized))

    def test_research_candidate(
        self,
        subject_id: str,
        candidate: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Mesure provenance, intégrité et cohérence lexicale d'un concept."""

        name = str(candidate.get("name", "")).strip()
        definition = str(candidate.get("definition", "")).strip()
        evidence_ids = [str(item) for item in candidate.get("evidence_ids", [])]
        urls = [str(item) for item in candidate.get("source_urls", [])]
        claims = [str(item) for item in candidate.get("source_claims", [])]
        domains = {
            str(urllib.parse.urlparse(url).hostname).casefold()
            for url in urls
            if urllib.parse.urlparse(url).hostname
        }
        https_results = [
            urllib.parse.urlparse(url).scheme == "https"
            and bool(urllib.parse.urlparse(url).hostname)
            for url in urls
        ]
        aligned = len(evidence_ids) == len(urls) == len(claims)
        integrity = [
            self.repository.evidence_matches(
                evidence_id,
                source_ref=url,
                content=claim,
            )
            for evidence_id, url, claim in zip(evidence_ids, urls, claims)
        ]
        name_words = self._research_words(name)
        definition_words = self._research_words(definition)
        subject_support = [
            bool(name_words)
            and name_words.issubset(self._research_words(claim))
            for claim in claims
        ]
        agreement = [
            (
                len(definition_words & self._research_words(claim))
                / max(1, len(definition_words))
            )
            for claim in claims
        ]
        negative_controls = {
            "http_rejected": not (
                urllib.parse.urlparse("http://invalid.example").scheme == "https"
            ),
            "blank_claim_rejected": not bool(self._research_words("")),
        }
        protected = {
            "identity",
            "objective",
            "permissions",
            "security_policy",
            "creator",
        }
        report = {
            "passed": (
                aligned
                and len(evidence_ids) >= 2
                and len(domains) >= 2
                and bool(definition_words)
                and all(https_results)
                and all(integrity)
                and all(subject_support)
                and all(score >= 0.20 for score in agreement)
                and all(negative_controls.values())
                and not protected.intersection(candidate)
            ),
            "source_count": len(urls),
            "independent_domains": len(domains),
            "aligned_artifacts": aligned,
            "https": https_results,
            "integrity": integrity,
            "subject_support": subject_support,
            "lexical_agreement": agreement,
            "negative_controls": negative_controls,
            "limitation": "cohérence vérifiée, vérité absolue non garantie",
        }
        return self.repository.save_report(subject_id, report), report
