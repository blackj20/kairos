"""Acquisition locale : une source devient une preuve, jamais une vérité."""

from __future__ import annotations

from pathlib import Path

from ..memory import MemoryRepository


class Acquire:
    """Collecte uniquement une réponse guidée ou un document local explicite."""

    def __init__(self, repository: MemoryRepository) -> None:
        """Injecte le dépôt transactionnel de provenance."""

        self.repository = repository

    def from_creator(self, reference: str, content: str) -> str:
        """Enregistre un enseignement du créateur avec un niveau de confiance élevé."""

        return self.repository.add_evidence("creator", reference, content, 90)

    def from_local_document(self, path: str | Path) -> tuple[str, str]:
        """Lit un fichier UTF-8 précis et conserve son chemin comme provenance."""

        resolved = Path(path).resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("La source locale doit être un fichier.")
        content = resolved.read_text(encoding="utf-8")
        evidence_id = self.repository.add_evidence(
            "local_document", str(resolved), content, 75
        )
        return evidence_id, content
