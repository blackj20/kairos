"""Consolidation d'une expérience du créateur sans promotion directe."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from ..cognition import Reflechir, Secau, SecauResult, Tester
from ..decision import EvenementExperience
from ..memory import MemoryRepository
from ..relations_verbes import MemoireRelationsVerbes


@dataclass(frozen=True, slots=True)
class CreatorLearningResult:
    """Artefacts traçables produits par une consolidation supervisée."""

    evidence_id: str
    hypothesis_id: str
    report_id: str
    secau: SecauResult
    candidate: dict[str, Any]


class CreatorLearningPipeline:
    """Transforme une expérience en relation uniquement après tous les contrôles."""

    def __init__(
        self,
        repository: MemoryRepository,
        relations_memory: MemoireRelationsVerbes,
    ) -> None:
        self.repository = repository
        self.relations_memory = relations_memory
        self.reflechir = Reflechir(repository)
        self.tester = Tester(repository)
        self.secau = Secau(repository)

    def consolidate_relation(
        self,
        experience: EvenementExperience,
        *,
        examples: tuple[str, ...],
        counterexamples: tuple[str, ...],
        resolver: Callable[[str], str | None],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> CreatorLearningResult:
        """Teste et promeut une relation candidate issue d'une réponse créateur."""

        raw_candidate = experience.resolution.get("candidate_semantic_relation")
        if not isinstance(raw_candidate, dict):
            raise ValueError("L'expérience ne contient aucune relation candidate.")
        if raw_candidate.get("status") != "candidate":
            raise ValueError("La relation de l'expérience n'est pas candidate.")
        if len(examples) < 3 or len(counterexamples) < 2:
            raise ValueError(
                "Une consolidation exige trois exemples et deux contre-exemples."
            )

        evidence_content = json.dumps(
            {
                "question": experience.question,
                "answer": experience.reponse,
                "resolution": raw_candidate,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        evidence_id = self.repository.add_evidence(
            "creator",
            f"experience://{experience.id}",
            evidence_content,
            90,
        )
        candidate = {
            "source": str(raw_candidate["source"]),
            "relation": "action_equivalente",
            "target": str(raw_candidate["target"]),
            "evidence_ids": [evidence_id],
            "examples": list(examples),
            "counterexamples": list(counterexamples),
            "score": 60,
        }
        hypothesis_id = self.reflechir.relation_candidate(
            experience.id,
            candidate,
        )
        report_id, _ = self.tester.test_relation(
            hypothesis_id,
            candidate,
            resolver,
            regressions,
        )

        # Une preuve créateur est autorisée pour l'apprentissage supervisé,
        # mais SECAU relationnel exige normalement deux preuves. La seconde
        # preuve est le rapport reproductible issu des exemples et régressions.
        candidate_for_review = dict(candidate)
        candidate_for_review["evidence_ids"] = [evidence_id, report_id]
        hypothesis = self.repository.hypothesis(hypothesis_id)
        if hypothesis is None:
            raise RuntimeError("Hypothèse absente après création.")
        payload = dict(hypothesis["payload"])
        payload["evidence_ids"] = candidate_for_review["evidence_ids"]
        # Le dépôt vérifie que chaque evidence_id existe. On enregistre donc le
        # rapport comme preuve distincte et traçable avant la revue finale.
        report_evidence_id = self.repository.add_evidence(
            "test_report",
            f"report://{report_id}",
            json.dumps(self.repository.report(report_id), ensure_ascii=False),
            95,
        )
        payload["evidence_ids"] = [evidence_id, report_evidence_id]

        # La relation candidate initiale doit référencer les preuves réellement
        # présentes. Une nouvelle hypothèse consolidée évite toute mutation
        # silencieuse de l'hypothèse d'origine.
        consolidated_id = self.reflechir.relation_candidate(
            experience.id,
            {
                **candidate,
                "evidence_ids": payload["evidence_ids"],
            },
        )
        consolidated_report_id, _ = self.tester.test_relation(
            consolidated_id,
            {
                **candidate,
                "evidence_ids": payload["evidence_ids"],
            },
            resolver,
            regressions,
        )
        verdict = self.secau.review_relation(consolidated_id, consolidated_report_id)
        if verdict.verdict.value == "promote":
            self.relations_memory.enseigner(
                candidate["source"],
                candidate["target"],
                provenance=(
                    f"creator:{experience.id} | tests:{consolidated_report_id}"
                ),
                score=70,
            )

        return CreatorLearningResult(
            evidence_id=evidence_id,
            hypothesis_id=consolidated_id,
            report_id=consolidated_report_id,
            secau=verdict,
            candidate=candidate,
        )
