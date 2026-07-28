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
    files_scanned: tuple[str, ...] = ()


class SkillScanner:
    """Détecte les primitives interdites et le code au chargement."""

    FORBIDDEN_IMPORTS = {
        "asyncio",
        "ctypes",
        "ftplib",
        "glob",
        "http",
        "importlib",
        "marshal",
        "mmap",
        "multiprocessing",
        "os",
        "pathlib",
        "pickle",
        "resource",
        "runpy",
        "shelve",
        "shutil",
        "signal",
        "smtplib",
        "socket",
        "sqlite3",
        "ssl",
        "subprocess",
        "tempfile",
        "threading",
        "urllib",
        "webbrowser",
    }
    ALLOWED_IMPORTS = {
        "collections",
        "dataclasses",
        "decimal",
        "fractions",
        "functools",
        "itertools",
        "json",
        "math",
        "operator",
        "re",
        "statistics",
        "string",
        "typing",
        "unittest",
    }
    FORBIDDEN_CALLS = {
        "__import__",
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "getattr",
        "globals",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
    FORBIDDEN_ATTRIBUTES = {
        "chmod",
        "chown",
        "connect",
        "fork",
        "kill",
        "open",
        "popen",
        "read_bytes",
        "read_text",
        "remove",
        "rename",
        "replace",
        "request",
        "rmdir",
        "spawn",
        "start",
        "system",
        "unlink",
        "urlopen",
        "write_bytes",
        "write_text",
    }
    ALLOWED_SUFFIXES = {".py", ".json", ".md"}
    MAX_FILES = 64
    MAX_TOTAL_BYTES = 512 * 1024

    def scan(self, path: str | Path) -> ScanReport:
        """Analyse un fichier Python isolé pour compatibilité avec la V0.4."""

        source = Path(path)
        violations = self._scan_source(source, allowed_local_modules={source.stem})
        return ScanReport(
            passed=not violations,
            violations=tuple(dict.fromkeys(violations)),
            files_scanned=(source.name,),
        )

    def scan_tree(self, candidate_path: str | Path) -> ScanReport:
        """Analyse tous les fichiers d'une candidate, tests compris."""

        root = Path(candidate_path).resolve()
        if not root.is_dir():
            return ScanReport(False, (f"dossier candidat absent : {root}",), ())

        violations: list[str] = []
        fichiers = sorted(root.rglob("*"))
        if len([path for path in fichiers if path.is_file()]) > self.MAX_FILES:
            violations.append(f"trop de fichiers : maximum {self.MAX_FILES}")

        total = 0
        python_files: list[Path] = []
        for path in fichiers:
            relatif = path.relative_to(root).as_posix()
            if path.is_symlink():
                violations.append(f"lien symbolique interdit : {relatif}")
                continue
            if path.is_dir():
                continue
            if path.suffix not in self.ALLOWED_SUFFIXES:
                violations.append(f"type de fichier interdit : {relatif}")
            try:
                taille = path.stat().st_size
            except OSError as erreur:
                violations.append(f"fichier illisible : {relatif} ({erreur})")
                continue
            total += taille
            if path.suffix == ".py":
                python_files.append(path)

        if total > self.MAX_TOTAL_BYTES:
            violations.append(
                f"candidate trop volumineuse : maximum {self.MAX_TOTAL_BYTES} octets"
            )

        local_modules = {path.stem for path in python_files}
        for path in python_files:
            violations.extend(self._scan_source(path, local_modules))

        fichiers_scannes = tuple(
            path.relative_to(root).as_posix() for path in python_files
        )
        return ScanReport(
            passed=not violations,
            violations=tuple(dict.fromkeys(violations)),
            files_scanned=fichiers_scannes,
        )

    def _scan_source(
        self,
        path: Path,
        allowed_local_modules: set[str],
    ) -> list[str]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            return [f"source invalide {path.name} : {error}"]

        violations: list[str] = []
        allowed_imports = self.ALLOWED_IMPORTS | allowed_local_modules
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._verifier_import(alias.name, allowed_imports, violations)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    self._verifier_import(
                        node.module or "",
                        allowed_imports,
                        violations,
                    )
            elif isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id in self.FORBIDDEN_CALLS
                ):
                    violations.append(f"appel interdit : {node.func.id}")
                if isinstance(node.func, ast.Attribute):
                    attribut = node.func.attr
                    if attribut in self.FORBIDDEN_ATTRIBUTES:
                        violations.append(f"attribut interdit : {attribut}")
                    if attribut.startswith("__"):
                        violations.append(f"attribut dunder interdit : {attribut}")
            elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                violations.append(f"attribut dunder interdit : {node.attr}")
            elif isinstance(node, ast.Name) and node.id in {
                "__builtins__",
                "__loader__",
                "__spec__",
            }:
                violations.append(f"nom interne interdit : {node.id}")

        # Au niveau module, seules les déclarations, imports et constantes sont acceptés.
        for node in tree.body:
            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                    ast.Import,
                    ast.ImportFrom,
                    ast.Assign,
                    ast.AnnAssign,
                    ast.Expr,
                ),
            ):
                violations.append(
                    f"instruction globale interdite : {type(node).__name__}"
                )
            if isinstance(node, ast.Expr) and not (
                isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                violations.append("code exécuté au chargement")

        return violations

    def _verifier_import(
        self,
        module: str,
        allowed_imports: set[str],
        violations: list[str],
    ) -> None:
        racine = module.split(".")[0]
        if racine in self.FORBIDDEN_IMPORTS:
            violations.append(f"import interdit : {module}")
        elif racine not in allowed_imports:
            violations.append(f"import non autorisé : {module}")
