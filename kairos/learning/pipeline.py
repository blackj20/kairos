"""Orchestrateur complet Acquire → Extract → Relier → SECAU."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from ..cognition import Reflechir, Relier, Secau, SecauResult, Tester
from ..memory import MemoryRepository
from ..relations_verbes import MemoireRelationsVerbes
from .extract import Extractor
from .internet import InternetAcquire


@dataclass(frozen=True, slots=True)
class LearningResult:
    """Tous les artefacts produits par une tentative d'apprentissage."""

    evidence_ids: tuple[str, ...]
    hypothesis_id: str
    report_id: str
    secau: SecauResult
    candidate: dict[str, Any]


class InternetLearningPipeline:
    """Exécute la chaîne complète sans raccourci vers la mémoire confirmée."""

    def __init__(
        self,
        repository: MemoryRepository,
        acquire: InternetAcquire,
        relations_memory: MemoireRelationsVerbes | None = None,
    ) -> None:
        self.repository = repository
        self.acquire = acquire
        self.extractor = Extractor()
        self.relier = Relier()
        self.reflechir = Reflechir(repository)
        self.tester = Tester(repository)
        self.secau = Secau(repository)
        self.relations_memory = relations_memory

    def learn_relation(
        self,
        urls: tuple[str, ...],
        resolver_factory: Callable[[dict[str, Any]], Callable[[str], str | None]],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> LearningResult:
        """Apprend une unique relation concordante depuis plusieurs domaines."""

        documents = self.acquire.fetch_many(urls)
        extractions = [
            relation
            for document in documents
            for relation in self.extractor.extract_relations(
                document.content,
                document.evidence_id,
            )
        ]
        candidates = self.relier.relations(extractions)
        if len(candidates) != 1:
            raise ValueError(
                "Les sources doivent produire une relation concordante unique."
            )
        candidate = candidates[0]
        experience_id = f"internet_learning_{uuid.uuid4().hex}"
        hypothesis_id = self.reflechir.relation_candidate(
            experience_id,
            candidate,
        )
        resolver = resolver_factory(candidate)
        report_id, _ = self.tester.test_relation(
            hypothesis_id,
            candidate,
            resolver,
            regressions,
        )
        verdict = self.secau.review_relation(hypothesis_id, report_id)
        if (
            verdict.verdict.value == "promote"
            and self.relations_memory is not None
        ):
            self.relations_memory.enseigner(
                candidate["source"],
                candidate["target"],
                provenance=" | ".join(document.url for document in documents),
                score=70,
            )
        return LearningResult(
            tuple(document.evidence_id for document in documents),
            hypothesis_id,
            report_id,
            verdict,
            candidate,
        )
