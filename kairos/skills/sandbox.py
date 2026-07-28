"""Exécution de tests dans un processus limité et temporaire."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .manifest import SkillManifest
from .policy import PermissionPolicy
from .scanner import SkillScanner


class SandboxRunner:
    """Isolation locale de test ; aucune promesse de conteneur système fort."""

    def __init__(
        self,
        scanner: SkillScanner | None = None,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self.scanner = scanner or SkillScanner()
        self.permission_policy = permission_policy or PermissionPolicy()

    def validate(self, candidate_path: str | Path) -> dict[str, Any]:
        """Valide manifeste, permissions, arborescence et entrypoint."""

        root = Path(candidate_path).resolve()
        try:
            manifest = SkillManifest.load(root / "skill.json")
        except ValueError as erreur:
            return {
                "passed": False,
                "manifest_valid": False,
                "permissions_valid": False,
                "scan_passed": False,
                "violations": [str(erreur)],
            }

        violations: list[str] = []
        permission_report = self.permission_policy.validate(manifest)
        violations.extend(permission_report.violations)

        module_name, function_name = manifest.entrypoint.split(":", 1)
        source = root.joinpath(*module_name.split(".")).with_suffix(".py")
        if not source.is_file():
            violations.append("entrypoint absent")
        elif not self._fonction_presente(source, function_name):
            violations.append(f"fonction d'entrypoint absente : {function_name}")

        scan_report = self.scanner.scan_tree(root)
        violations.extend(scan_report.violations)
        tests = tuple(sorted((root / "tests").glob("test_*.py")))
        if not tests:
            violations.append("aucun test candidat détecté")

        return {
            "passed": not violations,
            "manifest_valid": True,
            "permissions_valid": permission_report.passed,
            "scan_passed": scan_report.passed,
            "files_scanned": list(scan_report.files_scanned),
            "violations": list(dict.fromkeys(violations)),
            "manifest": manifest.vers_dict(),
        }

    @staticmethod
    def _fonction_presente(source: Path, function_name: str) -> bool:
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError):
            return False
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
            for node in tree.body
        )

    def run_tests(self, candidate_path: str | Path) -> dict[str, Any]:
        """Copie le candidat puis exécute unittest sans shell et avec quotas."""

        root = Path(candidate_path).resolve()
        validation = self.validate(root)
        if not validation["passed"]:
            return {**validation, "returncode": None, "timeout": False}

        manifest = SkillManifest.load(root / "skill.json")
        timeout = max(1, min(manifest.limits["timeout_seconds"], 10))
        memory_mb = max(64, min(manifest.limits["memory_mb"], 256))
        runner = self._runner_code(memory_mb=memory_mb, cpu_seconds=timeout)

        with tempfile.TemporaryDirectory(prefix="kairos-skill-") as tmp:
            isolated = Path(tmp) / "candidate"
            shutil.copytree(root, isolated, symlinks=False)
            try:
                process = subprocess.run(
                    [sys.executable, "-I", "-c", runner],
                    cwd=isolated,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 2,
                    check=False,
                    env={
                        "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8",
                        "PYTHONHASHSEED": "0",
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONPATH": "",
                    },
                )
            except subprocess.TimeoutExpired:
                return {
                    **validation,
                    "passed": False,
                    "tests_passed": False,
                    "returncode": None,
                    "timeout": True,
                    "violations": [*validation["violations"], "timeout"],
                }

        tests_passed = process.returncode == 0
        violations = list(validation["violations"])
        if not tests_passed:
            violations.append("tests candidats échoués")
        return {
            **validation,
            "passed": validation["passed"] and tests_passed,
            "tests_passed": tests_passed,
            "returncode": process.returncode,
            "stdout": process.stdout[-4000:],
            "stderr": process.stderr[-4000:],
            "timeout": False,
            "memory_limit_mb": memory_mb,
            "cpu_limit_seconds": timeout,
            "violations": list(dict.fromkeys(violations)),
        }

    @staticmethod
    def _runner_code(*, memory_mb: int, cpu_seconds: int) -> str:
        """Construit le bootstrap hors candidat qui applique les quotas POSIX."""

        return (
            "import sys, unittest\n"
            "try:\n"
            " import resource\n"
            f" memory={memory_mb}*1024*1024\n"
            f" cpu={cpu_seconds}\n"
            " resource.setrlimit(resource.RLIMIT_AS, (memory, memory))\n"
            " resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))\n"
            " resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024, 1024*1024))\n"
            " resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))\n"
            "except (ImportError, ValueError, OSError):\n"
            " pass\n"
            "sys.path.insert(0, '.')\n"
            "suite=unittest.defaultTestLoader.discover('tests')\n"
            "result=unittest.TextTestRunner(verbosity=2).run(suite)\n"
            "raise SystemExit(0 if result.wasSuccessful() else 1)\n"
        )
