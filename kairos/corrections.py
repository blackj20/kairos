"""Mémoire des relations orthographiques confirmées par l'utilisateur."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .normalisation import cle


class MemoireCorrections:
    """Conserve séparément candidats et corrections confirmées.

    Une proposition floue n'est jamais enregistrée comme correction. Seule la
    couche Expérience peut appeler :meth:`confirmer` après une réponse positive.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """Utilise la mémoire vive par défaut et un JSON atomique sur demande."""

        self.path = Path(path) if path is not None else None
        self._relations: dict[str, str] = {}
        self._lock = threading.RLock()
        if self.path is not None and self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._relations = {
                cle(source): cle(target)
                for source, target in data.get("relations", {}).items()
            }

    def obtenir(self, forme: str) -> str | None:
        """Retourne uniquement une relation déjà confirmée."""

        with self._lock:
            return self._relations.get(cle(forme))

    def confirmer(self, forme: str, forme_correcte: str) -> None:
        """Enregistre une relation et la persiste atomiquement si configuré."""

        source = cle(forme)
        target = cle(forme_correcte)
        if not source or not target or source == target:
            raise ValueError("Une correction doit relier deux formes différentes.")
        with self._lock:
            self._relations[source] = target
            if self.path is not None:
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

    def relations(self) -> dict[str, str]:
        """Expose une copie afin d'empêcher les modifications indirectes."""

        with self._lock:
            return dict(self._relations)
