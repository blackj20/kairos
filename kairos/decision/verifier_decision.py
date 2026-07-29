"""Porte finale entre une route proposée et sa mise en œuvre."""

from __future__ import annotations

from .configuration import ConfigurationDecision
from .demande import Demande
from .modeles import (
    EvaluationDecision,
    Route,
    RouteChoisie,
    VerdictDecision,
)


class VerifierDecision:
    """Valide une route ou délègue la main à Demande."""

    ROUTES_DEMANDE = {
        Route.CONFIRMER,
        Route.CLARIFIER,
        Route.ETUDIER,
    }

    def __init__(
        self,
        demande: Demande,
        configuration: ConfigurationDecision | None = None,
    ) -> None:
        self.demande = demande
        self.configuration = configuration or ConfigurationDecision()

    def verifier(
        self,
        evaluation: EvaluationDecision,
        route: RouteChoisie,
        acteur: str = "creator",
    ) -> VerdictDecision:
        route = self._corriger_route_incoherente(evaluation, route)

        autorises = self.configuration.routes["permissions"][route.route.value]
        if acteur not in autorises:
            return VerdictDecision(
                valide=False,
                route=Route.REFUSER,
                score=100,
                raison=(
                    f"le rôle « {acteur} » n'est pas autorisé "
                    f"à utiliser la route « {route.route.value} »"
                ),
            )

        if route.route in self.ROUTES_DEMANDE:
            question = self.demande.creer(evaluation, route)
            return VerdictDecision(
                valide=False,
                route=route.route,
                score=evaluation.score_global,
                raison=route.raison,
                question=question,
            )

        return VerdictDecision(
            valide=True,
            route=route.route,
            score=evaluation.score_global,
            raison=route.raison,
        )

    def _corriger_route_incoherente(
        self,
        evaluation: EvaluationDecision,
        route: RouteChoisie,
    ) -> RouteChoisie:
        type_requete = self._type_effectif(evaluation)
        seuil = self.configuration.seuils["authorize_min"]

        execution_invalide = (
            route.route == Route.EXECUTER
            and (
                type_requete != "ordre"
                or bool(evaluation.champs_manquants)
                or bool(evaluation.contradictions)
                or evaluation.score_global < seuil
            )
        )
        controle_invalide = (
            route.route == Route.CONTROLE
            and type_requete != "interdiction"
        )
        reponse_invalide = (
            route.route == Route.REPONDRE
            and type_requete in {"ordre", "interdiction", "inconnu"}
        )

        if execution_invalide or controle_invalide or reponse_invalide:
            return RouteChoisie(
                route=Route.CLARIFIER,
                score=100,
                raison="route proposée incohérente avec l'analyse",
            )
        return route

    @staticmethod
    def _type_effectif(evaluation: EvaluationDecision) -> str | None:
        if evaluation.analyse.cognition.get("intention") == "demande_indirecte":
            return "ordre"
        return evaluation.analyse.type_requete.valeur
