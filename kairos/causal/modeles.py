"""Modèles immuables de l'expérience causale V0.14."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StatutEpisode(str, Enum):
    CREATED = "created"
    PREDICTED = "predicted"
    EXECUTED = "executed"
    OBSERVED = "observed"
    EVALUATED = "evaluated"


@dataclass(frozen=True, slots=True)
class PredictionCausale:
    objectif: str
    route_id: str
    resultat_attendu: tuple[dict[str, Any], ...]
    sorties_attendues: dict[str, dict[str, str]]
    contrat_disponible: bool

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObservationCausale:
    execution_tentee: bool
    succes_technique: bool
    route_id: str
    trace: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    sortie: dict[str, Any] = field(default_factory=dict)
    erreur: str | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvaluationCausale:
    succes_technique: bool
    objectif_atteint: bool
    comprehension_validee: bool
    score_resultat: int
    controles: tuple[dict[str, Any], ...]
    erreurs: tuple[str, ...]

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResultatReplay:
    source_episode_id: str
    replay_episode_id: str
    score_avant: int
    score_apres: int
    difference: int
    meme_resultat: bool
    regression: bool

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
