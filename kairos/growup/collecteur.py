"""Collecte en lecture seule des épisodes utiles à l'évolution."""

from __future__ import annotations

from .modeles import ObservationApprentissage
from ..decision import StockageDecision


class Collecteur:
    """Lit la mémoire de décision sans modifier les épisodes originaux."""

    def __init__(self, stockage: StockageDecision) -> None:
        self.stockage = stockage

    def collecter(self) -> tuple[ObservationApprentissage, ...]:
        observations: list[ObservationApprentissage] = []

        for experience in self.stockage.experiences():
            if experience.statut != "recorded_not_confirmed":
                continue
            relation = experience.resolution.get("candidate_semantic_relation")
            focus = None
            if isinstance(relation, dict):
                focus = str(relation.get("source") or "").strip() or None
            if focus is None:
                valeur = experience.resolution.get("value")
                focus = str(valeur).strip() if valeur not in {None, ""} else None
            observations.append(
                ObservationApprentissage(
                    id=experience.id,
                    source_type="experience",
                    requete=experience.requete_originale,
                    champ=experience.champ,
                    focus=focus,
                    occurrences=1,
                    resolution=dict(experience.resolution),
                    creee_le=experience.cree_le,
                )
            )

        for evenement in self.stockage.apprentissages():
            if evenement.statut != "to_study":
                continue
            observations.append(
                ObservationApprentissage(
                    id=evenement.id,
                    source_type="learning_event",
                    requete=evenement.requete,
                    champ=evenement.champ,
                    focus=evenement.focus,
                    occurrences=max(1, int(evenement.occurrences)),
                    resolution={},
                    creee_le=evenement.cree_le,
                )
            )

        return tuple(observations)
