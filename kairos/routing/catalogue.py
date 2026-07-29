"""Chargement strict des actions, routes et capacités déclaratives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ErreurCatalogueRoute(RuntimeError):
    """Signale une définition de routage absente ou incohérente."""


class CatalogueRoute:
    FICHIERS = ("actions.json", "routes.json", "capabilities.json")

    def __init__(self, dossier: Path | None = None) -> None:
        racine = Path(__file__).resolve().parent.parent.parent
        self.dossier = dossier or racine / "data" / "routing"
        donnees = {
            nom.removesuffix(".json"): self._lire(nom)
            for nom in self.FICHIERS
        }
        self.actions = self._registre(donnees["actions"], "actions")
        self.routes = self._registre(donnees["routes"], "routes")
        self.capacites = self._registre(
            donnees["capabilities"], "capabilities"
        )
        self._valider_references()

    def _lire(self, nom: str) -> dict[str, Any]:
        chemin = self.dossier / nom
        try:
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurCatalogueRoute(
                f"Catalogue de routage invalide : {chemin}"
            ) from erreur
        if not isinstance(contenu, dict) or contenu.get("version") != 1:
            raise ErreurCatalogueRoute(
                f"{chemin} doit être un objet de version 1."
            )
        return contenu

    @staticmethod
    def _registre(
        contenu: dict[str, Any], cle: str
    ) -> dict[str, dict[str, Any]]:
        registre = contenu.get(cle)
        if not isinstance(registre, dict):
            raise ErreurCatalogueRoute(f"Registre « {cle} » absent.")
        return {
            str(nom).casefold(): dict(definition)
            for nom, definition in registre.items()
            if isinstance(definition, dict)
        }

    def _valider_references(self) -> None:
        for route_id, route in self.routes.items():
            etapes = route.get("steps")
            if not isinstance(etapes, list) or not etapes:
                raise ErreurCatalogueRoute(
                    f"La route « {route_id} » doit avoir des étapes."
                )
            for etape in etapes:
                capacite = str(etape.get("capability", "")).casefold()
                if capacite not in self.capacites:
                    raise ErreurCatalogueRoute(
                        f"Capacité inconnue « {capacite} » dans « {route_id} »."
                    )
        for action, definition in self.actions.items():
            compose = definition.get("compose", [])
            if not isinstance(compose, list):
                raise ErreurCatalogueRoute(
                    f"« compose » invalide pour l'action « {action} »."
                )
            inconnues = [
                str(item) for item in compose
                if str(item).casefold() not in self.capacites
            ]
            if inconnues:
                raise ErreurCatalogueRoute(
                    f"Capacités inconnues pour « {action} » : {inconnues}"
                )
