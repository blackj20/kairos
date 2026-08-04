"""Adaptateur minimal vers l'API locale d'Ollama."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

from .modeles import LectureLangage
from .protocole import ErreurMoteurLangage, MoteurLangageIndisponible


class OllamaLanguageEngine:
    """Compréhension structurée et formulation via un processus Ollama local."""

    nom = "ollama"
    LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

    ANALYSIS_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {
            "request_type": {
                "type": ["string", "null"],
                "enum": [
                    "action_request",
                    "prohibition",
                    "information_question",
                    "capability_question",
                    "statement",
                    "lesson",
                    None,
                ],
            },
            "approach": {"type": ["string", "null"]},
            "action": {"type": ["string", "null"]},
            "target": {"type": ["string", "null"]},
            "negation": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "missing_information": {
                "type": "array",
                "items": {"type": "string"},
            },
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "relation": {"type": "string"},
                        "target": {"type": "string"},
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                    },
                    "required": ["source", "relation", "target", "confidence"],
                },
            },
        },
        "required": [
            "request_type",
            "approach",
            "action",
            "target",
            "negation",
            "confidence",
            "missing_information",
            "relations",
        ],
    }

    def __init__(
        self,
        modele: str,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 45.0,
        keep_alive: str = "5m",
        allow_remote: bool = False,
    ) -> None:
        if not modele.strip():
            raise ValueError("Un modèle Ollama local est obligatoire.")
        if timeout <= 0:
            raise ValueError("Le timeout doit être positif.")
        self.modele = modele.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.keep_alive = keep_alive
        self._valider_url(allow_remote=allow_remote)

    def analyser(
        self,
        texte: str,
        contexte: Sequence[Mapping[str, Any]] = (),
    ) -> LectureLangage:
        if not texte.strip():
            raise ValueError("Le texte à analyser ne peut pas être vide.")
        prompt = (
            "Analyse la requête française suivante. Retourne uniquement le JSON "
            "respectant le schéma. Ne décide aucune permission et n'exécute rien.\n\n"
            f"Contexte validé : {json.dumps(list(contexte), ensure_ascii=False)}\n"
            f"Requête : {texte}"
        )
        payload = self._post(
            "/api/generate",
            {
                "model": self.modele,
                "system": (
                    "Tu es un analyseur linguistique. Tu extrais l'intention, "
                    "l'action et la cible. Les relations produites sont seulement "
                    "des candidates, jamais des vérités."
                ),
                "prompt": prompt,
                "stream": False,
                "format": self.ANALYSIS_SCHEMA,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0},
            },
        )
        raw = str(payload.get("response") or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ErreurMoteurLangage(
                "Ollama n'a pas retourné une analyse JSON valide."
            ) from error
        if not isinstance(data, dict):
            raise ErreurMoteurLangage("L'analyse Ollama doit être un objet JSON.")
        return LectureLangage.depuis_dict(data, modele=self.modele)

    def formuler(
        self,
        *,
        requete: str,
        analyse: Mapping[str, Any],
        decision: Mapping[str, Any],
        contexte: Sequence[Mapping[str, Any]] = (),
    ) -> str:
        prompt = (
            "Rédige une réponse française naturelle et directe. Respecte la "
            "décision de Kairos. N'affirme jamais qu'une action a été exécutée si "
            "la décision ne le dit pas. Les connaissances internes du modèle ne "
            "doivent pas être présentées comme une nouvelle mémoire validée.\n\n"
            f"Requête : {requete}\n"
            f"Analyse : {json.dumps(dict(analyse), ensure_ascii=False)}\n"
            f"Décision : {json.dumps(dict(decision), ensure_ascii=False)}\n"
            f"Contexte validé : {json.dumps(list(contexte), ensure_ascii=False)}"
        )
        payload = self._post(
            "/api/generate",
            {
                "model": self.modele,
                "system": (
                    "Tu es l'organe de formulation de K.A.I.R.O.S. "
                    "Tu rédiges, mais tu ne modifies aucune mémoire, permission "
                    "ou décision."
                ),
                "prompt": prompt,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0.25, "num_predict": 512},
            },
        )
        response = str(payload.get("response") or "").strip()
        if not response:
            raise ErreurMoteurLangage("Ollama a retourné une réponse vide.")
        return response

    def statut(self) -> dict[str, Any]:
        try:
            payload = self._get("/api/version")
        except MoteurLangageIndisponible as error:
            return {
                "provider": self.nom,
                "model": self.modele,
                "available": False,
                "local": True,
                "error": str(error),
            }
        return {
            "provider": self.nom,
            "model": self.modele,
            "available": True,
            "local": True,
            "version": payload.get("version"),
        }

    def _post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._request(request)

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(self.base_url + path, method="GET")
        return self._request(request)

    def _request(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise MoteurLangageIndisponible(
                f"Ollama local indisponible sur {self.base_url}."
            ) from error
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as error:
            raise ErreurMoteurLangage("Réponse HTTP Ollama invalide.") from error
        if not isinstance(payload, dict):
            raise ErreurMoteurLangage("La réponse Ollama doit être un objet JSON.")
        if payload.get("error"):
            raise ErreurMoteurLangage(str(payload["error"]))
        return payload

    def _valider_url(self, *, allow_remote: bool) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("L'URL Ollama est invalide.")
        if not allow_remote and parsed.hostname.casefold() not in self.LOCAL_HOSTS:
            raise ValueError(
                "Le moteur linguistique est local par défaut ; "
                "une adresse distante est refusée."
            )
