"""Contrat immuable reçu par la couche Répondre."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResponseContract:
    """Décrit quoi répondre, sans laisser le compositeur redécider la route."""

    mode: str
    intent: str
    concepts: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    language: str = "fr"
    max_length: int = 500

    def __post_init__(self) -> None:
        """Refuse les contrats susceptibles de produire une sortie non fondée."""

        if self.mode == "explanation" and not self.evidence_ids:
            raise ValueError("Une explication exige au moins une preuve.")
        if self.language != "fr":
            raise ValueError("Cette version compose uniquement en français.")
        if self.max_length < 1:
            raise ValueError("La longueur maximale doit être positive.")
