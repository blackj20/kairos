"""Registre qui n'expose que les versions activées après tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillRegistry:
    """Registre fichier atomique simple, remplaçable par SQLite."""

    def __init__(self, path: str | Path) -> None:
        """Crée un registre vide lorsqu'il n'existe pas encore."""

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('{"skills": {}}\n', encoding="utf-8")

    def _read(self) -> dict[str, Any]:
        """Lit l'état actuel du registre."""

        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        """Remplace atomiquement le registre après sérialisation complète."""

        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def activate(
        self, skill_id: str, version: str, report_id: str, path: str
    ) -> None:
        """Active uniquement une version accompagnée d'un rapport."""

        if not report_id:
            raise ValueError("Une activation exige un rapport de tests.")
        data = self._read()
        previous = data["skills"].get(skill_id, {}).get("active_version")
        data["skills"][skill_id] = {
            "active_version": version,
            "previous_version": previous,
            "report_id": report_id,
            "path": path,
            "status": "active",
        }
        self._write(data)

    def candidates(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Retourne uniquement les skills actives correspondant au domaine."""

        domain = request.get("domain")
        return [
            {"id": skill_id, **item}
            for skill_id, item in self._read()["skills"].items()
            if item.get("status") == "active"
            and (not domain or domain in skill_id)
        ]

    def rollback(self, skill_id: str) -> None:
        """Restaure la version précédente ou archive l'unique version."""

        data = self._read()
        skill = data["skills"].get(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        previous = skill.get("previous_version")
        if previous:
            skill["active_version"] = previous
            skill["previous_version"] = None
        else:
            skill["status"] = "archived"
        self._write(data)
