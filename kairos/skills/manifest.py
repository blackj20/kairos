"""Modèle et validation stricte du manifeste d'une skill."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_SKILL_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_ENTRYPOINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
    r":[A-Za-z_][A-Za-z0-9_]*$"
)


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

    CHAMPS = {
        "id",
        "name",
        "version",
        "status",
        "entrypoint",
        "intents",
        "domains",
        "input_schema",
        "output_schema",
        "permissions",
        "limits",
    }
    PERMISSIONS = {
        "network",
        "filesystem_read",
        "filesystem_write",
        "process",
        "shell",
    }
    STATUTS = {"candidate", "active", "quarantined", "archived"}

    @classmethod
    def load(cls, path: str | Path) -> "SkillManifest":
        """Charge un JSON et rejette toute ambiguïté de contrat."""

        chemin = Path(path)
        try:
            data = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ValueError(f"Manifeste illisible : {chemin} ({erreur})") from erreur
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Any) -> "SkillManifest":
        """Construit un manifeste uniquement après validation complète."""

        if not isinstance(data, dict):
            raise ValueError("Le manifeste doit être un objet JSON.")
        missing = cls.CHAMPS.difference(data)
        extra = set(data).difference(cls.CHAMPS)
        if missing:
            raise ValueError(f"Champs de manifeste absents : {sorted(missing)}")
        if extra:
            raise ValueError(f"Champs de manifeste inconnus : {sorted(extra)}")

        skill_id = data["id"]
        name = data["name"]
        version = data["version"]
        status = data["status"]
        entrypoint = data["entrypoint"]
        if not isinstance(skill_id, str) or not _SKILL_ID.fullmatch(skill_id):
            raise ValueError("Identifiant de skill invalide.")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("Nom de skill invalide.")
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise ValueError("Version de skill invalide ; utilisez MAJEUR.MINEUR.CORRECTIF.")
        if status not in cls.STATUTS:
            raise ValueError("Statut de skill invalide.")
        if not isinstance(entrypoint, str) or not _ENTRYPOINT.fullmatch(entrypoint):
            raise ValueError("Entrypoint invalide ; utilisez module:fonction.")

        intents = cls._liste_texte(data["intents"], "intents")
        domains = cls._liste_texte(data["domains"], "domains")
        input_schema = cls._schema(data["input_schema"], "input_schema")
        output_schema = cls._schema(data["output_schema"], "output_schema")

        permissions = data["permissions"]
        if not isinstance(permissions, dict):
            raise ValueError("Les permissions doivent être un objet.")
        if set(permissions) != cls.PERMISSIONS:
            raise ValueError("Toutes les permissions doivent être explicites.")
        for cle in ("network", "process", "shell"):
            if not isinstance(permissions[cle], bool):
                raise ValueError(f"La permission {cle!r} doit être booléenne.")
        for cle in ("filesystem_read", "filesystem_write"):
            cls._liste_texte(permissions[cle], f"permissions.{cle}")

        limits = data["limits"]
        if not isinstance(limits, dict) or set(limits) != {
            "timeout_seconds",
            "memory_mb",
        }:
            raise ValueError("Les limites timeout_seconds et memory_mb sont obligatoires.")
        timeout = limits["timeout_seconds"]
        memory = limits["memory_mb"]
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 10:
            raise ValueError("timeout_seconds doit être un entier entre 1 et 10.")
        if isinstance(memory, bool) or not isinstance(memory, int) or not 64 <= memory <= 256:
            raise ValueError("memory_mb doit être un entier entre 64 et 256.")

        return cls(
            id=skill_id,
            name=name.strip(),
            version=version,
            status=status,
            entrypoint=entrypoint,
            intents=intents,
            domains=domains,
            input_schema=input_schema,
            output_schema=output_schema,
            permissions={
                "network": permissions["network"],
                "filesystem_read": list(permissions["filesystem_read"]),
                "filesystem_write": list(permissions["filesystem_write"]),
                "process": permissions["process"],
                "shell": permissions["shell"],
            },
            limits={"timeout_seconds": timeout, "memory_mb": memory},
        )

    @staticmethod
    def _liste_texte(value: Any, champ: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise ValueError(f"{champ} doit être une liste.")
        nettoyes: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{champ} ne peut contenir que du texte non vide.")
            nettoyes.append(item.strip())
        if len(nettoyes) != len(set(nettoyes)):
            raise ValueError(f"{champ} contient des doublons.")
        return tuple(nettoyes)

    @staticmethod
    def _schema(value: Any, champ: str) -> dict[str, str]:
        if not isinstance(value, dict):
            raise ValueError(f"{champ} doit être un objet.")
        resultat: dict[str, str] = {}
        for cle, type_attendu in value.items():
            if not isinstance(cle, str) or not cle.strip():
                raise ValueError(f"Clé invalide dans {champ}.")
            if not isinstance(type_attendu, str) or not type_attendu.strip():
                raise ValueError(f"Type invalide dans {champ}.{cle}.")
            resultat[cle.strip()] = type_attendu.strip()
        return resultat

    def vers_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["intents"] = list(self.intents)
        payload["domains"] = list(self.domains)
        return payload
