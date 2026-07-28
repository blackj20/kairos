"""Choix pur d'une route parmi les actions estimées."""

from __future__ import annotations

from .configuration import ConfigurationDecision
from .modeles import EvaluationDecision, Route, RouteChoisie


class ChoisirRoute:
    """Choisit la meilleure route sans effectuer d'effet de bord."""

    def __init__(
        self, configuration: ConfigurationDecision | None = None
    ) -> None:
        self.configuration = configuration or ConfigurationDecision()

    def choisir(self, evaluation: EvaluationDecision) -> RouteChoisie:
        if not evaluation.actions_suivantes:
            return RouteChoisie(
                route=Route.CLARIFIER,
                score=0,
                raison="aucune action suivante estimée",
            )

        meilleure = max(
            evaluation.actions_suivantes,
            key=lambda action: action.score,
        )
        if meilleure.valeur not in self.configuration.routes["allowed"]:
            return RouteChoisie(
                route=Route.REFUSER,
                score=100,
                raison=f"route inconnue interdite : {meilleure.valeur}",
            )

        return RouteChoisie(
            route=Route(meilleure.valeur),
            score=meilleure.score,
            raison="; ".join(meilleure.raisons),
        )
