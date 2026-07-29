"""Acceptation V0.7 depuis la commande installée, sans dépendance réseau."""

from __future__ import annotations

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

    code, sortie = lancer("cherche", "toi-même", "atoms")
    resultats.append((
        "Recherche autonome dans la mémoire confirmée",
        code == 0
        and "Action     : chercher" in sortie
        and "Cible      : atome" in sortie
        and "Plan       : information.search (ready)" in sortie
        and "Source confirmée" in sortie,
    ))

    code, sortie = lancer("cherche", "xylophore")
    resultats.append((
        "Absence de connaissance annoncée sans invention",
        code == 0
        and "Aucune connaissance confirmée" in sortie
        and "--online" in sortie,
    ))

    code, sortie = lancer("--help")
    resultats.append((
        "Autorisation Web explicite disponible",
        code == 0 and "--online" in sortie and "lecture seule" in sortie,
    ))

    reussis = sum(succes for _, succes in resultats)
    total = len(resultats)
    print(f"USER_ACCEPTANCE_V07: {reussis}/{total} scénarios réussis")
    for nom, succes in resultats:
        print(f"[{'PASS' if succes else 'FAIL'}] {nom}")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
