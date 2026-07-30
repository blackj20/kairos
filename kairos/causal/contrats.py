"""Chargement strict des résultats attendus par capacité et par route."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ErreurContratResultat(RuntimeError):
    """Signale un contrat causal absent ou incohérent."""


class CatalogueResultats:
    TYPES = {"bool", "dict", "list", "number", "str", "nullable"}

    def __init__(self, chemin: Path | None = None) -> None:
        racine = Path(__file__).resolve().parent.parent.parent
        self.chemin = chemin or racine / "data" / "cognition" / "capability_outcomes.json"
        try:
            contenu = json.loads(self.chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurContratResultat(
                f"Contrats de résultat invalides : {self.chemin}"
            ) from erreur
        if not isinstance(contenu, dict) or contenu.get("version") != 1:
            raise ErreurContratResultat("Les contrats doivent être de version 1.")
        self.capacites = self._registre(contenu, "capabilities")
        self.routes = self._registre(contenu, "routes")
        self._valider()

    @staticmethod
    def _registre(contenu: dict[str, Any], cle: str) -> dict[str, dict[str, Any]]:
        registre = contenu.get(cle)
        if not isinstance(registre, dict):
            raise ErreurContratResultat(f"Registre causal absent : {cle}")
        return {
            str(nom).casefold(): dict(definition)
            for nom, definition in registre.items()
            if isinstance(definition, dict)
        }

    def _valider(self) -> None:
        for nom, definition in self.capacites.items():
            sorties = definition.get("required_outputs")
            if not isinstance(sorties, dict):
                raise ErreurContratResultat(
                    f"La capacité « {nom} » doit déclarer required_outputs."
                )
            inconnus = {
                str(type_attendu)
                for type_attendu in sorties.values()
                if str(type_attendu) not in self.TYPES
            }
            if inconnus:
                raise ErreurContratResultat(
                    f"Types causaux inconnus pour « {nom} » : {sorted(inconnus)}"
                )
        for route, definition in self.routes.items():
            conditions = definition.get("success_conditions")
            if not isinstance(conditions, list) or not conditions:
                raise ErreurContratResultat(
                    f"La route « {route} » doit déclarer ses conditions de succès."
                )
            for condition in conditions:
                if not isinstance(condition, dict) or not condition.get("id"):
                    raise ErreurContratResultat(
                        f"Condition causale invalide dans « {route} »."
                    )

    def capacite(self, nom: str) -> dict[str, Any] | None:
        definition = self.capacites.get(nom.casefold())
        return dict(definition) if definition is not None else None

    def route(self, route_id: str) -> dict[str, Any] | None:
        definition = self.routes.get(route_id.casefold())
        return dict(definition) if definition is not None else None
