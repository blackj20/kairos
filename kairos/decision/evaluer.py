"""Évaluation de la complétude et des prochaines actions possibles."""

from __future__ import annotations

from .configuration import ConfigurationDecision
from .modeles import ActionSuivante, EvaluationDecision
from ..modeles import Analyse


class Evaluer:
    """Mesure sans choisir, parler ou modifier une donnée."""

    def __init__(
        self, configuration: ConfigurationDecision | None = None
    ) -> None:
        self.configuration = configuration or ConfigurationDecision()

    def analyser(self, analyse: Analyse) -> EvaluationDecision:
        type_requete = self._type_effectif(analyse)
        manquants: list[str] = []
        contradictions: list[str] = []
        indices: list[str] = []

        if type_requete == "inconnu":
            manquants.append(
                "sens" if analyse.jetons_inconnus else "type_requete"
            )

        if type_requete in {"ordre", "interdiction"}:
            if analyse.action.valeur is None or analyse.action.score < 51:
                manquants.append("action")
            elif type_requete == "ordre" and self._cible_requise(analyse.action.valeur) and (
                analyse.cible.valeur is None
                or (
                    analyse.cible.score < 51
                    and not self._accepte_cible_inconnue(
                        analyse.action.valeur
                    )
                )
            ):
                manquants.append("cible")

        if any(
            "plusieurs actions détectées" in indice
            for indice in analyse.indices
        ):
            contradictions.append("plusieurs_actions")

        score = self._score_global(analyse, tuple(manquants))
        if (
            not manquants
            and analyse.action.valeur is not None
            and analyse.cible.valeur is not None
            and self._accepte_cible_inconnue(analyse.action.valeur)
        ):
            # Le terme reste sémantiquement inconnu, mais il est une cible
            # textuelle complète pour une opération de recherche en lecture.
            score = max(score, self.configuration.seuils["authorize_min"])
        if (
            not manquants
            and analyse.cognition.get("intention") == "demande_indirecte"
            and analyse.cognition.get("choix_recommande")
            == "executer_si_route_autorisee"
            and int(analyse.cognition.get("risque_score", 100))
            < int(analyse.cognition.get("seuil_confirmation", 80))
        ):
            # Une forme polie complète ne doit pas perdre des points parce
            # que l'impératif n'est pas en première position. Les permissions
            # finales restent contrôlées par VerifierDecision.
            score = max(score, self.configuration.seuils["authorize_min"])

        focus = self._choisir_focus(analyse, tuple(manquants))
        actions = self._actions_possibles(
            analyse,
            score,
            tuple(manquants),
            tuple(contradictions),
        )

        if manquants:
            indices.append(
                "champs manquants : " + ", ".join(manquants)
            )
        if contradictions:
            indices.append(
                "contradictions : " + ", ".join(contradictions)
            )
        indices.append(f"score décisionnel global : {score}")

        return EvaluationDecision(
            analyse=analyse,
            score_global=score,
            champs_manquants=tuple(manquants),
            contradictions=tuple(contradictions),
            actions_suivantes=actions,
            focus=focus,
            indices=tuple(indices),
        )

    def _cible_requise(self, action: str) -> bool:
        return action in self.configuration.routes["actions_requiring_target"]

    def _accepte_cible_inconnue(self, action: str) -> bool:
        """Une recherche peut viser un terme sans déjà en connaître le sens."""

        return action in self.configuration.routes.get(
            "actions_accepting_unknown_target", ()
        )

    def _score_global(
        self, analyse: Analyse, manquants: tuple[str, ...]
    ) -> int:
        type_requete = self._type_effectif(analyse)
        type_score = analyse.type_requete.score
        if type_requete != (analyse.type_requete.valeur or "inconnu"):
            type_score = max(
                type_score,
                int(analyse.cognition.get("intention_score", 0)),
            )
        if type_requete == "inconnu":
            return type_score

        if type_requete in {"ordre", "interdiction"}:
            if (
                type_requete == "ordre"
                and analyse.action.valeur
                in self.configuration.routes["actions_requiring_target"]
            ):
                cible_score = analyse.cible.score
                if (
                    analyse.cible.valeur is not None
                    and self._accepte_cible_inconnue(
                        str(analyse.action.valeur)
                    )
                ):
                    cible_score = max(cible_score, 80)
                score = round(
                    0.40 * type_score
                    + 0.35 * analyse.action.score
                    + 0.25 * cible_score
                )
                if type_requete == "interdiction" and not manquants:
                    score += 5
            else:
                score = round(
                    0.55 * type_score
                    + 0.45 * analyse.action.score
                )
                if not manquants:
                    score += 10
            return max(0, min(score, 100))

        bonus_completude = 0 if manquants else 10
        return min(100, type_score + bonus_completude)

    def _actions_possibles(
        self,
        analyse: Analyse,
        score: int,
        manquants: tuple[str, ...],
        contradictions: tuple[str, ...],
    ) -> tuple[ActionSuivante, ...]:
        seuils = self.configuration.seuils
        choix_cognitif = str(
            analyse.cognition.get("choix_recommande", "")
        )
        if choix_cognitif == "refuser":
            return (
                ActionSuivante(
                    "refuser",
                    100,
                    ("filtre cognitif de prévention du dommage",),
                ),
            )
        if contradictions:
            return (
                ActionSuivante(
                    "clarification",
                    100,
                    ("contradiction détectée",),
                ),
                ActionSuivante(
                    "competence",
                    0,
                    ("exécution interdite avec plusieurs actions",),
                ),
            )

        if manquants:
            if not analyse.decoupage or not analyse.decoupage.mots:
                return (
                    ActionSuivante(
                        "clarification",
                        100,
                        ("requête vide",),
                    ),
                )
            if score <= seuils["priority_study_max"]:
                return (
                    ActionSuivante(
                        "etudier",
                        100,
                        ("compréhension très faible",),
                    ),
                    ActionSuivante(
                        "clarification",
                        90,
                        ("explication nécessaire",),
                    ),
                )
            return (
                ActionSuivante(
                    "clarification",
                    100,
                    ("information obligatoire manquante",),
                ),
                ActionSuivante(
                    "confirmer",
                    40,
                    ("confirmation insuffisante sans champ complet",),
                ),
            )

        if choix_cognitif == "confirmer":
            return (
                ActionSuivante(
                    "confirmer",
                    100,
                    ("risque élevé : confirmation explicite obligatoire",),
                ),
            )

        structure = str(
            analyse.cognition.get("structure_intention", "")
        )
        intention = str(analyse.cognition.get("intention", ""))
        reponse_cognitive = (
            choix_cognitif == "repondre"
            and (
                intention in {"besoin_exprime", "envie_exprimee"}
                or structure
                in {"question_capacite", "question_information"}
            )
        )
        route_analyse = (
            "competence"
            if self._type_effectif(analyse) == "ordre"
            else "repondre"
            if reponse_cognitive
            else analyse.verification.route
        )
        if score >= seuils["authorize_min"]:
            return (
                ActionSuivante(
                    route_analyse,
                    score,
                    ("analyse complète et seuil atteint",),
                ),
                ActionSuivante(
                    "confirmer",
                    100 - score,
                    ("alternative prudente",),
                ),
            )
        if score >= seuils["confirm_min"]:
            return (
                ActionSuivante(
                    "confirmer",
                    100,
                    ("score intermédiaire",),
                ),
            )
        if score >= seuils["clarify_min"]:
            return (
                ActionSuivante(
                    "clarification",
                    100,
                    ("score faible",),
                ),
            )
        return (
            ActionSuivante(
                "etudier",
                100,
                ("score très faible",),
            ),
        )

    @staticmethod
    def _type_effectif(analyse: Analyse) -> str:
        if analyse.cognition.get("intention") == "demande_indirecte":
            return "ordre"
        return str(analyse.type_requete.valeur or "inconnu")

    @staticmethod
    def _choisir_focus(
        analyse: Analyse, manquants: tuple[str, ...]
    ) -> str | None:
        if "sens" in manquants and analyse.jetons_inconnus:
            return analyse.jetons_inconnus[-1]
        if "cible" in manquants:
            return analyse.action.valeur
        if "action" in manquants:
            return analyse.texte_normalise
        return None
