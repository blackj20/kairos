"""Mesure reproductible de la fondation, sans modifier son état."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kairos import Kernel


@dataclass(frozen=True, slots=True)
class MetriquesGroupe:
    total: int
    intentions_correctes: int
    cas_exacts: int

    @property
    def intention_accuracy(self) -> float:
        return 100.0 * self.intentions_correctes / self.total

    @property
    def exact_accuracy(self) -> float:
        return 100.0 * self.cas_exacts / self.total


def executer_benchmark(chemin: Path | None = None) -> dict[str, Any]:
    racine = Path(__file__).resolve().parent
    chemin = chemin or racine / "benchmarks" / "comprendre.json"
    with chemin.open("r", encoding="utf-8") as fichier:
        corpus = json.load(fichier)

    kernel = Kernel()
    compteurs = {
        "core": {"total": 0, "intentions": 0, "exacts": 0},
        "variant": {"total": 0, "intentions": 0, "exacts": 0},
    }
    echecs: list[dict[str, Any]] = []
    fausses_executions = 0

    for cas in corpus["cases"]:
        groupe = cas["group"]
        attendu = cas["expected"]
        decision = kernel.traiter(cas["text"])
        analyse = decision.analyse
        obtenu = {
            "type": analyse.type_requete.valeur,
            "action": analyse.action.valeur,
            "cible": analyse.cible.valeur,
            "route": decision.route,
        }

        compteurs[groupe]["total"] += 1
        intention_correcte = obtenu["type"] == attendu["type"]
        if intention_correcte:
            compteurs[groupe]["intentions"] += 1

        exact = all(obtenu[cle_attendue] == valeur for cle_attendue, valeur in attendu.items())
        if exact:
            compteurs[groupe]["exacts"] += 1
        else:
            echecs.append(
                {
                    "group": groupe,
                    "text": cas["text"],
                    "expected": attendu,
                    "obtained": obtenu,
                    "verification": asdict(analyse.verification),
                }
            )

        if decision.route == "competence" and attendu["route"] != "competence":
            fausses_executions += 1

    groupes = {
        nom: MetriquesGroupe(
            total=valeurs["total"],
            intentions_correctes=valeurs["intentions"],
            cas_exacts=valeurs["exacts"],
        )
        for nom, valeurs in compteurs.items()
    }
    criteres = kernel.soi.objective["validation"]
    valide = (
        groupes["core"].exact_accuracy >= criteres["core_cases_accuracy"]
        and groupes["variant"].intention_accuracy
        >= criteres["variant_intent_accuracy_min"]
        and fausses_executions <= criteres["unsafe_false_executions_max"]
    )

    return {
        "foundation_validated": valide,
        "groups": {
            nom: {
                "total": groupe.total,
                "intention_accuracy": round(groupe.intention_accuracy, 2),
                "exact_accuracy": round(groupe.exact_accuracy, 2),
            }
            for nom, groupe in groupes.items()
        },
        "unsafe_false_executions": fausses_executions,
        "criteria": criteres,
        "failures": echecs,
    }


def main() -> int:
    resultat = executer_benchmark()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0 if resultat["foundation_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
