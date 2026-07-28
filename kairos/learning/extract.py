"""Extraction prudente de documents explicitement structurés."""

from __future__ import annotations

import re
from typing import Any


class Extractor:
    """Extrait titres, définitions explicites et blocs de code sans les confirmer."""

    _DEFINITION = re.compile(
        r"^\s*([^:\n]{2,80})\s*(?:est|désigne|:)\s+(.{3,500})$",
        flags=re.IGNORECASE,
    )
    _CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", flags=re.DOTALL)
    _RELATION = re.compile(
        r"^\s*([\wÀ-ÿ'-]{2,60})\s+"
        r"(signifie|est synonyme de|équivaut à|permet de)\s+"
        r"([\wÀ-ÿ' -]{2,100})\s*[.!]?\s*$",
        flags=re.IGNORECASE,
    )
    _EXAMPLE = re.compile(r"^\s*(?:exemple|example)\s*:\s*(.+)$", re.IGNORECASE)
    _COUNTEREXAMPLE = re.compile(
        r"^\s*(?:contre-exemple|contre exemple|ne pas confondre)\s*:\s*(.+)$",
        re.IGNORECASE,
    )

    def extract(self, content: str, evidence_id: str) -> list[dict[str, Any]]:
        """Retourne des candidats reliés à la preuve d'origine."""

        candidates: list[dict[str, Any]] = []
        for line in content.splitlines():
            match = self._DEFINITION.match(line)
            if match:
                candidates.append(
                    {
                        "name": match.group(1).strip(" #"),
                        "definition": match.group(2).strip(),
                        "evidence_ids": [evidence_id],
                        "confidence": 60,
                    }
                )
        code_blocks = [block.strip() for block in self._CODE.findall(content)]
        for candidate in candidates:
            candidate["examples"] = code_blocks
        return candidates

    def extract_relations(
        self, content: str, evidence_id: str
    ) -> list[dict[str, Any]]:
        """Extrait des relations explicites et leurs cas positifs/négatifs."""

        relations: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        relation_types = {
            "signifie": "equivalent",
            "est synonyme de": "equivalent",
            "équivaut à": "equivalent",
            "permet de": "facilite",
        }
        for line in content.splitlines():
            match = self._RELATION.match(line)
            if match:
                current = {
                    "source": match.group(1),
                    "relation": relation_types[match.group(2).casefold()],
                    "target": match.group(3).strip(" ."),
                    "evidence_ids": [evidence_id],
                    "examples": [],
                    "counterexamples": [],
                }
                relations.append(current)
                continue
            if current is None:
                continue
            example = self._EXAMPLE.match(line)
            counterexample = self._COUNTEREXAMPLE.match(line)
            if example:
                current["examples"].append(example.group(1).strip())
            elif counterexample:
                current["counterexamples"].append(
                    counterexample.group(1).strip()
                )
        return relations
