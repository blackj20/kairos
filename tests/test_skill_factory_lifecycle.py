"""Régressions de cohérence du cycle de vie Skill Factory V0.5."""

from __future__ import annotations

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
)


class TestSkillFactoryLifecycle(unittest.TestCase):
    def test_manifest_rejects_memory_below_effective_sandbox_limit(self) -> None:
        payload = {
            "id": "learned.test",
            "name": "Test",
            "version": "0.1.0",
            "status": "candidate",
            "entrypoint": "handler:run",
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
            "limits": {"timeout_seconds": 2, "memory_mb": 32},
        }
        with self.assertRaisesRegex(ValueError, "64 et 256"):
            SkillManifest.from_dict(payload)

    def test_new_active_version_marks_previous_as_superseded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            growup = StockageGrowUp(root / "growup.db")
            store = SkillFactoryStore(root / "skills.db")
            try:
                groupe = GroupeApprentissage(
                    id="group_lifecycle",
                    cle="relation:deploie",
                    champ="relation",
                    focus="deploie",
                    observation_ids=("obs_1",),
                    experience_ids=("exp_1",),
                    evenement_ids=("event_1",),
                    occurrences=3,
                    relation_source="deploie",
                    relation_targets=("installer",),
                )
                plan = PlanApprentissage(
                    id="plan_lifecycle",
                    groupe_id=groupe.id,
                    objectif="comprendre deploie",
                    route="collecter_preuves",
                    manques=(),
                    questions=(),
                    tests_requis=6,
                    priorite=ScorePriorite(90, 90, 90, 90, 90),
                )
                growup.sauvegarder_groupe(groupe)
                growup.sauvegarder_plan(plan)
                growup.changer_statut_plan(plan.id, "promoted")
                factory = SkillFactory(
                    growup,
                    candidates_dir=root / "candidates",
                    active_dir=root / "active",
                    registry=SkillRegistry(root / "registry.json"),
                    store=store,
                    authorized_approvers=("Jps",),
                )

                v1 = factory.generate_from_plan(plan.id, version="0.1.0")
                r1 = factory.validate_candidate(v1.id)
                factory.activate_candidate(v1.id, r1.id, approved_by="Jps")

                v2 = factory.generate_from_plan(plan.id, version="0.2.0")
                r2 = factory.validate_candidate(v2.id)
                factory.activate_candidate(v2.id, r2.id, approved_by="Jps")

                self.assertEqual("superseded", store.candidate(v1.id).status)
                self.assertEqual("activated", store.candidate(v2.id).status)

                factory.rollback(v2.skill_id, approved_by="Jps")
                self.assertEqual("activated", store.candidate(v1.id).status)
                self.assertEqual("archived", store.candidate(v2.id).status)
            finally:
                store.close()
                growup.close()


if __name__ == "__main__":
    unittest.main()
