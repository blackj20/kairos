"""Construction de relations candidates depuis plusieurs extractions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..normalisation import cle


class Relier:
    """Regroupe les affirmations concordantes sans les confirmer."""

    def relations(
        self, extractions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Produit uniquement les relations appuyées par deux preuves."""

        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in extractions:
            key = (
                cle(str(item.get("source", ""))),
                str(item.get("relation", "equivalent")),
                cle(str(item.get("target", ""))),
            )
            if key[0] and key[2]:
                groups[key].append(item)
        candidates: list[dict[str, Any]] = []
        for (source, relation, target), items in groups.items():
            evidence_ids = sorted(
                {
                    evidence
                    for item in items
                    for evidence in item.get("evidence_ids", [])
                }
            )
            if len(evidence_ids) < 2:
                continue
            examples = list(
                dict.fromkeys(
                    example
                    for item in items
                    for example in item.get("examples", [])
                )
            )
            counterexamples = list(
                dict.fromkeys(
                    example
                    for item in items
                    for example in item.get("counterexamples", [])
                )
            )
            candidates.append(
                {
                    "source": source,
                    "relation": relation,
                    "target": target,
                    "evidence_ids": evidence_ids,
                    "examples": examples,
                    "counterexamples": counterexamples,
                    "score": min(85, 55 + 10 * len(evidence_ids)),
                    "status": "candidate",
                }
            )
        return candidates
