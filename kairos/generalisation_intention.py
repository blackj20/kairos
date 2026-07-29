"""Généralisation composable des intentions françaises.

Ce composant ne choisit aucune route et n'exécute rien. Il distingue une
commande formulée poliment d'une question portant seulement sur une capacité.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class LectureIntention:
    """Résultat explicable produit avant les filtres cognitifs."""

    indirecte: bool
    nature: str
    score: int
    signaux: tuple[str, ...]


class GeneralisateurIntention:
    """Combine des indices déclaratifs au lieu de mémoriser chaque phrase."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = racine or Path(__file__).resolve().parent.parent
        self.regles = self._lire("data/cognition/intent_rules.json")
        self._valider()
        groupes = (
            "request_openers",
            "modal_tokens",
            "second_person_tokens",
            "politeness_markers",
            "capability_questions",
            "information_openers",
            "non_directive_self_patterns",
            "negation_tokens",
        )
        self.mots_fonctionnels = {
            mot
            for groupe in groupes
            for forme in self.regles[groupe]
            for mot in self._normaliser(str(forme)).split()
        }

    def analyser(
        self,
        texte: str,
        *,
        action: str,
        type_requete: str,
    ) -> LectureIntention:
        normalise = self._normaliser(texte)
        if not action or type_requete == "interdiction":
            return LectureIntention(False, "aucune_demande_indirecte", 100, ())

        autonomie = self._premiere_forme(
            normalise, "non_directive_self_patterns"
        )
        if autonomie is not None:
            return LectureIntention(
                False,
                "preference_personnelle",
                94,
                (f"préférence du locuteur : {autonomie}",),
            )

        capacite = self._premiere_forme(normalise, "capability_questions")
        if capacite is not None:
            return LectureIntention(
                False,
                "question_capacite",
                int(self.regles["scores"]["capability_question"]),
                (f"question sur une capacité : {capacite}",),
            )

        information = self._forme_initiale(normalise, "information_openers")
        if information is not None:
            return LectureIntention(
                False,
                "question_information",
                int(self.regles["scores"]["information_question"]),
                (f"question informative : {information}",),
            )

        ouverture = self._premiere_forme(normalise, "request_openers")
        if ouverture is not None:
            return LectureIntention(
                True,
                "demande_indirecte",
                int(self.regles["scores"]["explicit_request"]),
                (f"ouverture directive : {ouverture}",),
            )

        mots = set(normalise.split())
        modaux = mots & set(self.regles["modal_tokens"])
        personnes = mots & set(self.regles["second_person_tokens"])
        if modaux and personnes:
            return LectureIntention(
                True,
                "demande_indirecte",
                int(self.regles["scores"]["composed_request"]),
                (
                    "modalité directive : " + ", ".join(sorted(modaux)),
                    "destinataire : " + ", ".join(sorted(personnes)),
                ),
            )

        if type_requete == "ordre":
            return LectureIntention(
                False,
                "ordre_direct",
                92,
                ("forme impérative déjà détectée",),
            )
        return LectureIntention(
            False,
            "aucune_demande_indirecte",
            int(self.regles["scores"]["uncertain"]),
            (),
        )

    def _premiere_forme(self, texte: str, groupe: str) -> str | None:
        for forme in self.regles[groupe]:
            candidate = self._normaliser(str(forme))
            if self._contient_expression(texte, candidate):
                return candidate
        return None

    def _forme_initiale(self, texte: str, groupe: str) -> str | None:
        for forme in self.regles[groupe]:
            candidate = self._normaliser(str(forme))
            if texte == candidate or texte.startswith(candidate + " "):
                return candidate
        return None

    @staticmethod
    def _contient_expression(texte: str, expression: str) -> bool:
        return bool(
            re.search(
                rf"(?<!\w){re.escape(expression)}(?!\w)",
                texte,
            )
        )

    def _valider(self) -> None:
        requis = {
            "request_openers",
            "modal_tokens",
            "second_person_tokens",
            "politeness_markers",
            "capability_questions",
            "information_openers",
            "non_directive_self_patterns",
            "negation_tokens",
            "scores",
        }
        absents = requis - set(self.regles)
        if absents:
            raise ValueError(
                "Règles d'intention absentes : " + ", ".join(sorted(absents))
            )
        for groupe in requis - {"scores"}:
            if not isinstance(self.regles[groupe], list):
                raise ValueError(f"La règle {groupe} doit être une liste.")

    def _lire(self, relatif: str) -> dict[str, Any]:
        chemin = self.racine / relatif
        try:
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise RuntimeError(
                f"Configuration d'intention invalide : {chemin}"
            ) from erreur
        if not isinstance(contenu, dict):
            raise RuntimeError(f"{chemin} doit contenir un objet JSON.")
        return contenu

    @staticmethod
    def _normaliser(texte: str) -> str:
        decompose = unicodedata.normalize("NFKD", texte)
        sans_accents = "".join(
            caractere
            for caractere in decompose
            if not unicodedata.combining(caractere)
        )
        nettoye = re.sub(r"[^\w\s]", " ", sans_accents.casefold())
        return re.sub(r"\s+", " ", nettoye).strip()
