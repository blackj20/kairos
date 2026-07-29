"""Consolidation contrôlée des hypothèses créées par Information Search."""

from __future__ import annotations

import urllib.parse
from dataclasses import asdict, dataclass
from typing import Any

from ..cognition import Secau, SecauResult, Tester
from ..memory import MemoryRepository


@dataclass(frozen=True, slots=True)
class DossierRecherche:
    hypothesis_id: str
    target: str
    evidence_count: int
    source_count: int
    claim_count: int
    independent_domains: int
    missing: tuple[str, ...]
    ready_for_tester: bool

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResultatConsolidationRecherche:
    dossier: DossierRecherche
    report_id: str | None
    report: dict[str, Any] | None
    secau: SecauResult

    def vers_dict(self) -> dict[str, Any]:
        return {
            "dossier": self.dossier.vers_dict(),
            "report_id": self.report_id,
            "report": self.report,
            "secau": self.secau.vers_dict(),
        }


class ConsolidateurRecherche:
    """Prépare, teste puis soumet une candidate exacte à SECAU."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository
        self.tester = Tester(repository)
        self.secau = Secau(repository)

    def preparer(self, hypothesis_id: str) -> DossierRecherche:
        hypothesis = self.repository.hypothesis(hypothesis_id)
        if hypothesis is None:
            raise KeyError(hypothesis_id)
        payload = hypothesis["payload"]
        if payload.get("research_kind") != "information.search":
            raise ValueError("Cette hypothèse ne provient pas d'une recherche.")
        evidence_ids = tuple(str(item) for item in payload.get("evidence_ids", ()))
        urls = tuple(str(item) for item in payload.get("source_urls", ()))
        claims = tuple(str(item) for item in payload.get("source_claims", ()))
        parsed = tuple(urllib.parse.urlparse(url) for url in urls)
        domains = {
            str(item.hostname).casefold() for item in parsed if item.hostname
        }
        missing: list[str] = []
        if len(evidence_ids) < 2:
            missing.append("deux_preuves")
        if len(urls) < 2:
            missing.append("deux_sources")
        if len(claims) < 2:
            missing.append("deux_affirmations")
        if len(domains) < 2:
            missing.append("deux_domaines_independants")
        if not (len(evidence_ids) == len(urls) == len(claims)):
            missing.append("alignement_preuves_sources")
        if any(item.scheme != "https" or not item.hostname for item in parsed):
            missing.append("sources_https")
        return DossierRecherche(
            hypothesis_id=hypothesis_id,
            target=str(payload.get("name", "")),
            evidence_count=len(evidence_ids),
            source_count=len(urls),
            claim_count=len(claims),
            independent_domains=len(domains),
            missing=tuple(dict.fromkeys(missing)),
            ready_for_tester=not missing,
        )

    def consolider(self, hypothesis_id: str) -> ResultatConsolidationRecherche:
        dossier = self.preparer(hypothesis_id)
        hypothesis = self.repository.hypothesis(hypothesis_id)
        assert hypothesis is not None
        if not dossier.ready_for_tester:
            verdict = self.secau.review_research(
                hypothesis_id,
                None,
                dossier.vers_dict(),
            )
            return ResultatConsolidationRecherche(
                dossier=dossier,
                report_id=None,
                report=None,
                secau=verdict,
            )
        report_id, report = self.tester.test_research_candidate(
            hypothesis_id,
            hypothesis["payload"],
        )
        verdict = self.secau.review_research(
            hypothesis_id,
            report_id,
            dossier.vers_dict(),
        )
        return ResultatConsolidationRecherche(
            dossier=dossier,
            report_id=report_id,
            report=report,
            secau=verdict,
        )
