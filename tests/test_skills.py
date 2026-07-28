"""Tests du cycle candidate → scan → registre → rollback."""

from __future__ import annotations

import json
import os
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


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class TestSkills(unittest.TestCase):
    """Verrouille l'absence d'activation et de permission implicites."""

    def test_builder_creates_candidate_with_no_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = SkillBuilder(Path(tmp) / "candidates").scaffold(
                {"id": "python.explain", "domains": ["python"]}
            )
            manifest = SkillManifest.load(root / "skill.json")
            self.assertEqual("candidate", manifest.status)
            self.assertFalse(manifest.permissions["network"])
            self.assertFalse(manifest.permissions["shell"])
            self.assertEqual(128, manifest.limits["memory_mb"])

    def test_manifest_rejects_invalid_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skill.json"
            payload = {
                "id": "INVALID",
                "name": "bad",
                "version": "latest",
                "status": "candidate",
                "entrypoint": "../handler:run",
                "intents": [],
                "domains": [],
                "input_schema": {},
                "output_schema": {},
                "permissions": {
                    "network": False,
                    "filesystem_read": [],
                    "filesystem_write": [],
                    "process": False,
                    "shell": False,
                },
                "limits": {"timeout_seconds": 2, "memory_mb": 128},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                SkillManifest.load(path)

    def test_scanner_rejects_dangerous_source(self) -> None:
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

    def test_scanner_checks_tests_and_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = SkillBuilder(Path(tmp) / "candidates").scaffold(
                {"id": "unsafe.tests"}
            )
            (root / "tests" / "test_handler.py").write_text(
                "import subprocess\n",
                encoding="utf-8",
            )
            report = SkillScanner().scan_tree(root)
            self.assertFalse(report.passed)
            self.assertTrue(
                any("subprocess" in item for item in report.violations),
                report,
            )

            if hasattr(os, "symlink"):
                lien = root / "secret.py"
                try:
                    lien.symlink_to(Path(tmp) / "outside.py")
                except OSError:
                    return
                report = SkillScanner().scan_tree(root)
                self.assertFalse(report.passed)
                self.assertTrue(
                    any("symbolique" in item for item in report.violations)
                )

    def test_invalid_candidate_is_never_executed(self) -> None:
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
            self.assertTrue(report["permissions_valid"])
            self.assertGreaterEqual(report["memory_limit_mb"], 64)

    def test_registry_requires_full_proof_and_rolls_back_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = SkillRegistry(Path(tmp) / "registry.json")
            with self.assertRaises(ValueError):
                registry.activate(
                    "python.explain",
                    "0.1.0",
                    "",
                    "/candidate",
                    digest=DIGEST_A,
                    approved_by="Jps",
                )
            registry.activate(
                "python.explain",
                "0.1.0",
                "report_1",
                "/active/0.1.0",
                digest=DIGEST_A,
                approved_by="Jps",
            )
            registry.activate(
                "python.explain",
                "0.2.0",
                "report_2",
                "/active/0.2.0",
                digest=DIGEST_B,
                approved_by="Jps",
            )
            restored = registry.rollback("python.explain")
            self.assertIsNotNone(restored)
            self.assertEqual("0.1.0", restored["version"])
            self.assertEqual("/active/0.1.0", restored["path"])
            self.assertEqual("report_1", restored["report_id"])
            self.assertEqual(DIGEST_A, restored["digest"])
            active = registry.active("python.explain")
            self.assertIsNotNone(active)
            self.assertEqual("0.1.0", active["version"])


if __name__ == "__main__":
    unittest.main()
