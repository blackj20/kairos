"""Exécution de tests dans un processus limité et temporaire."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .manifest import SkillManifest
from .scanner import SkillScanner


class SandboxRunner:
    """Fournit une isolation de test locale ; aucune promesse de conteneur fort."""

    def __init__(self, scanner: SkillScanner | None = None) -> None:
        """Permet d'injecter un scanner différent pendant les tests."""

        self.scanner = scanner or SkillScanner()

    def validate(self, candidate_path: str | Path) -> dict[str, Any]:
        """Valide le manifeste, l'entrypoint et chaque source Python."""

        root = Path(candidate_path).resolve()
        manifest = SkillManifest.load(root / "skill.json")
        module_name, separator, function_name = manifest.entrypoint.partition(":")
        if not separator or not function_name:
            return {"passed": False, "violations": ["entrypoint invalide"]}
        source = root / f"{module_name}.py"
        if not source.is_file():
            return {"passed": False, "violations": ["entrypoint absent"]}
        report = self.scanner.scan(source)
        return {"passed": report.passed, "violations": list(report.violations)}

    def run_tests(self, candidate_path: str | Path) -> dict[str, Any]:
        """Copie le candidat puis exécute unittest sans shell avec timeout."""

        root = Path(candidate_path).resolve()
        validation = self.validate(root)
        if not validation["passed"]:
            return {**validation, "returncode": None}
        manifest = SkillManifest.load(root / "skill.json")
        timeout = max(1, min(int(manifest.limits.get("timeout_seconds", 2)), 10))
        with tempfile.TemporaryDirectory(prefix="kairos-skill-") as tmp:
            isolated = Path(tmp) / "candidate"
            shutil.copytree(root, isolated, symlinks=False)
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-c",
                        (
                            "import sys, unittest;"
                            "sys.path.insert(0, '.');"
                            "suite=unittest.defaultTestLoader.discover('tests');"
                            "result=unittest.TextTestRunner().run(suite);"
                            "raise SystemExit(not result.wasSuccessful())"
                        ),
                    ],
                    cwd=isolated,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env={"PYTHONPATH": ""},
                )
            except subprocess.TimeoutExpired:
                return {"passed": False, "timeout": True, "violations": ["timeout"]}
        return {
            "passed": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": process.stdout[-4000:],
            "stderr": process.stderr[-4000:],
            "timeout": False,
        }
