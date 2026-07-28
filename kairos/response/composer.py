"""Compositeur déterministe depuis la mémoire confirmée."""

from __future__ import annotations

from ..memory import MemoryRepository
from .contract import ResponseContract


class ResponseComposer:
    """Assemble les définitions confirmées sans inventer de contenu."""

    def __init__(self, repository: MemoryRepository) -> None:
        """Injecte le dépôt afin de garder la couche facilement testable."""

        self.repository = repository

    def compose(self, contract: ResponseContract) -> str:
        """Retourne une réponse sourcée ou un constat explicite d'absence."""

        fragments: list[str] = []
        for concept in contract.concepts:
            matches = self.repository.search({"text": concept})
            exact = next(
                (
                    item
                    for item in matches
                    if item["name"].casefold() == concept.casefold()
                ),
                None,
            )
            if exact and exact.get("definition"):
                fragments.append(f"{exact['name']} : {exact['definition']}")
        if not fragments:
            return "Je ne possède pas encore de connaissance confirmée pour répondre."
        return " ".join(fragments)[: contract.max_length]
