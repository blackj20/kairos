"""Compilation sûre de JSON déclaratif en plans de route."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .catalogue import CatalogueRoute
from .modeles import EtapeRoute, PlanRoute, StatutRoute
from .registre import GestionnaireCapacite, RegistreCapacites


def _cle(valeur: str) -> str:
    texte = unicodedata.normalize("NFKD", valeur.casefold())
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"\s+", " ", texte).strip()


class RouteurDynamique:
    """Compile un graphe sans jamais importer un handler depuis le JSON."""

    def __init__(
        self,
        catalogue: CatalogueRoute | None = None,
        registre: RegistreCapacites | None = None,
    ) -> None:
        self.catalogue = catalogue or CatalogueRoute()
        self.registre = registre or RegistreCapacites(self.catalogue)

    def enregistrer_capacite(
        self,
        capacite: str,
        handler: GestionnaireCapacite,
        *,
        permissions: tuple[str, ...] = (),
    ) -> None:
        self.registre.enregistrer(
            capacite, handler, permissions=permissions
        )

    def planifier(
        self, action: str, cible: str | None = None
    ) -> PlanRoute:
        action_cle = _cle(action)
        definition = self.catalogue.actions.get(action_cle)
        if definition is None:
            return PlanRoute(
                id="unresolved",
                action=action_cle,
                objectif="action non déclarée",
                statut=StatutRoute.BLOCKED,
                cible=cible,
                raison="aucun schéma d'action connu",
            )

        objectif = str(definition.get("goal", action_cle))
        route_id = str(definition.get("route") or "").casefold()
        generee = False
        route = self.catalogue.routes.get(route_id) if route_id else None
        if route is not None:
            etapes_brutes = route["steps"]
        else:
            compose = definition.get("compose", [])
            if not compose:
                return PlanRoute(
                    id=route_id or f"generated.{action_cle}",
                    action=action_cle,
                    objectif=objectif,
                    statut=StatutRoute.BLOCKED,
                    cible=cible,
                    raison="route absente et aucune composition déclarée",
                )
            generee = True
            route_id = route_id or f"generated.{action_cle}"
            etapes_brutes = [
                {
                    "id": f"step_{index}",
                    "capability": capacite,
                    "required": True,
                }
                for index, capacite in enumerate(compose, start=1)
            ]

        etapes = tuple(
            EtapeRoute(
                id=str(item.get("id") or f"step_{index}"),
                capacite=str(item["capability"]).casefold(),
                obligatoire=bool(item.get("required", True)),
            )
            for index, item in enumerate(etapes_brutes, start=1)
        )

        if bool(definition.get("target_required")) and not str(
            cible or ""
        ).strip():
            return PlanRoute(
                id=route_id,
                action=action_cle,
                objectif=objectif,
                statut=StatutRoute.BLOCKED,
                etapes=etapes,
                cible=cible,
                generee=generee,
                score=40,
                raison="cible obligatoire absente",
            )

        manquantes = tuple(
            etape.capacite
            for etape in etapes
            if etape.obligatoire
            and not self.registre.disponible(etape.capacite)
        )
        if manquantes:
            return PlanRoute(
                id=route_id,
                action=action_cle,
                objectif=objectif,
                statut=StatutRoute.BLOCKED,
                etapes=etapes,
                capacites_manquantes=manquantes,
                cible=cible,
                generee=generee,
                score=max(10, 100 - 20 * len(manquantes)),
                raison="capacités obligatoires indisponibles",
            )

        statut = StatutRoute.CANDIDATE if generee else StatutRoute.READY
        return PlanRoute(
            id=route_id,
            action=action_cle,
            objectif=objectif,
            statut=statut,
            etapes=etapes,
            cible=cible,
            generee=generee,
            score=70 if generee else 100,
            raison=(
                "route composée à valider par Tester et SECAU"
                if generee
                else "route déclarée complète"
            ),
        )

    def executer(
        self, plan: PlanRoute, contexte: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if plan.statut is not StatutRoute.READY:
            raise PermissionError(
                f"Une route {plan.statut.value!r} ne peut pas être exécutée."
            )
        etat: dict[str, Any] = {
            "action": plan.action,
            "target": plan.cible,
            **(contexte or {}),
        }
        trace: list[dict[str, Any]] = []
        for etape in plan.etapes:
            if not self.registre.disponible(etape.capacite):
                if etape.obligatoire:
                    raise LookupError(
                        f"Capacité devenue indisponible : {etape.capacite}"
                    )
                continue
            resultat = self.registre.executer(etape.capacite, etat)
            etat.update(resultat)
            trace.append(
                {
                    "step": etape.id,
                    "capability": etape.capacite,
                    "status": "success",
                }
            )
        return {**etat, "route_id": plan.id, "trace": trace}
