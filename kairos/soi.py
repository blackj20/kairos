"""Connaissances protégées de Kairos sur lui-même et son créateur."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ErreurIdentite(RuntimeError):
    """Signale une identité centrale absente ou invalide."""


class ConnaissanceDeSoi:
    """Charge l'identité sans permettre sa modification implicite."""

    FICHIERS_SELF = (
        "identity.json",
        "home.json",
        "objective.json",
        "capabilities.json",
        "limits.json",
        "state.json",
    )

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = racine or Path(__file__).resolve().parent.parent
        self._self = {
            nom.removesuffix(".json"): self._lire(self.racine / "self" / nom)
            for nom in self.FICHIERS_SELF
        }
        self._creator = self._lire(
            self.racine / "relations" / "creator.json"
        )

    @staticmethod
    def _lire(chemin: Path) -> dict[str, Any]:
        try:
            with chemin.open("r", encoding="utf-8") as fichier:
                donnees = json.load(fichier)
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurIdentite(
                f"Connaissance identitaire invalide : {chemin}"
            ) from erreur
        if not isinstance(donnees, dict):
            raise ErreurIdentite(f"{chemin} doit contenir un objet JSON.")
        return donnees

    @property
    def identity(self) -> dict[str, Any]:
        return dict(self._self["identity"])

    @property
    def home(self) -> dict[str, Any]:
        return dict(self._self["home"])

    @property
    def objective(self) -> dict[str, Any]:
        return dict(self._self["objective"])

    @property
    def capabilities(self) -> dict[str, Any]:
        return dict(self._self["capabilities"])

    @property
    def limits(self) -> dict[str, Any]:
        return dict(self._self["limits"])

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._self["state"])

    @property
    def creator(self) -> dict[str, Any]:
        return dict(self._creator)

    def resume(self) -> dict[str, Any]:
        return {
            "name": self.identity["name"],
            "home": self.home["root"],
            "objective": self.objective["current"],
            "creator": self.creator["name"],
            "phase": self.state["phase"],
        }
