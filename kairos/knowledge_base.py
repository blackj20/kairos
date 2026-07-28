"""Lecture seule des leçons confirmées et de leurs branches relationnelles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .normalisation import cle


class KnowledgeBase:
    """Sélectionne une leçon confirmée par correspondance explicite d'alias."""

    def __init__(self, path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path else root / "data" / "knowledge" / "core.json"
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.items: tuple[dict[str, Any], ...] = tuple(data["items"])

    def find(self, request: str) -> dict[str, Any] | None:
        """Privilégie l'alias le plus spécifique présent dans la requête."""

        normalized = cle(request)
        matches: list[tuple[int, dict[str, Any]]] = []
        for item in self.items:
            for alias in item["aliases"]:
                normalized_alias = cle(alias)
                if normalized_alias in normalized:
                    matches.append((len(normalized_alias), item))
        return max(matches, key=lambda match: match[0])[1] if matches else None

    @staticmethod
    def compose(item: dict[str, Any]) -> str:
        """Produit une réponse claire avec sources et prochaine action concrète."""

        sources = ", ".join(item["sources"])
        return f"{item['answer']} Sources : {sources}"
