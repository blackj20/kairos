"""Acceptation V0.6 depuis la commande installée uniquement."""

from __future__ import annotations

import json
import subprocess


def lancer(*arguments: str) -> tuple[int, str]:
    process = subprocess.run(
        ["kairos", *arguments],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return process.returncode, (process.stdout + process.stderr).strip()


def main() -> int:
    resultats: list[tuple[str, bool]] = []

    code, sortie = lancer(
        "--route-plan", "chercher", "--route-target", "atome"
    )
    plan = json.loads(sortie) if code == 0 else {}
    resultats.append((
        "Route chercher compilée",
        code == 0
        and plan.get("id") == "information.search"
        and plan.get("statut") == "blocked"
        and "web.search" in plan.get("capacites_manquantes", []),
    ))

    code, sortie = lancer("cherche", "toi-même", "atome")
    resultats.append((
        "Ordre autonome ancré sans fausse exécution",
        code == 0
        and "Plan       : information.search (blocked)" in sortie
        and "Capacités manquantes" in sortie,
    ))

    code, sortie = lancer(
        "--route-plan", "enqueter", "--route-target", "quark"
    )
    candidate = json.loads(sortie) if code == 0 else {}
    resultats.append((
        "Route inexistante composée mais bloquée",
        code == 0
        and candidate.get("id") == "generated.enqueter"
        and candidate.get("generee") is True
        and candidate.get("statut") == "blocked",
    ))

    code, sortie = lancer("--secau-status")
    secau = json.loads(sortie) if code == 0 else {}
    resultats.append((
        "Observabilité SECAU disponible",
        code == 0
        and isinstance(secau.get("count"), int)
        and isinstance(secau.get("events"), list),
    ))

    reussis = sum(succes for _, succes in resultats)
    total = len(resultats)
    print(f"USER_ACCEPTANCE_V06: {reussis}/{total} scénarios réussis")
    for nom, succes in resultats:
        print(f"[{'PASS' if succes else 'FAIL'}] {nom}")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
