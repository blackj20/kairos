"""Interface stable entre Kairos et un moteur linguistique interchangeable."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from .modeles import LectureLangage


class ErreurMoteurLangage(RuntimeError):
    """Erreur contrôlée : le fallback symbolique doit rester disponible."""


class MoteurLangageIndisponible(ErreurMoteurLangage):
    """Le fournisseur local n'est pas joignable ou n'est pas configuré."""


@runtime_checkable
class MoteurLangage(Protocol):
    """Capacités minimales attendues d'un moteur local."""

    nom: str
    modele: str

    def analyser(
        self,
        texte: str,
        contexte: Sequence[Mapping[str, Any]] = (),
    ) -> LectureLangage:
        ...

    def formuler(
        self,
        *,
        requete: str,
        analyse: Mapping[str, Any],
        decision: Mapping[str, Any],
        contexte: Sequence[Mapping[str, Any]] = (),
    ) -> str:
        ...

    def statut(self) -> dict[str, Any]:
        ...
