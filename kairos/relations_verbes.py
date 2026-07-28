"""Mémoire évolutive des équivalences entre formes et verbes canoniques."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .normalisation import cle


class MemoireRelationsVerbes:
    """Stocke uniquement des relations explicitement enseignées et confirmées."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Charge un registre optionnel ou démarre en mémoire vive."""

        self.path = Path(path) if path is not None else None
        self._relations: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        if self.path is not None and self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._relations = {
                cle(alias): dict(relation)
                for alias, relation in data.get("relations", {}).items()
            }

    def obtenir(self, alias: str) -> dict[str, Any] | None:
        """Retourne une copie d'une relation confirmée."""

        with self._lock:
            relation = self._relations.get(cle(alias))
            return dict(relation) if relation is not None else None

    def enseigner(
        self,
        alias: str,
        cible: str,
        *,
        provenance: str,
        score: int = 90,
    ) -> None:
        """Ajoute une relation traçable après validation par le créateur."""

        alias_cle = cle(alias)
        cible_cle = cle(cible)
        if not alias_cle or not cible_cle or alias_cle == cible_cle:
            raise ValueError("Une relation exige deux verbes différents.")
        if not provenance.strip():
            raise ValueError("Une relation apprise exige une provenance.")
        if not 0 <= score <= 100:
            raise ValueError("Le score doit être compris entre 0 et 100.")
        with self._lock:
            self._relations[alias_cle] = {
                "target": cible_cle,
                "relation": "equivalent_appris",
                "provenance": provenance,
                "score": score,
                "status": "confirmed",
            }
            self._persist()

    def relations(self) -> dict[str, dict[str, Any]]:
        """Expose une copie pour l'audit et les tests."""

        with self._lock:
            return {
                alias: dict(relation)
                for alias, relation in self._relations.items()
            }

    def _persist(self) -> None:
        """Écrit atomiquement sans risquer un fichier partiel."""

        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"version": 1, "relations": self._relations},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
