"""Tests du cycle candidate → scan → registre → rollback."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.skills import (
    SandboxRunner,
    SkillBuilder,
    SkillManifest,
    SkillRegistry,
    SkillScanner,
)


class TestSkills(unittest.TestCase):
    """Verrouille l'absence d'activation et de permission implicites."""

    def test_builder_creates_candidate_with_no_permissions(self) -> None:
        """Le scaffold doit commencer fermé et non exécutable par le registre."""

        with tempfile.TemporaryDirectory() as tmp:
            root = SkillBuilder(Path(tmp) / "candidates").scaffold(
                {"id": "python.explain", "domains": ["python"]}
            )
            manifest = SkillManifest.load(root / "skill.json")
            self.assertEqual("candidate", manifest.status)
            self.assertFalse(manifest.permissions["network"])
            self.assertFalse(manifest.permissions["shell"])

    def test_scanner_rejects_dangerous_source(self) -> None:
        """Imports système et eval sont bloqués avant le sandbox."""

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "handler.py"
            source.write_text(
                "import os\n\ndef run(request, context):\n"
                "    return eval(request['code'])\n",
                encoding="utf-8",
            )
            report = SkillScanner().scan(source)
            self.assertFalse(report.passed)
            self.assertTrue(any("os" in item for item in report.violations))
            self.assertTrue(any("eval" in item for item in report.violations))

    def test_invalid_candidate_is_never_executed(self) -> None:
        """Le runner s'arrête immédiatement après un scan négatif."""

        with tempfile.TemporaryDirectory() as tmp:
            root = SkillBuilder(Path(tmp) / "candidates").scaffold(
                {"id": "unsafe.skill"}
            )
            (root / "handler.py").write_text(
                "import subprocess\n\ndef run(request, context):\n    return {}\n",
                encoding="utf-8",
            )
            report = SandboxRunner().run_tests(root)
            self.assertFalse(report["passed"])
            self.assertIsNone(report["returncode"])

    def test_safe_candidate_runs_in_isolated_process(self) -> None:
        """Une skill sûre est testée hors du processus principal."""

        with tempfile.TemporaryDirectory() as tmp:
            root = SkillBuilder(Path(tmp) / "candidates").scaffold(
                {"id": "safe.skill"}
            )
            (root / "tests" / "test_handler.py").write_text(
                "import unittest\n"
                "from handler import run\n\n"
                "class TestHandler(unittest.TestCase):\n"
                "    def test_candidate_status(self):\n"
                "        self.assertEqual(\n"
                "            'candidate_not_implemented', run({}, {})['status']\n"
                "        )\n",
                encoding="utf-8",
            )
            report = SandboxRunner().run_tests(root)
            self.assertTrue(report["passed"], report)
            self.assertEqual(0, report["returncode"])

    def test_registry_requires_report_and_rolls_back(self) -> None:
        """Toute activation a une preuve et toute version est réversible."""

        with tempfile.TemporaryDirectory() as tmp:
            registry = SkillRegistry(Path(tmp) / "registry.json")
            with self.assertRaises(ValueError):
                registry.activate("python.explain", "0.1.0", "", "/candidate")
            registry.activate(
                "python.explain", "0.1.0", "report_1", "/active/0.1.0"
            )
            registry.activate(
                "python.explain", "0.2.0", "report_2", "/active/0.2.0"
            )
            registry.rollback("python.explain")
            data = json.loads(
                (Path(tmp) / "registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "0.1.0", data["skills"]["python.explain"]["active_version"]
            )


if __name__ == "__main__":
    unittest.main()
