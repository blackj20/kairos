"""Scénarios d'acceptation historiques indispensables à Kairos."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "artifacts" / "user_acceptance"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class Resultat:
    nom: str
    succes: bool
    code_retour: int
    duree_ms: int
    details: str
    sortie: str


def lancer(
    arguments: list[str],
    entree: str | None = None,
) -> tuple[int, str, int]:
    debut = time.perf_counter()
    process = subprocess.run(
        arguments,
        input=entree,
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=30,
        check=False,
    )
    duree = round((time.perf_counter() - debut) * 1000)
    return process.returncode, (process.stdout + process.stderr).strip(), duree


def verifier(
    nom: str,
    arguments: list[str],
    fragments: tuple[str, ...],
    entree: str | None = None,
) -> Resultat:
    code, sortie, duree = lancer(arguments, entree)
    manquants = [
        fragment
        for fragment in fragments
        if fragment.casefold() not in sortie.casefold()
    ]
    succes = code == 0 and not manquants
    return Resultat(
        nom=nom,
        succes=succes,
        code_retour=code,
        duree_ms=duree,
        details=(
            "attentes présentes"
            if succes
            else f"fragments absents: {manquants}"
        ),
        sortie=sortie,
    )


def main() -> int:
    resultats = [
        verifier(
            "Faute historique atoms → atome",
            ["kairos", "c'est", "quoi", "un", "atoms", "?"],
            ("atome",),
        ),
        verifier(
            "Conversation installe → python",
            ["kairos"],
            (
                "Quelle est la cible",
                "Réponse reliée à l'expérience",
                "pas encore confirmée",
            ),
            entree="installe\npython\nquit\n",
        ),
        verifier(
            "Connaissance de son identité",
            ["kairos", "qui", "es", "tu", "?"],
            ("K.A.I.R.O.S.", "0.5.0-skill-factory"),
        ),
        verifier(
            "Connaissance de son objectif courant",
            ["kairos", "quel", "est", "ton", "objectif", "?"],
            ("comprendre", "classifier"),
        ),
    ]

    total = len(resultats)
    reussis = sum(resultat.succes for resultat in resultats)
    payload = {
        "resume": {
            "total": total,
            "reussis": reussis,
            "echoues": total - reussis,
            "taux_reussite": round(reussis / total * 100, 2),
        },
        "resultats": [asdict(resultat) for resultat in resultats],
    }
    (REPORT_DIR / "USER_ACCEPTANCE_ADDITIONAL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lignes = [
        "# Rapport d’acceptation complémentaire — K.A.I.R.O.S. V0.5",
        "",
        f"Résultat : **{reussis}/{total}** scénarios réussis.",
        "",
    ]
    for resultat in resultats:
        statut = "✅" if resultat.succes else "❌"
        lignes.extend(
            [
                f"## {statut} {resultat.nom}",
                "",
                f"- Code retour : `{resultat.code_retour}`",
                f"- Mesure : {resultat.details}",
                "",
                "```text",
                resultat.sortie or "(aucune sortie)",
                "```",
                "",
            ]
        )
    (REPORT_DIR / "USER_ACCEPTANCE_ADDITIONAL.md").write_text(
        "\n".join(lignes),
        encoding="utf-8",
    )

    print(
        f"USER_ACCEPTANCE_ADDITIONAL: {reussis}/{total} scénarios réussis"
    )
    for resultat in resultats:
        statut = "PASS" if resultat.succes else "FAIL"
        print(f"[{statut}] {resultat.nom}: {resultat.details}")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
