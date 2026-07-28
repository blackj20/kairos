"""Benchmark bloquant des invariants Skill Factory V0.5."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kairos.growup import (
    GroupeApprentissage,
    PlanApprentissage,
    ScorePriorite,
    StockageGrowUp,
)
from kairos.skills import SkillFactory, SkillFactoryStore, SkillRegistry


def main() -> int:
    resultats: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        growup = StockageGrowUp(root / "growup.db")
        store = SkillFactoryStore(root / "skills.db")
        registry = SkillRegistry(root / "registry.json")
        factory = SkillFactory(
            growup,
            candidates_dir=root / "candidates",
            active_dir=root / "active",
            registry=registry,
            store=store,
            authorized_approvers=("Jps",),
        )
        try:
            group = GroupeApprentissage(
                id="group_benchmark",
                cle="relation:deploie",
                champ="relation",
                focus="deploie",
                observation_ids=("obs_1", "obs_2", "obs_3"),
                experience_ids=("exp_1",),
                evenement_ids=("event_1",),
                occurrences=3,
                relation_source="deploie",
                relation_targets=("installer",),
            )
            plan = PlanApprentissage(
                id="plan_benchmark",
                groupe_id=group.id,
                objectif="comprendre deploie",
                route="collecter_preuves",
                manques=(),
                questions=(),
                tests_requis=6,
                priorite=ScorePriorite(90, 90, 90, 90, 90),
            )
            growup.sauvegarder_groupe(group)
            growup.sauvegarder_plan(plan)
            growup.changer_statut_plan(plan.id, "promoted")

            v1 = factory.generate_from_plan(plan.id, version="0.1.0")
            resultats["no_auto_activation"] = registry.active(v1.skill_id) is None
            r1 = factory.validate_candidate(v1.id)
            resultats["generated_candidate_passes"] = r1.passed
            try:
                factory.activate_candidate(v1.id, r1.id, approved_by="intrus")
            except PermissionError:
                resultats["unauthorized_activation_blocked"] = True
            else:
                resultats["unauthorized_activation_blocked"] = False
            a1 = factory.activate_candidate(v1.id, r1.id, approved_by="Jps")
            resultats["authorized_activation"] = (
                registry.active(v1.skill_id) is not None
                and registry.active(v1.skill_id)["digest"] == v1.digest
            )

            v2 = factory.generate_from_plan(plan.id, version="0.2.0")
            r2 = factory.validate_candidate(v2.id)
            a2 = factory.activate_candidate(v2.id, r2.id, approved_by="Jps")
            resultats["versioning"] = a2.previous_version == "0.1.0"
            restored = factory.rollback(v2.skill_id, approved_by="Jps")
            resultats["rollback_complete"] = bool(
                restored
                and restored["version"] == "0.1.0"
                and restored["path"] == a1.active_path
                and restored["report_id"] == r1.id
                and restored["digest"] == v1.digest
            )

            unsafe = factory.generate_from_plan(plan.id, version="0.3.0")
            (Path(unsafe.path) / "tests" / "test_handler.py").write_text(
                "import subprocess\n",
                encoding="utf-8",
            )
            unsafe_report = factory.validate_candidate(unsafe.id)
            resultats["dangerous_test_blocked"] = (
                not unsafe_report.passed
                and not unsafe_report.scan_passed
                and unsafe_report.details["returncode"] is None
            )

            tampered = factory.generate_from_plan(plan.id, version="0.4.0")
            tampered_report = factory.validate_candidate(tampered.id)
            handler = Path(tampered.path) / "handler.py"
            handler.write_text(
                handler.read_text(encoding="utf-8") + "\n# modification\n",
                encoding="utf-8",
            )
            try:
                factory.activate_candidate(
                    tampered.id,
                    tampered_report.id,
                    approved_by="Jps",
                )
            except ValueError:
                resultats["post_report_tamper_blocked"] = True
            else:
                resultats["post_report_tamper_blocked"] = False

            audit_events = [item["event"] for item in store.audit()]
            resultats["audit_traceability"] = all(
                event in audit_events
                for event in (
                    "CANDIDATE_GENERATED",
                    "CANDIDATE_VALIDATED",
                    "CANDIDATE_STATUS_CHANGED",
                )
            )
        finally:
            store.close()
            growup.close()

    total = len(resultats)
    reussis = sum(resultats.values())
    payload = {
        "version": "0.5.0",
        "passed": reussis == total,
        "score": f"{reussis}/{total}",
        "checks": resultats,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
