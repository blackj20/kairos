"""Politique de permissions appliquée avant tout test ou activation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .manifest import SkillManifest


@dataclass(frozen=True, slots=True)
class PermissionReport:
    """Résultat explicable du contrôle de permissions."""

    passed: bool
    violations: tuple[str, ...]


class PermissionPolicy:
    """V0.5 n'autorise que des skills pures, sans effet externe.

    Les permissions réseau, processus, shell et système de fichiers seront
    introduites plus tard par outils spécialisés. Une candidate générée ne peut
    donc pas les demander implicitement ni explicitement dans cette version.
    """

    def validate(self, manifest: SkillManifest) -> PermissionReport:
        violations: list[str] = []
        permissions = manifest.permissions
        for permission in ("network", "process", "shell"):
            if permissions[permission]:
                violations.append(f"permission interdite en V0.5 : {permission}")

        for permission in ("filesystem_read", "filesystem_write"):
            chemins = permissions[permission]
            for chemin in chemins:
                if self._chemin_invalide(chemin):
                    violations.append(
                        f"chemin de permission invalide : {permission}={chemin!r}"
                    )
                else:
                    violations.append(
                        f"permission interdite en V0.5 : {permission}={chemin!r}"
                    )

        return PermissionReport(
            passed=not violations,
            violations=tuple(dict.fromkeys(violations)),
        )

    @staticmethod
    def _chemin_invalide(value: str) -> bool:
        if not value or "\x00" in value or "\\" in value:
            return True
        chemin = PurePosixPath(value)
        return chemin.is_absolute() or ".." in chemin.parts
