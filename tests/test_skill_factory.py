"""Tests de la porte GrowUp → Skill Factory → activation réversible."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.growup import (
    GroupeApprentissage,
    PlanApprentissage,
    ScorePriorite,
    StockageGrowUp,
)
from kairos.skills import (
    SkillFactory,
    SkillFactoryStore,
    SkillManifest,
    SkillRegistry,
    artifact_digest,
)


class TestSkillFactory(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.growup = StockageGrowUp(self.root / "growup.db")
        self.store = SkillFactoryStore(self.root / "skills.db")
        self.registry = SkillRegistry(self.root / "registry.json")
        self.factory = SkillFactory(
            self.growup,
            candidates_dir=self.root / "candidates",
            active_dir=self.root / "active",
            registry=self.registry,
            store=self.store,
            authorized_approvers=("Jps",),
        )

    def tearDown(self) -> None:
        self.store.close()
        self.growup.close()
        self.temp.cleanup()

    def _plan(
        self,
        *,
        status: str = "promoted",
        source: str = "deploie",
        target: str = "installer",
        suffix: str = "1",
        contradictions: tuple[str, ...] = (),
    ) -> PlanApprentissage:
        group = GroupeApprentissage(
            id=f"group_{suffix}",
            cle=f"relation:{source}",
            champ="relation",
            focus=source,
            observation_ids=(f"obs_{suffix}",),
            experience_ids=(f"exp_{suffix}",),
            evenement_ids=(f"event_{suffix}",),
            occurrences=3,
            relation_source=source,
            relation_targets=(target,),
            contradictions=contradictions,
        )
        plan = PlanApprentissage(
            id=f"plan_{suffix}",
            groupe_id=group.id,
            objectif=f"comprendre {source}",
            route="collecter_preuves",
            manques=(),
            questions=(),
            tests_requis=6,
            priorite=ScorePriorite(90, 90, 90, 90, 90),
        )
        self.growup.sauvegarder_groupe(group)
        saved = self.growup.sauvegarder_plan(plan)
        if status != saved.statut:
            self.growup.changer_statut_plan(plan.id, status)
        result = self.growup.plan(plan.id)
        assert result is not None
        return result

    def test_only_promoted_plan_can_generate_candidate(self) -> None:
        planned = self._plan(status="planned")
        with self.assertRaisesRegex(ValueError, "promu"):
            self.factory.generate_from_plan(planned.id)

        promoted = self._plan(status="promoted", suffix="2")
        candidate = self.factory.generate_from_plan(promoted.id)
        self.assertEqual("generated", candidate.status)
        self.assertIsNone(self.registry.active(candidate.skill_id))

    def test_contradiction_blocks_generation(self) -> None:
        plan = self._plan(
            status="promoted",
            suffix="conflict",
            contradictions=("deux sens incompatibles",),
        )
        with self.assertRaisesRegex(ValueError, "contradictoire"):
            self.factory.generate_from_plan(plan.id)

    def test_generated_candidate_is_pure_and_traceable(self) -> None:
        plan = self._plan()
        candidate = self.factory.generate_from_plan(plan.id)
        root = Path(candidate.path)
        manifest = SkillManifest.load(root / "skill.json")
        provenance = json.loads(
            (root / "provenance.json").read_text(encoding="utf-8")
        )

        self.assertEqual("learned.deploie", manifest.id)
        self.assertEqual("candidate", manifest.status)
        self.assertFalse(manifest.permissions["network"])
        self.assertFalse(manifest.permissions["process"])
        self.assertFalse(manifest.permissions["shell"])
        self.assertEqual([], manifest.permissions["filesystem_read"])
        self.assertEqual([], manifest.permissions["filesystem_write"])
        self.assertEqual(plan.id, provenance["plan_id"])
        self.assertEqual(candidate.digest, artifact_digest(root))
        self.assertIsNone(self.registry.active(candidate.skill_id))

    def test_validation_runs_generated_tests_and_persists_report(self) -> None:
        candidate = self.factory.generate_from_plan(self._plan().id)
        report = self.factory.validate_candidate(candidate.id)

        self.assertTrue(report.passed, report)
        self.assertTrue(report.manifest_valid)
        self.assertTrue(report.permissions_valid)
        self.assertTrue(report.scan_passed)
        self.assertTrue(report.tests_passed)
        self.assertEqual(candidate.digest, report.digest)
        stored = self.store.report(report.id)
        self.assertIsNotNone(stored)
        self.assertEqual("validated", self.store.candidate(candidate.id).status)
        self.assertIsNone(self.registry.active(candidate.skill_id))

    def test_tampering_after_generation_quarantines_candidate(self) -> None:
        candidate = self.factory.generate_from_plan(self._plan().id)
        handler = Path(candidate.path) / "handler.py"
        handler.write_text(
            handler.read_text(encoding="utf-8") + "\n# modification\n",
            encoding="utf-8",
        )
        report = self.factory.validate_candidate(candidate.id)

        self.assertFalse(report.passed)
        self.assertTrue(any("empreinte" in item for item in report.violations))
        self.assertEqual("quarantined", self.store.candidate(candidate.id).status)

    def test_dangerous_code_in_candidate_tests_is_never_executed(self) -> None:
        candidate = self.factory.generate_from_plan(self._plan().id)
        test_file = Path(candidate.path) / "tests" / "test_handler.py"
        test_file.write_text("import subprocess\n", encoding="utf-8")
        report = self.factory.validate_candidate(candidate.id)

        self.assertFalse(report.passed)
        self.assertFalse(report.scan_passed)
        self.assertIsNone(report.details["returncode"])
        self.assertTrue(any("subprocess" in item for item in report.violations))

    def test_activation_requires_authorized_human_and_matching_report(self) -> None:
        first = self.factory.generate_from_plan(self._plan().id, version="0.1.0")
        first_report = self.factory.validate_candidate(first.id)
        second = self.factory.generate_from_plan(
            self.growup.plan("plan_1").id,
            version="0.2.0",
        )
        second_report = self.factory.validate_candidate(second.id)

        with self.assertRaises(PermissionError):
            self.factory.activate_candidate(
                first.id,
                first_report.id,
                approved_by="inconnu",
            )
        with self.assertRaisesRegex(ValueError, "autre candidate"):
            self.factory.activate_candidate(
                first.id,
                second_report.id,
                approved_by="Jps",
            )

        result = self.factory.activate_candidate(
            first.id,
            first_report.id,
            approved_by="Jps",
        )
        active = self.registry.active(first.skill_id)
        self.assertIsNotNone(active)
        self.assertEqual("0.1.0", active["version"])
        self.assertEqual(first_report.id, active["report_id"])
        self.assertEqual(first.digest, active["digest"])
        self.assertEqual("Jps", active["approved_by"])
        self.assertEqual(first.digest, artifact_digest(result.active_path))
        self.assertEqual(
            "active",
            SkillManifest.load(Path(result.active_path) / "skill.json").status,
        )

    def test_tampering_after_validation_blocks_activation(self) -> None:
        candidate = self.factory.generate_from_plan(self._plan().id)
        report = self.factory.validate_candidate(candidate.id)
        self.assertTrue(report.passed)
        handler = Path(candidate.path) / "handler.py"
        handler.write_text(
            handler.read_text(encoding="utf-8") + "\n# changé après rapport\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "changé"):
            self.factory.activate_candidate(
                candidate.id,
                report.id,
                approved_by="Jps",
            )
        self.assertIsNone(self.registry.active(candidate.skill_id))

    def test_new_version_and_rollback_restore_complete_artifact(self) -> None:
        plan = self._plan()
        v1 = self.factory.generate_from_plan(plan.id, version="0.1.0")
        r1 = self.factory.validate_candidate(v1.id)
        a1 = self.factory.activate_candidate(v1.id, r1.id, approved_by="Jps")

        v2 = self.factory.generate_from_plan(plan.id, version="0.2.0")
        r2 = self.factory.validate_candidate(v2.id)
        a2 = self.factory.activate_candidate(v2.id, r2.id, approved_by="Jps")
        self.assertEqual("0.1.0", a2.previous_version)
        self.assertEqual("0.2.0", self.registry.active(v2.skill_id)["version"])

        restored = self.factory.rollback(v2.skill_id, approved_by="Jps")
        self.assertIsNotNone(restored)
        self.assertEqual("0.1.0", restored["version"])
        self.assertEqual(a1.active_path, restored["path"])
        self.assertEqual(r1.id, restored["report_id"])
        self.assertEqual(v1.digest, restored["digest"])
        self.assertEqual("activated", self.store.candidate(v1.id).status)
        self.assertEqual("archived", self.store.candidate(v2.id).status)

    def test_audit_covers_generation_validation_and_activation(self) -> None:
        candidate = self.factory.generate_from_plan(self._plan().id)
        report = self.factory.validate_candidate(candidate.id)
        self.factory.activate_candidate(candidate.id, report.id, approved_by="Jps")
        events = [item["event"] for item in self.store.audit()]

        self.assertIn("CANDIDATE_GENERATED", events)
        self.assertIn("CANDIDATE_VALIDATED", events)
        self.assertGreaterEqual(events.count("CANDIDATE_STATUS_CHANGED"), 2)


if __name__ == "__main__":
    unittest.main()
