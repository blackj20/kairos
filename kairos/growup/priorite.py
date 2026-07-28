"""Calcul explicable de la priorité d'un groupe d'apprentissage."""

from __future__ import annotations

from .modeles import GroupeApprentissage, ScorePriorite


class Priorite:
    """Applique les poids validés sans modifier le groupe."""

    IMPACT_PAR_CHAMP = {
        "sens": 100,
        "action": 95,
        "cible": 85,
        "type_requete": 80,
        "demarche": 70,
        "confirmation": 45,
    }

    def calculer(self, groupe: GroupeApprentissage) -> ScorePriorite:
        frequence = min(100, groupe.occurrences * 25)
        impact = self.IMPACT_PAR_CHAMP.get(groupe.champ, 60)

        if groupe.contradictions:
            risque = 100
            verifiabilite = 20
        elif groupe.relation_source and groupe.relation_target:
            risque = 90
            verifiabilite = 90
        elif groupe.champ in {"action", "cible", "sens"}:
            risque = 80
            verifiabilite = 45
        else:
            risque = 55
            verifiabilite = 40

        total = round(
            frequence * 0.30
            + impact * 0.25
            + risque * 0.25
            + verifiabilite * 0.20
        )
        return ScorePriorite(
            total=max(0, min(100, total)),
            frequence=frequence,
            impact=impact,
            risque=risque,
            verifiabilite=verifiabilite,
        )
