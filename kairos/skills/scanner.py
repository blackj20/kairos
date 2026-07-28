"""Filtre AST conservateur appliqué avant toute exécution."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScanReport:
    """Liste les violations détectées sans modifier le candidat."""

    passed: bool
    violations: tuple[str, ...]


class SkillScanner:
    """Détecte les primitives interdites et le code au chargement."""

    FORBIDDEN_IMPORTS = {"os", "subprocess", "socket", "ctypes"}
    FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open"}
    FORBIDDEN_ATTRIBUTES = {"system", "popen", "spawn", "remove", "unlink"}

    def scan(self, path: str | Path) -> ScanReport:
        """Analyse le fichier ; une erreur syntaxique place aussi en quarantaine."""

        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as error:
            return ScanReport(False, (f"source invalide : {error}",))
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in self.FORBIDDEN_IMPORTS:
                        violations.append(f"import interdit : {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in self.FORBIDDEN_IMPORTS:
                    violations.append(f"import interdit : {node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
                    violations.append(f"appel interdit : {node.func.id}")
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.FORBIDDEN_ATTRIBUTES
                ):
                    violations.append(f"attribut interdit : {node.func.attr}")
        # Au niveau module, seules les déclarations et constantes sont acceptées.
        for node in tree.body:
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                       ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                       ast.Expr)
            ):
                violations.append(f"instruction globale interdite : {type(node).__name__}")
            if isinstance(node, ast.Expr) and not (
                isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                violations.append("code exécuté au chargement")
        return ScanReport(not violations, tuple(dict.fromkeys(violations)))
