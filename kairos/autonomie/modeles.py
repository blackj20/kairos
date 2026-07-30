"""Modèles immuables des buts, événements et choix d'attention V0.15."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StatutBut(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"
    ABANDONED = "abandoned"

    @property
    def terminal(self) -> bool:
        return self in {
            StatutBut.COMPLETED,
            StatutBut.BLOCKED,
            StatutBut.INVALIDATED,
            StatutBut.ABANDONED,
        }


class TypeEvenementBut(str, Enum):
    CREATED = "goal.created"
    ACTIVATED = "goal.activated"
    RESUMED = "goal.resumed"
    ATTENTION_SELECTED = "attention.selected"
    STEP_STARTED = "step.started"
    EPISODE_EVALUATED = "episode.evaluated"
    COMPLETED = "goal.completed"
    BLOCKED = "goal.blocked"
    INVALIDATED = "goal.invalidated"
    ABANDONED = "goal.abandoned"
    BUDGET_EXHAUSTED = "budget.exhausted"


@dataclass(frozen=True, slots=True)
class But:
    id: str
    mission: str
    action: str | None
    cible: str | None
    priorite: int
    statut: StatutBut
    max_etapes: int
    etapes_utilisees: int
    dernier_episode_id: str | None
    derniere_raison: str | None
    created_at: str
    updated_at: str

    def vers_dict(self) -> dict[str, Any]:
        resultat = asdict(self)
        resultat["statut"] = self.statut.value
        return resultat


@dataclass(frozen=True, slots=True)
class ChoixAttention:
    goal_id: str
    action: str
    score: int
    raisons: tuple[str, ...]
    contexte: dict[str, Any] = field(default_factory=dict)

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResultatCycle:
    but: But
    choix: ChoixAttention | None
    episode: dict[str, Any] | None
    evenements: tuple[dict[str, Any], ...]

    def vers_dict(self) -> dict[str, Any]:
        return {
            "goal": self.but.vers_dict(),
            "attention": self.choix.vers_dict() if self.choix else None,
            "episode": self.episode,
            "events": list(self.evenements),
        }
