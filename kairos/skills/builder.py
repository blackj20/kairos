"""Création d'un scaffold candidat sans activation implicite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillBuilder:
    """Produit uniquement des fichiers candidats faciles à auditer."""

    def __init__(self, candidates_dir: str | Path) -> None:
        """Fixe le seul dossier dans lequel le builder peut écrire."""

        self.candidates_dir = Path(candidates_dir).resolve()
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

    def scaffold(self, specification: dict[str, Any]) -> Path:
        """Crée un candidat minimal avec permissions toutes désactivées."""

        skill_id = str(specification["id"])
        safe_name = skill_id.replace(".", "_")
        if not safe_name.replace("_", "").isalnum():
            raise ValueError("Identifiant de skill invalide.")
        root = self.candidates_dir / safe_name
        if root.exists():
            raise FileExistsError(root)
        (root / "tests").mkdir(parents=True)
        manifest = {
            "id": skill_id,
            "name": specification.get("name", skill_id),
            "version": specification.get("version", "0.1.0"),
            "status": "candidate",
            "entrypoint": "handler:run",
            "intents": specification.get("intents", []),
            "domains": specification.get("domains", []),
            "input_schema": specification.get("input_schema", {}),
            "output_schema": specification.get("output_schema", {}),
            "permissions": {
                "network": False,
                "filesystem_read": [],
                "filesystem_write": [],
                "process": False,
                "shell": False,
            },
            "limits": {"timeout_seconds": 2, "memory_mb": 64},
        }
        (root / "skill.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "handler.py").write_text(
            '"""Entrée candidate générée par K.A.I.R.O.S."""\n\n'
            "def run(request: dict, context: dict) -> dict:\n"
            '    """Retourne une sortie vide tant que la skill n’est pas développée."""\n'
            '    return {"status": "candidate_not_implemented"}\n',
            encoding="utf-8",
        )
        (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        return root
