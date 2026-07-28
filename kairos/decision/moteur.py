"""Façade de la couche de décision V0.3."""

from __future__ import annotations

from .choisir_route import ChoisirRoute
from .configuration import ConfigurationDecision
from .demande import Demande
from .evaluer import Evaluer
from .experience import Experience
from .modeles import EvenementExperience, ProcessusDecision
from .stockage import StockageDecision, StockageJson, StockageMemoire
from .verifier_decision import VerifierDecision
from ..comprendre import Comprendre
from ..modeles import Analyse


class MoteurDecision:
    """Coordonne les organes de décision sans logique linguistique."""

    def __init__(
        self,
        comprendre: Comprendre,
        stockage: StockageDecision | None = None,
        persister: bool = False,
    ) -> None:
        self.configuration = ConfigurationDecision()
        self.stockage = stockage or (
            StockageJson() if persister else StockageMemoire()
        )
        self.evaluer = Evaluer(self.configuration)
        self.choisir_route = ChoisirRoute(self.configuration)
        self.demande = Demande(self.stockage, self.configuration)
        self.verifier = VerifierDecision(
            self.demande,
            self.configuration,
        )
        self.experience = Experience(self.stockage, comprendre)

    def decider(
        self,
        analyse: Analyse,
        acteur: str = "creator",
    ) -> ProcessusDecision:
        evaluation = self.evaluer.analyser(analyse)
        route = self.choisir_route.choisir(evaluation)
        verdict = self.verifier.verifier(evaluation, route, acteur)
        return ProcessusDecision(
            evaluation=evaluation,
            route_choisie=route,
            verdict=verdict,
        )

    def repondre_a(
        self,
        question_id: str,
        reponse: str,
        acteur: str = "creator",
    ) -> EvenementExperience:
        return self.experience.enregistrer_reponse(
            question_id,
            reponse,
            acteur,
        )
