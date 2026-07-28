"""Empreinte déterministe des artefacts de skill."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ErreurIntegrite(ValueError):
    """Signale un artefact impossible à mesurer de manière sûre."""


def artifact_digest(candidate_path: str | Path) -> str:
    """Calcule une empreinte SHA-256 indépendante du statut de cycle de vie.

    Le statut ``candidate``/``active`` du manifeste est piloté par le registre.
    Il est normalisé dans l'empreinte afin qu'une copie activée puisse être liée
    au même rapport sans modifier le code testé.
    """

    root = Path(candidate_path).resolve()
    if not root.is_dir():
        raise ErreurIntegrite(f"Dossier de skill absent : {root}")

    fichiers = sorted(path for path in root.rglob("*") if path.is_file())
    if not fichiers:
        raise ErreurIntegrite("Une skill vide ne peut pas être mesurée.")

    digest = hashlib.sha256()
    for path in fichiers:
        if path.is_symlink():
            raise ErreurIntegrite(f"Lien symbolique interdit : {path}")
        try:
            relatif = path.relative_to(root).as_posix()
        except ValueError as erreur:
            raise ErreurIntegrite(f"Fichier hors du candidat : {path}") from erreur
        contenu = path.read_bytes()
        if relatif == "skill.json":
            try:
                manifeste = json.loads(contenu.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
                raise ErreurIntegrite("Le manifeste ne peut pas être normalisé.") from erreur
            if not isinstance(manifeste, dict):
                raise ErreurIntegrite("Le manifeste doit être un objet JSON.")
            manifeste["status"] = "candidate"
            contenu = (
                json.dumps(
                    manifeste,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        digest.update(relatif.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(contenu).to_bytes(8, "big"))
        digest.update(contenu)
    return digest.hexdigest()
