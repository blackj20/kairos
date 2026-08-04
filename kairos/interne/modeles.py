"""Modèles observables du moteur interne hors ligne."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class TypeTravail(str, Enum):
    """Nature d'un travail détecté dans la mémoire cognitive."""

    REVUE_LOCALE = "local_review"
    QUESTION_HUMAINE = "human_question"
    BLOQUE = "blocked"


@dataclass(frozen=True, slots=True)
class TacheInterne:
    """Unité de travail calculée sans exécuter de capacité."""

    hypothesis_id: str
    nom: str
    type: TypeTravail
    priorite: int
    raison: str
    executable: bool
    manques: tuple[str, ...] = ()
    contexte_local: tuple[dict[str, Any], ...] = ()

    def vers_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["type"] = self.type.value
        return payload


@dataclass(frozen=True, slots=True)
class QuestionInterne:
    """Une seule question liée au manque le plus utile."""

    hypothesis_id: str
    champ: str
    texte: str
    gain_attendu: int
    raison: str

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RapportCycleInterne:
    """Rapport persistant d'un cycle synchrone du moteur interne."""

    run_id: str
    etat: str
    cycles: int
    candidats_vus: int
    taches_executees: int
    taches: tuple[TacheInterne, ...]
    question: QuestionInterne | None
    laboratoire: dict[str, Any] | None
    avant: dict[str, int]
    apres: dict[str, int]
    connaissances_production_modifiees: bool
    reseau_utilise: bool
    ratio_hors_ligne: float
    arret: str
    report_path: str

    def vers_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "etat": self.etat,
            "cycles": self.cycles,
            "candidats_vus": self.candidats_vus,
            "taches_executees": self.taches_executees,
            "taches": [item.vers_dict() for item in self.taches],
            "question": self.question.vers_dict() if self.question else None,
            "laboratoire": self.laboratoire,
            "avant": self.avant,
            "apres": self.apres,
            "connaissances_production_modifiees": (
                self.connaissances_production_modifiees
            ),
            "reseau_utilise": self.reseau_utilise,
            "ratio_hors_ligne": self.ratio_hors_ligne,
            "arret": self.arret,
            "report_path": self.report_path,
        }
