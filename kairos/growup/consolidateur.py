"""Consolidation contrôlée : Réfléchir → Tester → SECAU."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from urllib.parse import urlparse

from .modeles import (
    GroupeApprentissage,
    PlanApprentissage,
    PreuveApprentissage,
    ResultatConsolidation,
)
from .stockage import StockageGrowUp
from ..cognition import Reflechir, Secau, Tester
from ..memory import MemoryRepository
from ..relations_verbes import MemoireRelationsVerbes


class Consolidateur:
    """Seul organe GrowUp autorisé à demander une promotion à SECAU."""

    def __init__(
        self,
        repository: MemoryRepository,
        stockage: StockageGrowUp,
        relations: MemoireRelationsVerbes,
    ) -> None:
        self.repository = repository
        self.stockage = stockage
        self.relations = relations
        self.reflechir = Reflechir(repository)
        self.tester = Tester(repository)
        self.secau = Secau(repository)

    @staticmethod
    def _verifier_preuves(preuves: tuple[PreuveApprentissage, ...]) -> None:
        references = tuple(dict.fromkeys(preuve.source_ref for preuve in preuves))
        if len(references) < 2:
            raise ValueError("Une consolidation exige deux preuves indépendantes.")

        urls = [urlparse(reference) for reference in references if "://" in reference]
        web = [url for url in urls if url.scheme in {"http", "https"}]
        if web:
            if len(web) != len(references) or any(url.scheme != "https" for url in web):
                raise ValueError("Les preuves Internet doivent toutes utiliser HTTPS.")
            domaines = {url.hostname for url in web if url.hostname}
            if len(domaines) < 2:
                raise ValueError(
                    "Les preuves Internet doivent provenir de deux domaines distincts."
                )

    def consolider_relation(
        self,
        groupe: GroupeApprentissage,
        plan: PlanApprentissage,
        *,
        preuves: Iterable[PreuveApprentissage],
        exemples: Iterable[str],
        contre_exemples: Iterable[str],
        resolver: Callable[[str], str | None],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> ResultatConsolidation:
        if plan.groupe_id != groupe.id:
            raise ValueError("Le plan ne correspond pas au groupe fourni.")
        if plan.statut not in {"planned", "needs_more_evidence"}:
            raise ValueError(f"Plan non consolidable dans l'état {plan.statut!r}.")
        if groupe.contradictions:
            raise ValueError("Une contradiction doit être résolue avant les tests.")
        if not groupe.relation_source or not groupe.relation_target:
            raise ValueError("Le groupe ne contient pas de relation candidate complète.")
        if groupe.occurrences < 3:
            raise ValueError("Trois occurrences sont requises avant consolidation.")
        if not groupe.experience_ids:
            raise ValueError("La relation doit provenir d'au moins une expérience.")

        preuves_tuple = tuple(preuves)
        self._verifier_preuves(preuves_tuple)
        exemples_tuple = tuple(dict.fromkeys(item.strip() for item in exemples if item.strip()))
        contre_tuple = tuple(
            dict.fromkeys(item.strip() for item in contre_exemples if item.strip())
        )
        if len(exemples_tuple) < 3 or len(contre_tuple) < 2:
            raise ValueError("Il faut trois exemples et deux contre-exemples distincts.")

        evidence_ids = [
            self.repository.add_evidence(
                preuve.source_type,
                preuve.source_ref,
                preuve.contenu,
                preuve.confiance,
            )
            for preuve in preuves_tuple
        ]
        candidate = {
            "source": groupe.relation_source,
            "relation": "equivalent_appris",
            "target": groupe.relation_target,
            "evidence_ids": evidence_ids,
            "examples": list(exemples_tuple),
            "counterexamples": list(contre_tuple),
            "score": plan.priorite.total,
        }
        hypothesis_id = self.reflechir.relation_candidate(
            groupe.experience_ids[0],
            candidate,
        )
        report_id, _ = self.tester.test_relation(
            hypothesis_id,
            candidate,
            resolver,
            regressions,
        )
        verdict = self.secau.review_relation(hypothesis_id, report_id)
        statut = {
            "promote": "promoted",
            "reject": "rejected",
            "quarantine": "quarantined",
            "needs_more_evidence": "needs_more_evidence",
        }[verdict.verdict.value]

        if verdict.verdict.value == "promote":
            self.relations.enseigner(
                groupe.relation_source,
                groupe.relation_target,
                provenance=" | ".join(preuve.source_ref for preuve in preuves_tuple),
                score=70,
            )
        self.stockage.changer_statut_plan(
            plan.id,
            statut,
            {
                "hypothesis_id": hypothesis_id,
                "report_id": report_id,
                "verdict": verdict.verdict.value,
                "relation_id": verdict.concept_id,
            },
        )
        return ResultatConsolidation(
            plan_id=plan.id,
            hypothesis_id=hypothesis_id,
            report_id=report_id,
            verdict=verdict.verdict.value,
            raison=verdict.reason,
            relation_id=verdict.concept_id,
        )
