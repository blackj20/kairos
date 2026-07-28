"""Cinquième étape de Comprendre : contrôle linguistique des scores."""

from __future__ import annotations

from .connaissances import Connaissances
from .modeles import ResultatEstimation, Verification


class VerifierAnalyse:
    """Valide une analyse linguistique sans autoriser une action réelle."""

    def __init__(self, connaissances: Connaissances) -> None:
        self.connaissances = connaissances

    def analyser(self, resultat: ResultatEstimation) -> Verification:
        seuils = self.connaissances.conditions["seuils"]
        raisons: list[str] = []
        type_requete = resultat.type_requete.valeur or "inconnu"

        if (
            type_requete == "inconnu"
            or resultat.type_requete.score < seuils["type"]
        ):
            return Verification(
                valide=False,
                route="clarification",
                score=resultat.type_requete.score,
                raisons=("type de requête insuffisamment reconnu",),
            )

        ecart = (
            resultat.type_requete.score - resultat.alternative_type.score
        )
        if ecart < seuils["ecart_hypotheses"]:
            raisons.append(
                f"écart insuffisant entre les deux hypothèses : {ecart}"
            )
            return Verification(
                valide=False,
                route="clarification",
                score=resultat.type_requete.score,
                raisons=tuple(raisons),
            )

        if (
            type_requete == "ordre"
            and resultat.action.score < seuils["action_execution"]
        ):
            return Verification(
                valide=False,
                route="clarification",
                score=resultat.action.score,
                raisons=("action trop incertaine pour être exécutée",),
            )

        route = self.connaissances.conditions["routes"][type_requete]
        score = resultat.type_requete.score
        if type_requete == "ordre":
            score = min(score, resultat.action.score)

        raisons.append(
            f"{type_requete} validé avec un écart de {ecart} points"
        )
        return Verification(
            valide=True,
            route=route,
            score=score,
            raisons=tuple(raisons),
        )
