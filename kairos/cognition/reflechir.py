"""Transformation d'expériences en hypothèses, jamais en vérités."""

from __future__ import annotations

from typing import Any

from ..memory import MemoryRepository


class Reflechir:
    """Transforme les manques en questions ou hypothèses testables."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def from_experience(
        self,
        experience_id: str,
        *,
        name: str,
        definition: str,
        evidence_ids: list[str],
        domain: str = "general",
        score: int = 60,
    ) -> str:
        return self.repository.add_hypothesis(
            {
                "created_from_experience_id": experience_id,
                "name": name,
                "definition": definition,
                "domain": domain,
                "evidence_ids": evidence_ids,
                "score": score,
            }
        )

    def relation_candidate(
        self,
        experience_id: str,
        candidate: dict[str, Any],
    ) -> str:
        """Crée une hypothèse relationnelle sans la rendre utilisable."""

        required = {
            "source",
            "relation",
            "target",
            "evidence_ids",
            "examples",
            "counterexamples",
        }
        missing = required.difference(candidate)
        if missing:
            raise ValueError(f"Relation candidate incomplète : {sorted(missing)}")
        return self.repository.add_hypothesis(
            {
                "created_from_experience_id": experience_id,
                **candidate,
                "kind": "semantic_relation",
            }
        )

    @staticmethod
    def questions_for(
        topic: str,
        missing: tuple[str, ...] = (
            "definition",
            "examples",
            "counterexamples",
            "relations",
        ),
    ) -> tuple[str, ...]:
        """Produit des questions ciblées pour améliorer un sujet."""

        templates = {
            "definition": f"Comment définir précisément « {topic} » ?",
            "examples": f"Peux-tu donner trois exemples de « {topic} » ?",
            "counterexamples": (
                f"Dans quels cas « {topic} » ne s'applique-t-il pas ?"
            ),
            "relations": (
                f"À quels concepts ou actions « {topic} » est-il relié ?"
            ),
            "source": f"Quelle source vérifiable décrit « {topic} » ?",
        }
        return tuple(templates[item] for item in missing if item in templates)
