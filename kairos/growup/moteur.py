"""Orchestrateur de la croissance contrôlée de K.A.I.R.O.S."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable

from .collecteur import Collecteur
from .consolidateur import Consolidateur
from .modeles import PreuveApprentissage, RapportGrowUp, ResultatConsolidation
from .planificateur import Planificateur
from .priorite import Priorite
from .regroupement import Regroupement
from .stockage import StockageGrowUp
from ..decision import StockageDecision
from ..memory import MemoryRepository
from ..relations_verbes import MemoireRelationsVerbes


class MoteurGrowUp:
    """Collecte, regroupe et planifie avant toute consolidation explicite."""

    def __init__(
        self,
        decision_storage: StockageDecision,
        *,
        cognitive_repository: MemoryRepository | None = None,
        growup_storage: StockageGrowUp | None = None,
        relations_memory: MemoireRelationsVerbes | None = None,
    ) -> None:
        self.decision_storage = decision_storage
        self.cognitive_repository = cognitive_repository or MemoryRepository()
        self.stockage = growup_storage or StockageGrowUp()
        self.relations = relations_memory or MemoireRelationsVerbes()
        self.collecteur = Collecteur(decision_storage)
        self.regroupement = Regroupement()
        self.priorite = Priorite()
        self.planificateur = Planificateur()
        self.consolidateur = Consolidateur(
            self.cognitive_repository,
            self.stockage,
            self.relations,
        )

    def analyser(self) -> RapportGrowUp:
        """Produit et trace des plans sans modifier la mémoire confirmée."""

        observations = self.collecteur.collecter()
        groupes = self.regroupement.regrouper(observations)
        plans = []
        for groupe in groupes:
            score = self.priorite.calculer(groupe)
            plan = self.planificateur.planifier(groupe, score)
            self.stockage.sauvegarder_groupe(groupe)
            plans.append(self.stockage.sauvegarder_plan(plan))

        couples = sorted(
            zip(groupes, plans, strict=True),
            key=lambda couple: couple[1].priorite.total,
            reverse=True,
        )
        groupes_tries = tuple(groupe for groupe, _ in couples)
        plans_tries = tuple(plan for _, plan in couples)
        run_id = f"growup_run_{uuid.uuid4().hex}"
        rapport = RapportGrowUp(
            run_id=run_id,
            observations=len(observations),
            groupes=groupes_tries,
            plans=plans_tries,
        )
        self.stockage.sauvegarder_run(run_id, rapport.vers_dict())
        return rapport

    def consolider_relation(
        self,
        plan_id: str,
        *,
        preuves: Iterable[PreuveApprentissage],
        exemples: Iterable[str],
        contre_exemples: Iterable[str],
        resolver: Callable[[str], str | None],
        regressions: Iterable[Callable[[], bool]] = (),
    ) -> ResultatConsolidation:
        """Charge un plan traçable et l'envoie aux portes cognitives."""

        plan = self.stockage.plan(plan_id)
        if plan is None:
            raise KeyError(f"Plan GrowUp inconnu : {plan_id}")
        groupe = self.stockage.groupe(plan.groupe_id)
        if groupe is None:
            raise KeyError(f"Groupe GrowUp inconnu : {plan.groupe_id}")
        return self.consolidateur.consolider_relation(
            groupe,
            plan,
            preuves=preuves,
            exemples=exemples,
            contre_exemples=contre_exemples,
            resolver=resolver,
            regressions=regressions,
        )
