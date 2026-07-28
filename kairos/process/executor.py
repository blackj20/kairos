"""Exécuteur de fichiers borné à une racine et doté d'un rollback."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .planner import ProcessPlan


@dataclass(frozen=True, slots=True)
class TransactionResult:
    """Résultat et journal compensatoire d'une transaction."""

    id: str
    outputs: tuple[Any, ...]
    rollback_actions: tuple[tuple[str, str, str | None], ...]


class FileExecutor:
    """Exécute une liste fermée d'opérations sans suivre de chemins externes."""

    def __init__(self, root: str | Path) -> None:
        """Fixe la racine autorisée et une corbeille locale récupérable."""

        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("La racine autorisée doit être un dossier.")
        self.trash = self.root / ".kairos-trash"
        self._transactions: dict[str, TransactionResult] = {}

    def _resolve(self, raw: str, *, existing: bool = False) -> Path:
        """Résout un chemin sans autoriser traversal ou symlink hors racine."""

        # Le contrôle de périmètre précède le contrôle d'existence afin qu'un
        # traversal soit toujours signalé comme une violation de permission.
        candidate = (self.root / raw).resolve(strict=False)
        if candidate != self.root and self.root not in candidate.parents:
            raise PermissionError(f"Chemin hors périmètre : {raw}")
        if existing and not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    def preview(self, plan: ProcessPlan) -> dict[str, Any]:
        """Valide le plan et décrit ses effets sans modifier le disque."""

        plan.validate()
        return {
            "goal": plan.goal,
            "steps": [
                {"tool": step.tool, "risk": step.risk.value,
                 "arguments": dict(step.arguments)}
                for step in plan.steps
            ],
        }

    def execute(self, plan: ProcessPlan) -> TransactionResult:
        """Exécute séquentiellement et annule automatiquement après une erreur."""

        self.preview(plan)
        transaction_id = f"transaction_{uuid.uuid4().hex}"
        outputs: list[Any] = []
        rollbacks: list[tuple[str, str, str | None]] = []
        try:
            for step in plan.steps:
                result, compensation = self._execute_step(step.tool, step.arguments)
                outputs.append(result)
                if compensation:
                    rollbacks.append(compensation)
        except Exception:
            self._apply_rollback(reversed(rollbacks))
            raise
        result = TransactionResult(transaction_id, tuple(outputs), tuple(rollbacks))
        self._transactions[transaction_id] = result
        return result

    def rollback(self, transaction_id: str) -> None:
        """Applique les compensations dans l'ordre inverse une seule fois."""

        transaction = self._transactions.pop(transaction_id)
        self._apply_rollback(reversed(transaction.rollback_actions))

    def _execute_step(
        self, tool: str, arguments: dict[str, Any]
    ) -> tuple[Any, tuple[str, str, str | None] | None]:
        """Implémente chaque outil sous forme d'appel Python spécialisé."""

        path = self._resolve(str(arguments.get("path", ".")),
                             existing=tool not in {"fs.create_directory"})
        if tool == "fs.list":
            return tuple(item.name for item in path.iterdir()), None
        if tool == "fs.stat":
            return {"size": path.stat().st_size, "is_file": path.is_file()}, None
        if tool == "fs.read":
            return path.read_text(encoding="utf-8"), None
        if tool == "fs.search":
            pattern = str(arguments.get("pattern", "*"))
            return tuple(str(item.relative_to(self.root)) for item in path.rglob(pattern)), None
        if tool == "fs.create_directory":
            path.mkdir(parents=False, exist_ok=False)
            return str(path), ("remove_dir", str(path), None)
        # La mise à la corbeille calcule elle-même une destination interne.
        if tool == "fs.delete_to_trash":
            self.trash.mkdir(exist_ok=True)
            trashed = self.trash / f"{uuid.uuid4().hex}-{path.name}"
            shutil.move(path, trashed)
            return str(trashed), ("move", str(trashed), str(path))
        destination = self._resolve(str(arguments["destination"]), existing=False)
        if destination.exists():
            raise FileExistsError(destination)
        if tool == "fs.copy":
            shutil.copy2(path, destination)
            return str(destination), ("remove_file", str(destination), None)
        if tool in {"fs.move", "fs.rename"}:
            shutil.move(path, destination)
            return str(destination), ("move", str(destination), str(path))
        raise ValueError(f"Outil non implémenté : {tool}")

    @staticmethod
    def _apply_rollback(
        actions: Any,
    ) -> None:
        """Restaure les déplacements et retire seulement les éléments créés."""

        for action, source, destination in actions:
            path = Path(source)
            if action == "move" and destination is not None and path.exists():
                shutil.move(path, destination)
            elif action == "remove_file" and path.is_file():
                path.unlink()
            elif action == "remove_dir" and path.is_dir():
                path.rmdir()
