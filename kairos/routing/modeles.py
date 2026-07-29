"""Contrats immuables du routeur déclaratif."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StatutRoute(str, Enum):
    READY = "ready"
    CANDIDATE = "candidate"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class EtapeRoute:
    id: str
    capacite: str
    obligatoire: bool = True


@dataclass(frozen=True, slots=True)
class PlanRoute:
    id: str
    action: str
    objectif: str
    statut: StatutRoute
    etapes: tuple[EtapeRoute, ...] = field(default_factory=tuple)
    capacites_manquantes: tuple[str, ...] = field(default_factory=tuple)
    cible: str | None = None
    generee: bool = False
    score: int = 0
    raison: str = ""

    def vers_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["statut"] = self.statut.value
        return payload
