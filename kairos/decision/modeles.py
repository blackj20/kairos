"""Contrats immuables échangés dans la couche de décision."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ..modeles import Analyse


class Route(str, Enum):
    REPONDRE = "repondre"
    EXECUTER = "competence"
    CONTROLE = "controle"
    CONFIRMER = "confirmer"
    CLARIFIER = "clarification"
    ETUDIER = "etudier"
    REFUSER = "refuser"


@dataclass(frozen=True, slots=True)
class ActionSuivante:
    valeur: str
    score: int
    raisons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("Le score d'une action doit être entre 0 et 100.")


@dataclass(frozen=True, slots=True)
class EvaluationDecision:
    analyse: Analyse
    score_global: int
    champs_manquants: tuple[str, ...]
    contradictions: tuple[str, ...]
    actions_suivantes: tuple[ActionSuivante, ...]
    focus: str | None = None
    indices: tuple[str, ...] = field(default_factory=tuple)

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RouteChoisie:
    route: Route
    score: int
    raison: str

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QuestionEnAttente:
    id: str
    requete_originale: str
    champ_manquant: str
    texte: str
    statut: str
    score_initial: int
    route_proposee: str
    analyse: dict[str, Any]
    creee_le: str
    reponse: str | None = None
    resolue_le: str | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvenementApprentissage:
    id: str
    requete: str
    score: int
    champ: str
    focus: str | None
    question_id: str
    priorite: str
    statut: str
    occurrences: int
    cree_le: str

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvenementExperience:
    id: str
    question_id: str
    requete_originale: str
    question: str
    reponse: str
    champ: str
    resolution: dict[str, Any]
    analyse_reponse: dict[str, Any]
    statut: str
    cree_le: str

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VerdictDecision:
    valide: bool
    route: Route
    score: int
    raison: str
    question: QuestionEnAttente | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProcessusDecision:
    evaluation: EvaluationDecision
    route_choisie: RouteChoisie
    verdict: VerdictDecision

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
