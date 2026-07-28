"""Lecture des règles déclaratives de décision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ErreurConfigurationDecision(RuntimeError):
    """Signale une règle de décision absente ou invalide."""


class ConfigurationDecision:
    FICHIERS = ("questions.json", "routes.json", "thresholds.json")

    def __init__(self, dossier: Path | None = None) -> None:
        racine = Path(__file__).resolve().parent.parent.parent
        self.dossier = dossier or racine / "data" / "decision"
        self._donnees = {
            nom.removesuffix(".json"): self._lire(nom)
            for nom in self.FICHIERS
        }

    def _lire(self, nom: str) -> dict[str, Any]:
        chemin = self.dossier / nom
        try:
            with chemin.open("r", encoding="utf-8") as fichier:
                donnees = json.load(fichier)
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurConfigurationDecision(
                f"Configuration de décision invalide : {chemin}"
            ) from erreur
        if not isinstance(donnees, dict):
            raise ErreurConfigurationDecision(
                f"{chemin} doit contenir un objet JSON."
            )
        return donnees

    @property
    def questions(self) -> dict[str, Any]:
        return self._donnees["questions"]

    @property
    def routes(self) -> dict[str, Any]:
        return self._donnees["routes"]

    @property
    def seuils(self) -> dict[str, int]:
        return self._donnees["thresholds"]
