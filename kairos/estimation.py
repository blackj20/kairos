"""Quatrième étape : estimation de l'intention globale et de ses éléments."""

from __future__ import annotations

from .connaissances import Connaissances
from .modeles import (
    Decoupage,
    Estimation as Score,
    RelationSemantique,
    ResultatEstimation,
    SensContextuel,
)
from .normalisation import cle


class Estimer:
    """Transforme les sens contextualisés en hypothèses explicables."""

    def __init__(self, connaissances: Connaissances) -> None:
        self.connaissances = connaissances

    def analyser(
        self,
        decoupage: Decoupage,
        contextuels: tuple[SensContextuel, ...],
        relations: tuple[RelationSemantique, ...] = (),
    ) -> ResultatEstimation:
        if not decoupage.mots:
            return ResultatEstimation(
                type_requete=Score("inconnu", 0),
                alternative_type=Score(None, 0),
                demarche=Score("clarification", 100),
                action=Score(None, 0),
                cible=Score(None, 0),
                indices=("requête vide",),
            )

        texte = cle(decoupage.texte_normalise)
        mots = [jeton.normalise for jeton in decoupage.mots]
        ensemble_mots = set(mots)
        action, position_action, score_action, indices_action = (
            self._estimer_action(contextuels)
        )
        cible, score_cible, indices_cible = self._estimer_cible(
            contextuels, position_action
        )
        if action:
            relation_action = next(
                (
                    relation
                    for relation in relations
                    if relation.relation == action
                ),
                None,
            )
            if relation_action is not None and cible is None:
                cible = relation_action.target
                score_cible = relation_action.score
                indices_cible = [
                    f"cible relationnelle : {relation_action.target}"
                ]

        hypotheses: dict[str, int] = {"inconnu": 25}
        indices_type: list[str] = []
        expressions = self.connaissances.expressions

        salutation = bool(
            ensemble_mots
            & {cle(mot) for mot in expressions["salutations"]}
        )
        question_etat = self._contient(
            texte, expressions["questions_etat"]
        ) or any(
            element.choisi
            and element.choisi.categorie == "question_etat"
            for element in contextuels
        )
        ponctuation_question = any(
            jeton.valeur == "?" for jeton in decoupage.jetons
        )
        interrogatifs = self.connaissances.obtenir("grammaire")[
            "interrogatifs"
        ]
        interrogatif = bool(mots and mots[0] in {cle(mot) for mot in interrogatifs})

        negations = self.connaissances.obtenir("negations")
        negation_double = (
            bool(ensemble_mots & {"ne", "n"})
            and bool(ensemble_mots & {"pas", "jamais", "plus", "aucun"})
        )
        interdiction_directe = self._contient(
            texte, expressions["interdictions"]
        ) or self._contient(texte, negations["expressions"])

        retour = self._contient(
            texte,
            expressions["retours_positifs"] + expressions["retours_negatifs"],
        )
        lecon = self._contient(texte, expressions["lecons"])
        action_lecon = action in {"apprendre", "expliquer"}

        if negation_double or interdiction_directe:
            hypotheses["interdiction"] = 90
            indices_type.append("négation directive ou interdiction explicite")
            if action:
                hypotheses["ordre"] = min(65, score_action)

        if retour:
            hypotheses["retour_utilisateur"] = 88
            indices_type.append("retour positif ou correction explicite")

        if lecon or action_lecon:
            hypotheses["lecon"] = 90 if lecon else 82
            indices_type.append("demande d'explication ou d'apprentissage")

        if ponctuation_question and question_etat:
            hypotheses["question"] = 80
            indices_type.extend(
                ["point d'interrogation", "question d'état reconnue"]
            )
            if salutation:
                hypotheses["demarrage_conversation"] = 60
        elif ponctuation_question or interrogatif:
            hypotheses["question"] = 75
            indices_type.append("forme interrogative détectée")

        sujets = set(
            self.connaissances.obtenir("grammaire")["pronoms_sujets"]
        )
        sujet_avant_action = False
        action_directrice = self._action_est_initiale(
            contextuels, position_action
        )
        if position_action is not None:
            sujet_avant_action = bool(
                sujets
                & {
                    element.jeton.normalise
                    for element in contextuels
                    if element.jeton.position < position_action
                }
            ) and not action_directrice

        if (
            action
            and not sujet_avant_action
            and not (lecon or action_lecon)
            and not (negation_double or interdiction_directe)
            and not (ponctuation_question or interrogatif)
        ):
            score_ordre = 70
            if action_directrice:
                score_ordre += 10
            if cible:
                score_ordre += 5
            hypotheses["ordre"] = max(
                hypotheses.get("ordre", 0), min(score_ordre, 100)
            )
            indices_type.extend(
                ["verbe d'action directeur", "forme directive"]
            )

        verbes_etat = set(
            self.connaissances.obtenir("grammaire")["verbes_etat"]
        )
        affirmation_simple = bool(
            ensemble_mots
            & {
                cle(mot)
                for mot in self.connaissances.obtenir("affirmations")["simples"]
            }
        )
        if (
            not ponctuation_question
            and not retour
            and not salutation
            and (
                affirmation_simple
                or bool(ensemble_mots & verbes_etat)
                or (sujet_avant_action and action is not None)
            )
        ):
            hypotheses["affirmation"] = 75 if not affirmation_simple else 85
            indices_type.append("énoncé affirmatif détecté")

        if salutation and not ponctuation_question:
            hypotheses["demarrage_conversation"] = 92
            indices_type.append("salutation reconnue")

        classements = sorted(
            hypotheses.items(), key=lambda element: element[1], reverse=True
        )
        principal_nom, principal_score = classements[0]
        alternatif_nom, alternatif_score = (
            classements[1] if len(classements) > 1 else (None, 0)
        )
        demarche = self.connaissances.conditions["demarches"][principal_nom]
        score_demarche = self._score_demarche(
            principal_nom,
            principal_score,
            texte,
            salutation,
            question_etat,
            score_action,
        )

        inconnus = tuple(
            element.jeton.normalise
            for element in contextuels
            if element.choisi is None
            or element.choisi.categorie == "inconnu"
        )
        indices_contexte = [
            indice
            for element in contextuels
            for indice in element.indices
        ]

        return ResultatEstimation(
            type_requete=Score(principal_nom, principal_score),
            alternative_type=Score(alternatif_nom, alternatif_score),
            demarche=Score(demarche, score_demarche),
            action=Score(action, score_action),
            cible=Score(cible, score_cible),
            indices=tuple(
                indices_type
                + indices_action
                + indices_cible
                + indices_contexte
            ),
            jetons_inconnus=inconnus,
        )

    def _estimer_action(
        self, contextuels: tuple[SensContextuel, ...]
    ) -> tuple[str | None, int | None, int, list[str]]:
        actions = [
            element
            for element in contextuels
            if element.choisi
            and element.choisi.categorie == "verbe_action"
        ]
        if not actions:
            return None, None, 0, []

        element = actions[0]
        choisi = element.choisi
        assert choisi is not None
        if len(actions) > 1:
            return (
                choisi.lemme,
                element.jeton.position,
                40,
                ["plusieurs actions détectées : clarification obligatoire"],
            )

        # Le score lexical participe au score d'action : une correction candidate
        # reste sous le seuil, tandis qu'une relation confirmée retrouve le score
        # normal d'une forme déclarée.
        score = min(60, choisi.score)
        if self._action_est_initiale(contextuels, element.jeton.position):
            score += 10
        if any(
            autre.jeton.position > element.jeton.position
            for autre in contextuels
        ):
            score += 6
        return (
            choisi.lemme,
            element.jeton.position,
            min(score, 100),
            [f"action contextualisée : {choisi.lemme}"],
        )

    def _estimer_cible(
        self,
        contextuels: tuple[SensContextuel, ...],
        position_action: int | None,
    ) -> tuple[str | None, int, list[str]]:
        if position_action is None:
            return None, 0, []

        suivants = [
            element
            for element in contextuels
            if element.jeton.position > position_action
        ]
        for element in suivants:
            if (
                element.choisi
                and element.choisi.categorie.startswith("entite:")
            ):
                return (
                    element.choisi.lemme,
                    element.choisi.score,
                    [
                        (
                            "cible exacte reconnue"
                            if not element.choisi.source.startswith(
                                "correction_candidate:"
                            )
                            else "correction orthographique candidate"
                        )
                        + f" : {element.jeton.normalise} → "
                        + element.choisi.lemme
                    ],
                )

        ignores = (
            "articles:",
            "bruits:",
            "grammaire:",
            "negations:",
            "affirmations:",
        )
        candidats = [
            element.jeton.normalise
            for element in suivants
            if element.choisi
            and not element.choisi.categorie.startswith(ignores)
        ]
        if not candidats:
            return None, 0, []
        cible = " ".join(candidats)
        return cible, 55, [f"cible syntaxique non vérifiée : {cible}"]

    @staticmethod
    def _action_est_initiale(
        contextuels: tuple[SensContextuel, ...],
        position_action: int | None,
    ) -> bool:
        if position_action is None:
            return False
        avant = [
            element
            for element in contextuels
            if element.jeton.position < position_action
        ]
        mots_avant = [element.jeton.normalise for element in avant]
        if mots_avant in (
            ["merci", "de"],
            ["s", "il", "te", "plait"],
            ["s", "il", "vous", "plait"],
        ):
            return True
        autorises_avant = ("bruits:", "negations:")
        return all(
            element.jeton.position >= position_action
            or (
                element.choisi is not None
                and element.choisi.categorie.startswith(autorises_avant)
            )
            for element in contextuels
        )

    @staticmethod
    def _contient(texte: str, expressions: list[str]) -> bool:
        return any(cle(expression) in texte for expression in expressions)

    @staticmethod
    def _score_demarche(
        type_requete: str,
        score_type: int,
        texte: str,
        salutation: bool,
        question_etat: bool,
        score_action: int,
    ) -> int:
        if type_requete == "question" and salutation and question_etat:
            return 56
        if type_requete == "ordre":
            return score_action
        valeurs = {
            "affirmation": 70,
            "demarrage_conversation": 80,
            "interdiction": 80,
            "lecon": 85,
            "question": 60,
            "retour_utilisateur": 82,
            "inconnu": 75,
        }
        return valeurs.get(type_requete, score_type)
