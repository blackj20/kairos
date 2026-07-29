"""Contrats immuables de la recherche d'information."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceInformation:
    """Une source lisible, traçable et jamais confondue avec une vérité."""

    titre: str
    url: str
    extrait: str
    type_source: str = "web"
    confiance: int = 60

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
