"""Création ciblée des demandes de clarification ou d'explication."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .configuration import ConfigurationDecision
from .modeles import (
    EvaluationDecision,
    EvenementApprentissage,
    QuestionEnAttente,
    Route,
    RouteChoisie,
)
from .stockage import StockageDecision


class Demande:
    """Seul composant autorisé à créer une question en attente."""

    def __init__(
        self,
        stockage: StockageDecision,
        configuration: ConfigurationDecision | None = None,
    ) -> None:
        self.stockage = stockage
        self.configuration = configuration or ConfigurationDecision()

    def creer(
        self,
        evaluation: EvaluationDecision,
        route: RouteChoisie,
    ) -> QuestionEnAttente:
        champ = self._champ_question(evaluation, route.route)
        mode = self._mode_question(evaluation, route.route)
        correction = self._correction_candidate(evaluation)
        if champ == "confirmation" and correction is not None:
            source, cible = correction
            texte = (
                f"As-tu voulu écrire « {cible} » à la place de « {source} » ?"
            )
        else:
            modele = self.configuration.questions[champ][mode]
            texte = modele.format(
                action=evaluation.analyse.action.valeur or "inconnue",
                focus=evaluation.focus or "cet élément",
                proposed_route=evaluation.analyse.verification.route,
            )
        maintenant = datetime.now(timezone.utc).isoformat()
        question = QuestionEnAttente(
            id=f"question_{uuid4().hex}",
            requete_originale=evaluation.analyse.texte_original,
            champ_manquant=champ,
            texte=texte,
            statut="waiting_answer",
            score_initial=evaluation.score_global,
            route_proposee=route.route.value,
            analyse=evaluation.analyse.vers_dict(),
            creee_le=maintenant,
        )
        self.stockage.sauvegarder_question(question)

        if evaluation.score_global <= self.configuration.seuils["study_max"]:
            evenement = EvenementApprentissage(
                id=f"learning_{uuid4().hex}",
                requete=evaluation.analyse.texte_original,
                score=evaluation.score_global,
                champ=champ,
                focus=evaluation.focus,
                question_id=question.id,
                priorite=(
                    "high"
                    if evaluation.score_global
                    <= self.configuration.seuils["priority_study_max"]
                    else "normal"
                ),
                statut="to_study",
                occurrences=1,
                cree_le=maintenant,
            )
            self.stockage.sauvegarder_apprentissage(evenement)

        return question

    @staticmethod
    def _correction_candidate(
        evaluation: EvaluationDecision,
    ) -> tuple[str, str] | None:
        """Extrait une relation orthographique des indices explicables."""

        for indice in evaluation.analyse.indices:
            if (
                "correction orthographique candidate" not in indice
                or "→" not in indice
            ):
                continue
            relation = indice.rsplit(":", 1)[-1].strip()
            source, _, cible = relation.partition("→")
            if source.strip() and cible.strip():
                return source.strip(), cible.strip()
        return None

    @staticmethod
    def _champ_question(
        evaluation: EvaluationDecision, route: Route
    ) -> str:
        if evaluation.contradictions:
            return "contradiction"
        if route == Route.CONFIRMER:
            return "confirmation"
        if evaluation.champs_manquants:
            return evaluation.champs_manquants[0]
        return "type_requete"

    def _mode_question(
        self,
        evaluation: EvaluationDecision,
        route: Route,
    ) -> str:
        if (
            route == Route.ETUDIER
            or evaluation.score_global
            <= self.configuration.seuils["priority_study_max"]
        ):
            return "explanation"
        return "clarification"
