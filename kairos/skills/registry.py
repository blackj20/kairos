"""Registre qui n'expose que les versions activées après tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillRegistry:
    """Registre atomique des artefacts actifs et de leur historique."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 2, "skills": {}})
        else:
            data = self._read_raw()
            if data.get("version") != 2:
                self._write(self._migrer(data))

    def _read_raw(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ValueError(f"Registre de skills illisible : {erreur}") from erreur
        if not isinstance(data, dict) or not isinstance(data.get("skills"), dict):
            raise ValueError("Format du registre de skills invalide.")
        return data

    def _read(self) -> dict[str, Any]:
        data = self._read_raw()
        if data.get("version") != 2:
            raise ValueError("Version du registre de skills non prise en charge.")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _migrer(data: dict[str, Any]) -> dict[str, Any]:
        """Conserve l'active V0.4 sans inventer les métadonnées historiques."""

        resultat: dict[str, Any] = {"version": 2, "skills": {}}
        for skill_id, item in data.get("skills", {}).items():
            active = item.get("active_version")
            versions: dict[str, Any] = {}
            history: list[str] = []
            if active:
                history.append(active)
                versions[active] = {
                    "path": item.get("path"),
                    "report_id": item.get("report_id"),
                    "digest": item.get("digest"),
                    "approved_by": item.get("approved_by"),
                    "status": "active" if item.get("status") == "active" else "inactive",
                }
            resultat["skills"][skill_id] = {
                "active_version": active if item.get("status") == "active" else None,
                "history": history,
                "versions": versions,
                "status": item.get("status", "archived"),
            }
        return resultat

    def activate(
        self,
        skill_id: str,
        version: str,
        report_id: str,
        path: str,
        *,
        digest: str,
        approved_by: str,
    ) -> str | None:
        """Active une version complète et retourne la version précédente."""

        if not report_id.strip():
            raise ValueError("Une activation exige un rapport de tests.")
        if len(digest) != 64 or any(car not in "0123456789abcdef" for car in digest):
            raise ValueError("Une activation exige une empreinte SHA-256 valide.")
        if not approved_by.strip():
            raise ValueError("Une activation exige un approbateur explicite.")
        if not path.strip():
            raise ValueError("Une activation exige un chemin d'artefact.")

        data = self._read()
        skill = data["skills"].setdefault(
            skill_id,
            {
                "active_version": None,
                "history": [],
                "versions": {},
                "status": "archived",
            },
        )
        previous = skill.get("active_version")
        existing = skill["versions"].get(version)
        metadata = {
            "path": path,
            "report_id": report_id,
            "digest": digest,
            "approved_by": approved_by.strip(),
            "status": "active",
        }
        if existing is not None:
            comparable = {**existing, "status": "active"}
            if comparable != metadata:
                raise ValueError("Cette version existe déjà avec un autre artefact.")

        for item in skill["versions"].values():
            if item.get("status") == "active":
                item["status"] = "inactive"
        skill["versions"][version] = metadata
        if version not in skill["history"]:
            skill["history"].append(version)
        skill["active_version"] = version
        skill["status"] = "active"
        self._synchroniser_vue_active(skill)
        self._write(data)
        return previous

    def active(self, skill_id: str) -> dict[str, Any] | None:
        skill = self._read()["skills"].get(skill_id)
        if not skill or skill.get("status") != "active":
            return None
        version = skill.get("active_version")
        metadata = skill.get("versions", {}).get(version)
        if not version or not metadata:
            raise ValueError(f"Registre incohérent pour {skill_id}.")
        return {"id": skill_id, "version": version, **metadata}

    def candidates(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Retourne uniquement les skills actives correspondant au domaine."""

        domain = request.get("domain")
        resultats: list[dict[str, Any]] = []
        for skill_id in self._read()["skills"]:
            active = self.active(skill_id)
            if active is not None and (not domain or domain in skill_id):
                resultats.append(active)
        return resultats

    def rollback(self, skill_id: str) -> dict[str, Any] | None:
        """Restaure toutes les métadonnées de la version précédente."""

        data = self._read()
        skill = data["skills"].get(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        current = skill.get("active_version")
        history = list(skill.get("history", []))
        if current not in history:
            raise ValueError(f"Historique incohérent pour {skill_id}.")

        index = history.index(current)
        previous = next(
            (
                version
                for version in reversed(history[:index])
                if version in skill.get("versions", {})
            ),
            None,
        )
        if current in skill["versions"]:
            skill["versions"][current]["status"] = "inactive"
        if previous is None:
            skill["active_version"] = None
            skill["status"] = "archived"
            self._synchroniser_vue_active(skill)
            self._write(data)
            return None

        skill["active_version"] = previous
        skill["versions"][previous]["status"] = "active"
        skill["status"] = "active"
        self._synchroniser_vue_active(skill)
        self._write(data)
        return {"id": skill_id, "version": previous, **skill["versions"][previous]}

    @staticmethod
    def _synchroniser_vue_active(skill: dict[str, Any]) -> None:
        version = skill.get("active_version")
        metadata = skill.get("versions", {}).get(version) if version else None
        for cle in ("path", "report_id", "digest", "approved_by"):
            skill[cle] = metadata.get(cle) if metadata else None
