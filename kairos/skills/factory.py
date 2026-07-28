"""Orchestration GrowUp → candidate → validation → activation réversible."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..growup import PlanApprentissage, StockageGrowUp
from .builder import SkillBuilder
from .integrity import ErreurIntegrite, artifact_digest
from .manifest import SkillManifest
from .models import ActivationResult, CandidateRecord, ValidationReport
from .registry import SkillRegistry
from .sandbox import SandboxRunner
from .store import SkillFactoryStore


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillFactory:
    """Fabrique des skills pures sans jamais les activer implicitement."""

    def __init__(
        self,
        growup_storage: StockageGrowUp,
        *,
        candidates_dir: str | Path,
        active_dir: str | Path,
        registry: SkillRegistry,
        store: SkillFactoryStore | None = None,
        sandbox: SandboxRunner | None = None,
        authorized_approvers: Iterable[str] = ("Jps",),
    ) -> None:
        self.growup_storage = growup_storage
        self.candidates_dir = Path(candidates_dir).resolve()
        self.active_dir = Path(active_dir).resolve()
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        if self.candidates_dir == self.active_dir:
            raise ValueError("Les dossiers candidate et actif doivent être séparés.")
        self.registry = registry
        self.store = store or SkillFactoryStore()
        self.sandbox = sandbox or SandboxRunner()
        self.builder = SkillBuilder(self.candidates_dir)
        self.authorized_approvers = frozenset(
            item.strip() for item in authorized_approvers if item.strip()
        )
        if not self.authorized_approvers:
            raise ValueError("Au moins un approbateur doit être déclaré.")

    def eligible_plans(self) -> tuple[PlanApprentissage, ...]:
        """Retourne les plans promus qui possèdent une relation non conflictuelle."""

        resultats: list[PlanApprentissage] = []
        for plan in self.growup_storage.plans("promoted"):
            groupe = self.growup_storage.groupe(plan.groupe_id)
            if (
                groupe is not None
                and not groupe.contradictions
                and groupe.relation_source
                and groupe.relation_target
            ):
                resultats.append(plan)
        return tuple(resultats)

    def generate_from_plan(
        self,
        plan_id: str,
        *,
        skill_id: str | None = None,
        version: str = "0.1.0",
    ) -> CandidateRecord:
        """Génère une candidate uniquement depuis un plan déjà promu."""

        plan = self.growup_storage.plan(plan_id)
        if plan is None:
            raise KeyError(f"Plan GrowUp inconnu : {plan_id}")
        if plan.statut != "promoted":
            raise ValueError(
                f"Une skill exige un plan GrowUp promu, état reçu : {plan.statut!r}."
            )
        groupe = self.growup_storage.groupe(plan.groupe_id)
        if groupe is None:
            raise KeyError(f"Groupe GrowUp inconnu : {plan.groupe_id}")
        if groupe.contradictions:
            raise ValueError("Une relation contradictoire ne peut générer aucune skill.")
        if not groupe.relation_source or not groupe.relation_target:
            raise ValueError("Le groupe ne contient pas de relation complète.")

        identifiant = skill_id or f"learned.{self._slug(groupe.relation_source)}"
        specification = {
            "id": identifiant,
            "name": (
                f"Relation apprise : {groupe.relation_source} → "
                f"{groupe.relation_target}"
            ),
            "version": version,
            "template": "relation_mapper",
            "plan_id": plan.id,
            "group_id": groupe.id,
            "source": groupe.relation_source,
            "target": groupe.relation_target,
            "intents": [groupe.relation_source],
            "domains": ["learned"],
            "input_schema": {"action": "string", "target": "any"},
            "output_schema": {
                "status": "string",
                "action": "string",
                "target": "any",
            },
        }
        path = self.builder.build(specification)
        digest = artifact_digest(path)
        manifest = SkillManifest.load(path / "skill.json")
        candidate = CandidateRecord(
            id=f"candidate_{uuid.uuid4().hex}",
            skill_id=manifest.id,
            version=manifest.version,
            plan_id=plan.id,
            group_id=groupe.id,
            path=str(path),
            digest=digest,
            status="generated",
            created_at=_maintenant(),
        )
        try:
            return self.store.save_candidate(candidate)
        except Exception:
            shutil.rmtree(path, ignore_errors=True)
            raise

    def validate_candidate(self, candidate_id: str) -> ValidationReport:
        """Teste la candidate et lie le rapport à son contenu exact."""

        candidate = self.store.candidate(candidate_id)
        if candidate is None:
            raise KeyError(f"Candidate inconnue : {candidate_id}")
        path = Path(candidate.path)
        violations: list[str] = []
        try:
            digest = artifact_digest(path)
        except ErreurIntegrite as erreur:
            digest = "0" * 64
            violations.append(str(erreur))

        result = self.sandbox.run_tests(path)
        violations.extend(result.get("violations", []))
        manifest_payload = result.get("manifest")
        if isinstance(manifest_payload, dict):
            if manifest_payload.get("id") != candidate.skill_id:
                violations.append("le manifeste ne correspond pas au skill_id enregistré")
            if manifest_payload.get("version") != candidate.version:
                violations.append("le manifeste ne correspond pas à la version enregistrée")
        if digest != candidate.digest:
            violations.append("empreinte candidate modifiée depuis la génération")

        violations_tuple = tuple(dict.fromkeys(violations))
        passed = bool(result.get("passed")) and not violations_tuple
        report = ValidationReport(
            id=f"skill_report_{uuid.uuid4().hex}",
            candidate_id=candidate.id,
            skill_id=candidate.skill_id,
            version=candidate.version,
            digest=digest,
            passed=passed,
            manifest_valid=bool(result.get("manifest_valid")),
            permissions_valid=bool(result.get("permissions_valid")),
            scan_passed=bool(result.get("scan_passed")),
            tests_passed=bool(result.get("tests_passed")),
            violations=violations_tuple,
            created_at=_maintenant(),
            details={
                "files_scanned": result.get("files_scanned", []),
                "returncode": result.get("returncode"),
                "timeout": result.get("timeout", False),
                "memory_limit_mb": result.get("memory_limit_mb"),
                "cpu_limit_seconds": result.get("cpu_limit_seconds"),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            },
        )
        self.store.save_report(report)
        self.store.change_candidate_status(
            candidate.id,
            "validated" if report.passed else "quarantined",
            {"report_id": report.id, "violations": list(report.violations)},
        )
        return report

    def activate_candidate(
        self,
        candidate_id: str,
        report_id: str,
        *,
        approved_by: str,
    ) -> ActivationResult:
        """Active explicitement l'artefact exact couvert par un rapport réussi."""

        approbateur = approved_by.strip()
        if approbateur not in self.authorized_approvers:
            raise PermissionError("Approbateur non autorisé pour les skills.")
        candidate = self.store.candidate(candidate_id)
        if candidate is None:
            raise KeyError(f"Candidate inconnue : {candidate_id}")
        if candidate.status != "validated":
            raise ValueError(
                f"Candidate non activable dans l'état {candidate.status!r}."
            )
        report = self.store.report(report_id)
        if report is None:
            raise KeyError(f"Rapport inconnu : {report_id}")
        if report.candidate_id != candidate.id:
            raise ValueError("Le rapport appartient à une autre candidate.")
        if not report.passed:
            raise ValueError("Un rapport en échec ne peut activer aucune skill.")

        source = Path(candidate.path).resolve()
        digest = artifact_digest(source)
        if digest != candidate.digest or digest != report.digest:
            raise ValueError("La candidate a changé après sa validation.")
        manifest = SkillManifest.load(source / "skill.json")
        if manifest.id != candidate.skill_id or manifest.version != candidate.version:
            raise ValueError("Le manifeste ne correspond plus à la candidate validée.")

        target = self.active_dir / manifest.id.replace(".", "_") / manifest.version
        created = False
        if target.exists():
            if artifact_digest(target) != digest:
                raise FileExistsError("Une autre version occupe déjà ce chemin actif.")
        else:
            self._copier_actif(source, target, manifest)
            created = True
        try:
            previous = self.registry.activate(
                manifest.id,
                manifest.version,
                report.id,
                str(target),
                digest=digest,
                approved_by=approbateur,
            )
        except Exception:
            if created:
                shutil.rmtree(target, ignore_errors=True)
            raise

        if previous and previous != candidate.version:
            for autre in self.store.candidates():
                if (
                    autre.id != candidate.id
                    and autre.skill_id == candidate.skill_id
                    and autre.version == previous
                    and autre.status == "activated"
                ):
                    self.store.change_candidate_status(
                        autre.id,
                        "superseded",
                        {
                            "replaced_by": candidate.version,
                            "approved_by": approbateur,
                        },
                    )

        self.store.change_candidate_status(
            candidate.id,
            "activated",
            {
                "report_id": report.id,
                "approved_by": approbateur,
                "active_path": str(target),
            },
        )
        return ActivationResult(
            skill_id=manifest.id,
            version=manifest.version,
            report_id=report.id,
            digest=digest,
            active_path=str(target),
            approved_by=approbateur,
            previous_version=previous,
        )

    def rollback(self, skill_id: str, *, approved_by: str) -> dict[str, Any] | None:
        """Demande au registre de restaurer la version précédente complète."""

        approbateur = approved_by.strip()
        if approbateur not in self.authorized_approvers:
            raise PermissionError("Approbateur non autorisé pour le rollback.")
        active = self.registry.active(skill_id)
        if active is None:
            raise KeyError(skill_id)
        restored = self.registry.rollback(skill_id)
        for candidate in self.store.candidates():
            if candidate.skill_id != skill_id:
                continue
            if restored is not None and candidate.version == restored["version"]:
                self.store.change_candidate_status(
                    candidate.id,
                    "activated",
                    {"rollback_by": approbateur},
                )
            elif candidate.version == active["version"]:
                self.store.change_candidate_status(
                    candidate.id,
                    "archived",
                    {"rollback_by": approbateur},
                )
        return restored

    @staticmethod
    def _copier_actif(
        source: Path,
        target: Path,
        manifest: SkillManifest,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{manifest.id.replace('.', '_')}-", dir=target.parent)
        )
        staged = temporary_root / "artifact"
        try:
            shutil.copytree(source, staged, symlinks=False)
            payload = manifest.vers_dict()
            payload["status"] = "active"
            (staged / "skill.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if artifact_digest(staged) != artifact_digest(source):
                raise ValueError("La copie active diffère de la candidate validée.")
            staged.replace(target)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    @staticmethod
    def _slug(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = "".join(
            char for char in normalized if not unicodedata.combining(char)
        ).casefold()
        slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
        if not slug:
            raise ValueError("Impossible de créer un identifiant depuis la relation.")
        if slug[0].isdigit():
            slug = f"action_{slug}"
        return slug[:64]
