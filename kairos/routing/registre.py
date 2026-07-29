"""Registre explicite des fonctions réellement disponibles."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .catalogue import CatalogueRoute

GestionnaireCapacite = Callable[[dict[str, Any]], dict[str, Any]]


class RegistreCapacites:
    """Lie un identifiant déclaré à un handler fourni par le Kernel."""

    def __init__(self, catalogue: CatalogueRoute) -> None:
        self.catalogue = catalogue
        self._handlers: dict[str, GestionnaireCapacite] = {}

    def enregistrer(
        self,
        capacite: str,
        handler: GestionnaireCapacite,
        *,
        permissions: Iterable[str] = (),
    ) -> None:
        nom = capacite.casefold().strip()
        definition = self.catalogue.capacites.get(nom)
        if definition is None:
            raise KeyError(f"Capacité non déclarée : {capacite}")
        requises = set(definition.get("permissions", []))
        accordees = {str(item) for item in permissions}
        if not requises.issubset(accordees):
            manquantes = sorted(requises - accordees)
            raise PermissionError(
                f"Permissions manquantes pour « {nom} » : {manquantes}"
            )
        if not callable(handler):
            raise TypeError("Le gestionnaire de capacité doit être appelable.")
        self._handlers[nom] = handler

    def disponible(self, capacite: str) -> bool:
        return capacite.casefold() in self._handlers

    def executer(
        self, capacite: str, contexte: dict[str, Any]
    ) -> dict[str, Any]:
        nom = capacite.casefold()
        handler = self._handlers.get(nom)
        if handler is None:
            raise LookupError(f"Capacité indisponible : {nom}")
        resultat = handler(dict(contexte))
        if not isinstance(resultat, dict):
            raise TypeError(
                f"La capacité « {nom} » doit retourner un dictionnaire."
            )
        return resultat
