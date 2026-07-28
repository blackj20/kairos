"""Modèle et validation stricte du manifeste d'une skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Permissions explicites et contrat d'exécution d'une version."""

    id: str
    name: str
    version: str
    status: str
    entrypoint: str
    intents: tuple[str, ...]
    domains: tuple[str, ...]
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    permissions: dict[str, Any]
    limits: dict[str, int]

    @classmethod
    def load(cls, path: str | Path) -> "SkillManifest":
        """Charge un JSON et rejette les permissions implicites."""

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        required = {
            "id", "name", "version", "status", "entrypoint", "intents",
            "domains", "input_schema", "output_schema", "permissions", "limits",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(f"Champs de manifeste absents : {sorted(missing)}")
        permission_keys = {
            "network", "filesystem_read", "filesystem_write",
            "process", "shell",
        }
        if set(data["permissions"]) != permission_keys:
            raise ValueError("Toutes les permissions doivent être explicites.")
        if data["status"] not in {"candidate", "active", "quarantined", "archived"}:
            raise ValueError("Statut de skill invalide.")
        return cls(
            **{
                **data,
                "intents": tuple(data["intents"]),
                "domains": tuple(data["domains"]),
            }
        )
