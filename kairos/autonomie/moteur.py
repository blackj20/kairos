"""Gestion bornée des buts, événements et de l'attention."""

from __future__ import annotations

from typing import Any

from ..causal import MoteurCausal
from ..routing import StatutRoute
from .modeles import (
    But,
    ChoixAttention,
    ResultatCycle,
    StatutBut,
    TypeEvenementBut,
)
from .stockage import StockageButs


class GestionnaireAttention:
    """Choisit un but sans exécuter d'action."""

    @staticmethod
    def choisir(buts: list[But]) -> ChoixAttention | None:
        if not buts:
            return None

        def score(but: But) -> int:
            bonus_reprise = 10 if but.statut is StatutBut.ACTIVE else 0
            cout_etapes = but.etapes_utilisees * 3
            return but.priorite + bonus_reprise - cout_etapes

        but = max(
            buts,
            key=lambda item: (
                score(item),
                -item.etapes_utilisees,
                item.created_at,
            ),
        )
        raisons = [
            f"priorité={but.priorite}",
            f"statut={but.statut.value}",
            f"budget_restant={but.max_etapes - but.etapes_utilisees}",
        ]
        if but.statut is StatutBut.ACTIVE:
            raisons.append("reprise_d_un_objectif_actif")
        return ChoixAttention(
            goal_id=but.id,
            action="execute_causal_step",
            score=score(but),
            raisons=tuple(raisons),
            contexte={
                "mission": but.mission,
                "action": but.action,
                "target": but.cible,
            },
        )


