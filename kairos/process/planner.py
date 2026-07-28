"""Contrats de plans explicites et validables avant exécution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Risk(str, Enum):
    """Niveaux de risque autorisés par le prototype."""

    READ = "read"
    REVERSIBLE_WRITE = "reversible_write"
    SENSITIVE_WRITE = "sensitive_write"
    DESTRUCTION = "destruction"


@dataclass(frozen=True, slots=True)
class ProcessStep:
    """Une opération ciblée, sans possibilité de commande shell."""

    tool: str
    arguments: dict[str, Any]
    risk: Risk
    requires_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class ProcessPlan:
    """Plan complet avec approbation explicite des étapes sensibles."""

    goal: str
    steps: tuple[ProcessStep, ...]
    approved: bool = False

    def validate(self) -> None:
        """Refuse les outils inconnus et les écritures risquées non confirmées."""

        allowed = {
            "fs.list", "fs.stat", "fs.read", "fs.search",
            "fs.create_directory", "fs.copy", "fs.move", "fs.rename",
            "fs.delete_to_trash",
        }
        for step in self.steps:
            if step.tool not in allowed:
                raise ValueError(f"Outil interdit : {step.tool}")
            if step.risk in {Risk.SENSITIVE_WRITE, Risk.DESTRUCTION}:
                if not step.requires_confirmation or not self.approved:
                    raise PermissionError("Une étape sensible exige une confirmation.")
