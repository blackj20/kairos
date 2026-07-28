"""Production de plans d'apprentissage sans exécution implicite."""

from __future__ import annotations

import hashlib

from .modeles import GroupeApprentissage, PlanApprentissage, ScorePriorite
from ..cognition import Reflechir


class Planificateur:
    """Décide ce qu'il manque, jamais ce qui doit être confirmé."""

    def planifier(
        self,
        groupe: GroupeApprentissage,
        priorite: ScorePriorite,
    ) -> PlanApprentissage:
        sujet = groupe.relation_source or groupe.focus or groupe.champ
        manques: list[str] = []
        questions: list[str] = []

        if groupe.contradictions:
            route = "demander_createur"
            manques.append("target_confirmation")
            questions.append(
                f"Plusieurs sens sont proposés pour « {sujet} ». "
                "Quel verbe canonique est correct, et dans quel contexte ?"
            )
        elif groupe.relation_source and groupe.relation_target:
            route = "collecter_preuves" if groupe.occurrences >= 3 else "observer"
        else:
            route = "demander_createur"
            manques.extend(("definition", "target"))
            questions.extend(
                (
                    f"Que signifie précisément « {sujet} » dans ces requêtes ?",
                    f"À quelle action ou quel concept canonique « {sujet} » doit-il être relié ?",
                )
            )

        for manque in ("source", "examples", "counterexamples", "regressions"):
            if manque not in manques:
                manques.append(manque)

        questions.extend(Reflechir.questions_for(sujet, ("source", "examples", "counterexamples")))
        questions.append(
            f"Quelles formulations proches de « {sujet} » ne doivent surtout pas être modifiées ?"
        )

        digest = hashlib.sha256(groupe.id.encode("utf-8")).hexdigest()[:20]
        objectif = (
            f"Valider la relation « {groupe.relation_source} → "
            f"{groupe.relation_target} »"
            if groupe.relation_source and groupe.relation_target
            else f"Résoudre le manque « {sujet} »"
        )
        return PlanApprentissage(
            id=f"growup_plan_{digest}",
            groupe_id=groupe.id,
            objectif=objectif,
            route=route,
            manques=tuple(dict.fromkeys(manques)),
            questions=tuple(dict.fromkeys(questions)),
            tests_requis=6,
            priorite=priorite,
        )
