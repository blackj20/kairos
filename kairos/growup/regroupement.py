"""Regroupement déterministe des expériences similaires."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from .modeles import GroupeApprentissage, ObservationApprentissage
from ..normalisation import cle


class Regroupement:
    """Fusionne les observations sans perdre leurs identifiants d'origine."""

    @staticmethod
    def _relation(observation: ObservationApprentissage) -> dict | None:
        relation = observation.resolution.get("candidate_semantic_relation")
        if not isinstance(relation, dict):
            # Compatibilité de lecture avec les premiers épisodes historiques.
            relation = observation.resolution.get("learned_semantic_relation")
        return relation if isinstance(relation, dict) else None

    def regrouper(
        self,
        observations: tuple[ObservationApprentissage, ...],
    ) -> tuple[GroupeApprentissage, ...]:
        paquets: dict[str, list[ObservationApprentissage]] = defaultdict(list)

        for observation in observations:
            relation = self._relation(observation)
            if relation is not None and relation.get("source"):
                cle_groupe = f"relation:{cle(str(relation['source']))}"
            elif observation.focus:
                cle_groupe = f"{observation.champ}:{cle(observation.focus)}"
            else:
                cle_groupe = f"{observation.champ}:{cle(observation.requete)}"
            paquets[cle_groupe].append(observation)

        groupes: list[GroupeApprentissage] = []
        for cle_groupe, membres in sorted(paquets.items()):
            experiences = tuple(
                membre.id for membre in membres if membre.source_type == "experience"
            )
            evenements = tuple(
                membre.id
                for membre in membres
                if membre.source_type == "learning_event"
            )
            compteur_evenement = max(
                (
                    membre.occurrences
                    for membre in membres
                    if membre.source_type == "learning_event"
                ),
                default=0,
            )
            # Les événements résument souvent les mêmes expériences. Le maximum
            # évite de compter deux fois un même épisode.
            occurrences = max(len(experiences), compteur_evenement, 1)

            relations = [
                relation
                for membre in membres
                if (relation := self._relation(membre)) is not None
            ]
            sources = sorted(
                {
                    cle(str(relation.get("source", "")))
                    for relation in relations
                    if str(relation.get("source", "")).strip()
                }
            )
            targets = sorted(
                {
                    cle(str(relation.get("target", "")))
                    for relation in relations
                    if str(relation.get("target", "")).strip()
                }
            )
            contradictions: list[str] = []
            if len(sources) > 1:
                contradictions.append("plusieurs sources sémantiques dans un groupe")
            if len(targets) > 1:
                contradictions.append("plusieurs verbes canoniques proposés")

            focus = sources[0] if len(sources) == 1 else next(
                (membre.focus for membre in membres if membre.focus),
                None,
            )
            digest = hashlib.sha256(cle_groupe.encode("utf-8")).hexdigest()[:20]
            groupes.append(
                GroupeApprentissage(
                    id=f"growup_group_{digest}",
                    cle=cle_groupe,
                    champ=membres[0].champ,
                    focus=focus,
                    observation_ids=tuple(membre.id for membre in membres),
                    experience_ids=experiences,
                    evenement_ids=evenements,
                    occurrences=occurrences,
                    relation_source=sources[0] if len(sources) == 1 else None,
                    relation_targets=tuple(targets),
                    contradictions=tuple(contradictions),
                )
            )

        return tuple(groupes)