class MoteurAutonomie:
    """Exécute des cycles explicites; ne crée jamais de daemon."""

    ERREURS_BLOQUANTES = {
        "information_not_found",
        "missing_outcome_contract",
        "output_contract_violation",
        "route_not_executed",
        "goal_condition_failed",
    }

    def __init__(
        self,
        *,
        causal: MoteurCausal | None = None,
        stockage: StockageButs | None = None,
    ) -> None:
        self.causal = causal or MoteurCausal()
        self.stockage = stockage or StockageButs()
        self.attention = GestionnaireAttention()
        self._owns_causal = causal is None
        self._owns_stockage = stockage is None

    def creer_but(
        self,
        mission: str,
        *,
        priorite: int = 50,
        max_etapes: int = 3,
    ) -> But:
        analyse = self.causal.kernel.comprendre.analyser(mission)
        action = analyse.action.valeur
        cible = analyse.cible.valeur
        return self.stockage.creer(
            mission,
            str(action) if action else None,
            str(cible) if cible else None,
            priorite=priorite,
            max_etapes=max_etapes,
        )

    def selectionner(self) -> ChoixAttention | None:
        choix = self.attention.choisir(self.stockage.eligibles())
        if choix is not None:
            self.stockage.evenement(
                choix.goal_id,
                TypeEvenementBut.ATTENTION_SELECTED,
                choix.vers_dict(),
            )
        return choix

    def executer_prochaine_etape(
        self,
        goal_id: str | None = None,
    ) -> ResultatCycle:
        choix = self._choix(goal_id)
        if choix is None:
            raise ValueError("Aucun but éligible.")

        but = self._exiger_but(choix.goal_id)
        if but.statut is StatutBut.PENDING:
            but = self.stockage.transition(
                but.id,
                StatutBut.ACTIVE,
                TypeEvenementBut.ACTIVATED,
                {"reason": "première étape autorisée"},
            )
        else:
            self.stockage.evenement(
                but.id,
                TypeEvenementBut.RESUMED,
                {"reason": "reprise explicite"},
            )

        if but.etapes_utilisees >= but.max_etapes:
            but = self._bloquer_budget(but)
            return self._resultat(but, choix, None)

        raison_blocage = self._verifier_executable(but)
        if raison_blocage is not None:
            but = self.stockage.transition(
                but.id,
                StatutBut.BLOCKED,
                TypeEvenementBut.BLOCKED,
                {"reason": raison_blocage},
            )
            return self._resultat(but, choix, None)

        self.stockage.commencer_etape(but.id, choix.vers_dict())
        episode = self.causal.executer_message(but.mission)
        evaluation = dict(episode.get("evaluation") or {})
        but = self.stockage.enregistrer_episode(
            but.id, str(episode["id"]), evaluation
        )

        if bool(evaluation.get("objectif_atteint")):
            but = self.stockage.transition(
                but.id,
                StatutBut.COMPLETED,
                TypeEvenementBut.COMPLETED,
                {
                    "reason": "objectif causal atteint",
                    "episode_id": episode["id"],
                    "score": evaluation.get("score_resultat", 0),
                },
            )
        else:
            erreurs = {
                str(item) for item in evaluation.get("erreurs", [])
            }
            bloquantes = sorted(erreurs & self.ERREURS_BLOQUANTES)
            if bloquantes:
                but = self.stockage.transition(
                    but.id,
                    StatutBut.BLOCKED,
                    TypeEvenementBut.BLOCKED,
                    {
                        "reason": ",".join(bloquantes),
                        "episode_id": episode["id"],
                    },
                )
            elif but.etapes_utilisees >= but.max_etapes:
                but = self._bloquer_budget(but)

        return self._resultat(but, choix, episode)

    def executer_jusqua_terminal(
        self,
        goal_id: str,
    ) -> ResultatCycle:
        resultat: ResultatCycle | None = None
        while True:
            but = self._exiger_but(goal_id)
            if but.statut.terminal:
                return self._resultat(but, None, None) if resultat is None else resultat
            resultat = self.executer_prochaine_etape(goal_id)
            if resultat.but.statut.terminal:
                return resultat

    def lancer(
        self,
        mission: str,
        *,
        priorite: int = 50,
        max_etapes: int = 3,
    ) -> ResultatCycle:
        but = self.creer_but(
            mission, priorite=priorite, max_etapes=max_etapes
        )
        return self.executer_jusqua_terminal(but.id)

    def invalider(self, goal_id: str, raison: str) -> But:
        but = self._exiger_but(goal_id)
        if but.statut.terminal:
            raise ValueError("Un but terminal ne peut plus être invalidé.")
        return self.stockage.transition(
            but.id,
            StatutBut.INVALIDATED,
            TypeEvenementBut.INVALIDATED,
            {"reason": raison.strip() or "prédiction invalidée"},
        )

    def statut(self, goal_id: str | None = None) -> dict[str, Any]:
        but = self.stockage.but(goal_id) if goal_id else self.stockage.dernier()
        if but is None:
            return {"goal": None, "events": []}
        return {
            "goal": but.vers_dict(),
            "events": self.stockage.evenements(but.id),
        }

    def _choix(self, goal_id: str | None) -> ChoixAttention | None:
        if goal_id is None:
            return self.selectionner()
        but = self._exiger_but(goal_id)
        if but.statut.terminal:
            raise ValueError(f"Le but est déjà terminal : {but.statut.value}.")
        choix = self.attention.choisir([but])
        assert choix is not None
        self.stockage.evenement(
            but.id, TypeEvenementBut.ATTENTION_SELECTED, choix.vers_dict()
        )
        return choix

    def _verifier_executable(self, but: But) -> str | None:
        if not but.action:
            return "action_missing"
        plan = self.causal.kernel.routeur.planifier(but.action, but.cible)
        if plan.statut is not StatutRoute.READY:
            return f"route_{plan.statut.value}"
        prediction = self.causal.predicteur.predire(plan)
        if not prediction.contrat_disponible:
            return "missing_outcome_contract"
        return None

    def _bloquer_budget(self, but: But) -> But:
        self.stockage.evenement(
            but.id,
            TypeEvenementBut.BUDGET_EXHAUSTED,
            {
                "used": but.etapes_utilisees,
                "maximum": but.max_etapes,
            },
        )
        return self.stockage.transition(
            but.id,
            StatutBut.BLOCKED,
            TypeEvenementBut.BLOCKED,
            {"reason": "budget_exhausted"},
        )

    def _resultat(
        self,
        but: But,
        choix: ChoixAttention | None,
        episode: dict[str, Any] | None,
    ) -> ResultatCycle:
        return ResultatCycle(
            but=but,
            choix=choix,
            episode=episode,
            evenements=tuple(self.stockage.evenements(but.id)),
        )

    def _exiger_but(self, goal_id: str) -> But:
        but = self.stockage.but(goal_id)
        if but is None:
            raise KeyError(goal_id)
        return but

    def close(self) -> None:
        if self._owns_causal:
            self.causal.close()
        if self._owns_stockage:
            self.stockage.close()
