"""Acceptation V0.5 via la commande installée ``kairos`` uniquement."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kairos.growup import (
    GroupeApprentissage,
    PlanApprentissage,
    ScorePriorite,
    StockageGrowUp,
)


ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "memory"
REPORT_DIR = ROOT / "artifacts" / "user_acceptance"


@dataclass(slots=True)
class Resultat:
    nom: str
    succes: bool
    code_retour: int
    duree_ms: int
    details: str
    sortie: str


def nettoyer() -> None:
    MEMORY.mkdir(parents=True, exist_ok=True)
    for nom in (
        "growup.db",
        "growup.db-shm",
        "growup.db-wal",
        "skills.db",
        "skills.db-shm",
        "skills.db-wal",
        "skill_registry.json",
    ):
        path = MEMORY / nom
        if path.exists():
            path.unlink()
    for dossier in (ROOT / "skills" / "candidates", ROOT / "skills" / "active"):
        dossier.mkdir(parents=True, exist_ok=True)
        for item in dossier.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def preparer_plan() -> None:
    stockage = StockageGrowUp(MEMORY / "growup.db")
    try:
        groupe = GroupeApprentissage(
            id="group_cli_v05",
            cle="relation:deploie",
            champ="relation",
            focus="deploie",
            observation_ids=("obs_cli_1", "obs_cli_2", "obs_cli_3"),
            experience_ids=("exp_cli_1",),
            evenement_ids=("event_cli_1",),
            occurrences=3,
            relation_source="deploie",
            relation_targets=("installer",),
        )
        plan = PlanApprentissage(
            id="plan_cli_v05",
            groupe_id=groupe.id,
            objectif="comprendre deploie",
            route="collecter_preuves",
            manques=(),
            questions=(),
            tests_requis=6,
            priorite=ScorePriorite(90, 90, 90, 90, 90),
        )
        stockage.sauvegarder_groupe(groupe)
        stockage.sauvegarder_plan(plan)
        stockage.changer_statut_plan(plan.id, "promoted")
    finally:
        stockage.close()


def lancer(*arguments: str) -> tuple[int, str, int]:
    debut = time.perf_counter()
    process = subprocess.run(
        ["kairos", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )
    duree = round((time.perf_counter() - debut) * 1000)
    return process.returncode, (process.stdout + process.stderr).strip(), duree


def json_command(*arguments: str) -> tuple[int, dict[str, Any], str, int]:
    code, sortie, duree = lancer(*arguments)
    try:
        payload = json.loads(sortie) if sortie else {}
    except json.JSONDecodeError:
        payload = {}
    return code, payload, sortie, duree


def ajouter(
    resultats: list[Resultat],
    nom: str,
    code: int,
    sortie: str,
    duree: int,
    succes: bool,
    details: str,
) -> None:
    resultats.append(
        Resultat(
            nom=nom,
            succes=succes,
            code_retour=code,
            duree_ms=duree,
            details=details,
            sortie=sortie,
        )
    )


def main() -> int:
    nettoyer()
    preparer_plan()
    resultats: list[Resultat] = []

    code, scan, sortie, duree = json_command("--skill-factory-scan")
    plans = scan.get("eligible_plans", [])
    ajouter(
        resultats,
        "Plan promu visible depuis la CLI",
        code,
        sortie,
        duree,
        code == 0 and any(plan.get("id") == "plan_cli_v05" for plan in plans),
        f"{len(plans)} plan(s) éligible(s)",
    )

    code, generated, sortie, duree = json_command(
        "--skill-generate",
        "plan_cli_v05",
        "--skill-version",
        "0.1.0",
    )
    candidate_v1 = str(generated.get("id", ""))
    skill_id = str(generated.get("skill_id", ""))
    ajouter(
        resultats,
        "Génération candidate inactive V1",
        code,
        sortie,
        duree,
        code == 0
        and candidate_v1.startswith("candidate_")
        and skill_id == "learned.deploie",
        f"candidate={candidate_v1 or 'absente'}",
    )

    code, scan, sortie, duree = json_command("--skill-factory-scan")
    ajouter(
        resultats,
        "Aucune activation automatique",
        code,
        sortie,
        duree,
        code == 0 and scan.get("active_skills") == [],
        f"active_skills={len(scan.get('active_skills', []))}",
    )

    code, report_v1, sortie, duree = json_command(
        "--skill-validate",
        candidate_v1,
    )
    report_id_v1 = str(report_v1.get("id", ""))
    ajouter(
        resultats,
        "Validation sandbox V1",
        code,
        sortie,
        duree,
        code == 0
        and report_v1.get("passed") is True
        and report_id_v1.startswith("skill_report_"),
        f"report={report_id_v1 or 'absent'}",
    )

    code, sortie, duree = lancer(
        "--skill-activate",
        candidate_v1,
        "--report-id",
        report_id_v1,
        "--approved-by",
        "intrus",
    )
    ajouter(
        resultats,
        "Intrus refusé",
        code,
        sortie,
        duree,
        code != 0 and "SKILL_FACTORY_ERROR" in sortie,
        "activation non autorisée bloquée",
    )

    code, activated_v1, sortie, duree = json_command(
        "--skill-activate",
        candidate_v1,
        "--report-id",
        report_id_v1,
        "--approved-by",
        "Jps",
    )
    path_v1 = str(activated_v1.get("active_path", ""))
    ajouter(
        resultats,
        "Activation humaine V1",
        code,
        sortie,
        duree,
        code == 0
        and activated_v1.get("approved_by") == "Jps"
        and Path(path_v1).is_dir(),
        f"active_path={path_v1 or 'absent'}",
    )

    code, generated_v2, sortie, duree = json_command(
        "--skill-generate",
        "plan_cli_v05",
        "--skill-version",
        "0.2.0",
    )
    candidate_v2 = str(generated_v2.get("id", ""))
    ajouter(
        resultats,
        "Génération candidate V2",
        code,
        sortie,
        duree,
        code == 0 and candidate_v2.startswith("candidate_"),
        f"candidate={candidate_v2 or 'absente'}",
    )

    code, report_v2, sortie, duree = json_command(
        "--skill-validate",
        candidate_v2,
    )
    report_id_v2 = str(report_v2.get("id", ""))
    ajouter(
        resultats,
        "Validation sandbox V2",
        code,
        sortie,
        duree,
        code == 0 and report_v2.get("passed") is True,
        f"report={report_id_v2 or 'absent'}",
    )

    code, activated_v2, sortie, duree = json_command(
        "--skill-activate",
        candidate_v2,
        "--report-id",
        report_id_v2,
        "--approved-by",
        "Jps",
    )
    ajouter(
        resultats,
        "Activation versionnée V2",
        code,
        sortie,
        duree,
        code == 0 and activated_v2.get("previous_version") == "0.1.0",
        f"previous={activated_v2.get('previous_version')}",
    )

    code, restored, sortie, duree = json_command(
        "--skill-rollback",
        skill_id,
        "--approved-by",
        "Jps",
    )
    ajouter(
        resultats,
        "Rollback complet vers V1",
        code,
        sortie,
        duree,
        code == 0
        and restored.get("version") == "0.1.0"
        and restored.get("path") == path_v1
        and restored.get("report_id") == report_id_v1,
        f"restored={restored.get('version')}",
    )

    code, tampered, sortie, duree = json_command(
        "--skill-generate",
        "plan_cli_v05",
        "--skill-version",
        "0.3.0",
    )
    tampered_id = str(tampered.get("id", ""))
    code_report, tampered_report, sortie_report, duree_report = json_command(
        "--skill-validate",
        tampered_id,
    )
    tampered_path = Path(str(tampered.get("path", ""))) / "handler.py"
    if tampered_path.is_file():
        tampered_path.write_text(
            tampered_path.read_text(encoding="utf-8") + "\n# altération\n",
            encoding="utf-8",
        )
    code_activation, sortie_activation, duree_activation = lancer(
        "--skill-activate",
        tampered_id,
        "--report-id",
        str(tampered_report.get("id", "")),
        "--approved-by",
        "Jps",
    )
    ajouter(
        resultats,
        "Altération après rapport bloquée",
        code_activation,
        "\n".join((sortie, sortie_report, sortie_activation)),
        duree + duree_report + duree_activation,
        code == 0
        and code_report == 0
        and code_activation != 0
        and "changé" in sortie_activation,
        "empreinte modifiée refusée",
    )

    total = len(resultats)
    reussis = sum(resultat.succes for resultat in resultats)
    payload = {
        "version_testee": "0.5.0",
        "resume": {
            "total": total,
            "reussis": reussis,
            "echoues": total - reussis,
            "taux_reussite": round(reussis / total * 100, 2),
        },
        "resultats": [asdict(resultat) for resultat in resultats],
    }
    json_path = REPORT_DIR / "USER_ACCEPTANCE_V05.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lignes = [
        "# Acceptation utilisateur — Skill Factory V0.5",
        "",
        f"Résultat : **{reussis}/{total}** scénarios réussis.",
        "",
    ]
    for resultat in resultats:
        lignes.extend(
            [
                f"## {'✅' if resultat.succes else '❌'} {resultat.nom}",
                "",
                f"- Code retour : `{resultat.code_retour}`",
                f"- Détail : {resultat.details}",
                "",
                "```text",
                resultat.sortie or "(aucune sortie)",
                "```",
                "",
            ]
        )
    md_path = REPORT_DIR / "USER_ACCEPTANCE_V05.md"
    md_path.write_text("\n".join(lignes), encoding="utf-8")

    print(f"USER_ACCEPTANCE_V05: {reussis}/{total} scénarios réussis")
    for resultat in resultats:
        print(f"[{'PASS' if resultat.succes else 'FAIL'}] {resultat.nom}: {resultat.details}")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
