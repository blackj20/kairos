"""Création de candidates déterministes sans activation implicite."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .manifest import SkillManifest


class SkillBuilder:
    """Produit uniquement des fichiers candidats faciles à auditer."""

    def __init__(self, candidates_dir: str | Path) -> None:
        self.candidates_dir = Path(candidates_dir).resolve()
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

    def scaffold(self, specification: dict[str, Any]) -> Path:
        """Crée un candidat minimal avec permissions toutes désactivées."""

        manifest = self._manifest(specification)
        return self._creer_atomiquement(
            manifest,
            handler=(
                '"""Entrée candidate générée par K.A.I.R.O.S."""\n\n'
                "def run(request: dict, context: dict) -> dict:\n"
                '    """Reste inactive tant que son comportement n’est pas défini."""\n'
                '    return {"status": "candidate_not_implemented"}\n'
            ),
            tests=None,
            provenance={
                "template": "scaffold",
                "plan_id": specification.get("plan_id"),
                "group_id": specification.get("group_id"),
            },
        )

    def build(self, specification: dict[str, Any]) -> Path:
        """Génère uniquement un template explicitement autorisé."""

        template = specification.get("template", "scaffold")
        if template == "scaffold":
            return self.scaffold(specification)
        if template == "relation_mapper":
            return self._relation_mapper(specification)
        raise ValueError(f"Template de skill non autorisé : {template!r}")

    def _relation_mapper(self, specification: dict[str, Any]) -> Path:
        """Crée une skill pure qui applique une relation déjà promue."""

        source = self._texte_court(specification.get("source"), "source")
        target = self._texte_court(specification.get("target"), "target")
        plan_id = self._texte_court(specification.get("plan_id"), "plan_id")
        group_id = self._texte_court(specification.get("group_id"), "group_id")
        manifest = self._manifest(specification)

        source_literal = repr(source.casefold().strip())
        target_literal = repr(target.casefold().strip())
        handler = (
            '"""Mapping pur généré depuis une relation GrowUp promue."""\n\n'
            f"SOURCE_ACTION = {source_literal}\n"
            f"TARGET_ACTION = {target_literal}\n\n"
            "def _normaliser(value: object) -> str:\n"
            '    """Normalise sans accéder à une ressource externe."""\n'
            "    return ' '.join(str(value).casefold().split())\n\n"
            "def run(request: dict, context: dict) -> dict:\n"
            '    """Transforme uniquement l’action attendue et conserve la cible."""\n'
            "    if not isinstance(request, dict):\n"
            '        return {"status": "invalid_request"}\n'
            "    action = _normaliser(request.get('action', ''))\n"
            "    if action != SOURCE_ACTION:\n"
            "        return {\n"
            '            "status": "not_applicable",\n'
            '            "expected_action": SOURCE_ACTION,\n'
            "        }\n"
            "    return {\n"
            '        "status": "ok",\n'
            '        "source_action": SOURCE_ACTION,\n'
            '        "action": TARGET_ACTION,\n'
            '        "target": request.get("target"),\n'
            "    }\n"
        )
        tests = (
            "import unittest\n"
            "from handler import run\n\n"
            "class TestGeneratedRelationMapper(unittest.TestCase):\n"
            "    def test_maps_promoted_relation(self):\n"
            "        result = run(\n"
            f"            {{'action': {source_literal}, 'target': 'python'}}, {{}}\n"
            "        )\n"
            "        self.assertEqual('ok', result['status'])\n"
            f"        self.assertEqual({target_literal}, result['action'])\n"
            "        self.assertEqual('python', result['target'])\n\n"
            "    def test_rejects_other_action(self):\n"
            "        result = run({'action': 'supprime', 'target': 'python'}, {})\n"
            "        self.assertEqual('not_applicable', result['status'])\n\n"
            "    def test_rejects_non_mapping_request(self):\n"
            "        self.assertEqual('invalid_request', run('bad', {})['status'])\n"
        )
        return self._creer_atomiquement(
            manifest,
            handler=handler,
            tests=tests,
            provenance={
                "template": "relation_mapper",
                "plan_id": plan_id,
                "group_id": group_id,
                "source": source,
                "target": target,
            },
        )

    def _manifest(self, specification: dict[str, Any]) -> SkillManifest:
        skill_id = str(specification["id"])
        payload = {
            "id": skill_id,
            "name": specification.get("name", skill_id),
            "version": specification.get("version", "0.1.0"),
            "status": "candidate",
            "entrypoint": "handler:run",
            "intents": list(specification.get("intents", [])),
            "domains": list(specification.get("domains", [])),
            "input_schema": dict(specification.get("input_schema", {})),
            "output_schema": dict(specification.get("output_schema", {})),
            "permissions": {
                "network": False,
                "filesystem_read": [],
                "filesystem_write": [],
                "process": False,
                "shell": False,
            },
            "limits": {
                "timeout_seconds": int(specification.get("timeout_seconds", 2)),
                "memory_mb": int(specification.get("memory_mb", 128)),
            },
        }
        return SkillManifest.from_dict(payload)

    def _creer_atomiquement(
        self,
        manifest: SkillManifest,
        *,
        handler: str,
        tests: str | None,
        provenance: dict[str, Any],
    ) -> Path:
        safe_name = manifest.id.replace(".", "_")
        root = self.candidates_dir / safe_name / manifest.version
        if root.exists():
            raise FileExistsError(root)
        root.parent.mkdir(parents=True, exist_ok=True)

        temporaire = Path(
            tempfile.mkdtemp(prefix=f".{safe_name}-", dir=root.parent)
        )
        try:
            (temporaire / "tests").mkdir(parents=True)
            (temporaire / "skill.json").write_text(
                json.dumps(
                    manifest.vers_dict(),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (temporaire / "provenance.json").write_text(
                json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (temporaire / "handler.py").write_text(handler, encoding="utf-8")
            (temporaire / "tests" / "__init__.py").write_text(
                "",
                encoding="utf-8",
            )
            if tests is not None:
                (temporaire / "tests" / "test_handler.py").write_text(
                    tests,
                    encoding="utf-8",
                )
            temporaire.replace(root)
        except Exception:
            shutil.rmtree(temporaire, ignore_errors=True)
            raise
        return root

    @staticmethod
    def _texte_court(value: Any, champ: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{champ} est obligatoire.")
        nettoye = " ".join(value.split())
        if len(nettoye) > 160:
            raise ValueError(f"{champ} est trop long.")
        return nettoye
