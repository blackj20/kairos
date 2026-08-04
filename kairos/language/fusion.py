"""Fusion prudente entre l'analyse symbolique et une proposition LLM."""

from __future__ import annotations

from dataclasses import replace

from ..modeles import Analyse, Estimation
from .modeles import LectureLangage


_TYPES = {
    "action_request": "ordre",
    "command": "ordre",
    "commande": "ordre",
    "ordre": "ordre",
    "prohibition": "interdiction",
    "interdiction": "interdiction",
    "information_question": "question",
    "question_information": "question",
    "capability_question": "question",
    "question_capacite": "question",
    "question": "question",
    "statement": "affirmation",
    "affirmation": "affirmation",
    "lesson": "lecon",
    "leçon": "lecon",
    "lecon": "lecon",
}


class FusionLangage:
    """Le LLM propose ; Kairos conserve la trace et applique un seuil."""

    def __init__(self, seuil: int = 70) -> None:
        if not 0 <= seuil <= 100:
            raise ValueError("Le seuil de fusion doit être entre 0 et 100.")
        self.seuil = seuil

    def fusionner(self, analyse: Analyse, lecture: LectureLangage) -> Analyse:
        metadata = {
            "provider": "local_llm",
            "model": lecture.modele,
            "confidence": lecture.confiance,
            "accepted": lecture.confiance >= self.seuil,
            "missing_information": list(lecture.informations_manquantes),
            "relation_candidates": [
                {
                    "source": relation.source,
                    "relation": relation.relation,
                    "target": relation.cible,
                    "confidence": relation.confiance,
                    "status": "candidate",
                }
                for relation in lecture.relations
            ],
        }
        cognition = dict(analyse.cognition)
        cognition["language_model"] = metadata
        indices = list(analyse.indices)
        indices.append(
            f"moteur linguistique {lecture.modele} : "
            f"{lecture.confiance}% ({'accepté' if metadata['accepted'] else 'observé'})"
        )

        if lecture.confiance < self.seuil:
            return replace(
                analyse,
                indices=tuple(indices),
                cognition=cognition,
            )

        request_type = self._type(lecture)
        action = lecture.action or analyse.action.valeur
        target = lecture.cible or analyse.cible.valeur
        approach = lecture.demarche or analyse.demarche.valeur
        confidence = lecture.confiance

        return replace(
            analyse,
            type_requete=Estimation(
                request_type or analyse.type_requete.valeur,
                max(analyse.type_requete.score, confidence if request_type else 0),
            ),
            demarche=Estimation(
                approach,
                max(analyse.demarche.score, confidence if approach else 0),
            ),
            action=Estimation(
                action,
                max(analyse.action.score, confidence if action else 0),
            ),
            cible=Estimation(
                target,
                max(analyse.cible.score, confidence if target else 0),
            ),
            indices=tuple(indices),
            cognition=cognition,
        )

    @staticmethod
    def _type(lecture: LectureLangage) -> str | None:
        if lecture.negation and lecture.action:
            return "interdiction"
        raw = str(lecture.type_requete or "").casefold().strip().replace(" ", "_")
        return _TYPES.get(raw)
