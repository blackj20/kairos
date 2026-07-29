"""Filtres cognitifs opérationnels entre compréhension et décision."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .generalisation_intention import GeneralisateurIntention
from .modeles import Analyse


@dataclass(frozen=True, slots=True)
class ProfilCognitif:
    """Lecture explicable d'une intention, sans simuler une émotion."""

    intention: str
    intention_score: int
    structure_intention: str
    direction: str
    besoins: tuple[str, ...]
    envies: tuple[str, ...]
    manques: tuple[str, ...]
    risque: str
    risque_score: int
    prudence: str
    choix_recommande: str
    filtres: tuple[str, ...]
    raisons: tuple[str, ...]

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


class FiltresCognitifs:
    """Applique des concepts mesurables avant le moteur de décision."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = racine or Path(__file__).resolve().parent.parent
        self.concepts = self._lire("data/cognition/concepts.json")
        self.regles = self._lire("data/cognition/filters.json")
        self.generalisateur = GeneralisateurIntention(self.racine)
        self._valider()
        self._mots_formes = {
            mot
            for groupes in self.regles["intent_patterns"].values()
            for forme in groupes
            for mot in self._normaliser(str(forme)).split()
        }
        self._mots_formes.update(self.generalisateur.mots_fonctionnels)

    def evaluer(self, analyse: Analyse) -> ProfilCognitif:
        texte = self._normaliser(analyse.texte_normalise)
        action = str(analyse.action.valeur or "")
        type_requete = str(analyse.type_requete.valeur or "inconnu")
        lecture_intention = self.generalisateur.analyser(
            texte,
            action=action,
            type_requete=type_requete,
        )
        indirecte = bool(
            lecture_intention.indirecte
            and action not in self.regles["non_directive_desires"]
        )
        commande = type_requete == "ordre" or indirecte

        intention, intention_score = self._intention(
            texte,
            type_requete,
            indirecte,
            lecture_intention.nature,
            lecture_intention.score,
        )
        famille_risque, score_risque = self._risque_action(action)
        dommage = commande and any(
            forme in texte for forme in self.regles["harm_patterns"]
        )
        portee_large = commande and any(
            self._mot_present(texte, forme)
            for forme in self.regles["broad_scope_patterns"]
        )
        if dommage:
            famille_risque, score_risque = "harmful", 100
        elif portee_large and famille_risque in {"irreversible", "physical"}:
            score_risque = max(score_risque, 90)

        direction = self._direction(action, dommage, type_requete)
        besoins: list[str] = []
        envies: list[str] = []
        manques: list[str] = []
        filtres: list[str] = ["truth", "authorization", "objective_alignment"]
        raisons: list[str] = [f"intention détectée : {intention}"]
        raisons.extend(lecture_intention.signaux)

        inconnus_reels = tuple(
            mot
            for mot in analyse.jetons_inconnus
            if not self._est_forme_fonctionnelle(mot)
        )
        if inconnus_reels:
            besoins.append("information")
            manques.extend(f"sens:{mot}" for mot in inconnus_reels)
            raisons.append(
                "sens encore absent : " + ", ".join(inconnus_reels)
            )
        if action and analyse.cible.valeur is None:
            besoins.append("cible")
            manques.append("cible")
        if commande:
            besoins.append("autorisation")
        if score_risque >= self.regles["thresholds"]["confirm_min"]:
            besoins.extend(("confirmation", "reversibilite"))
            filtres.extend(("human_safety", "system_integrity", "reversibility"))
            raisons.append(
                f"prudence élevée par risque {famille_risque} ({score_risque} %)"
            )
        if self._contient_forme(texte, "need"):
            besoins.append("besoin_exprime")
            raisons.append("un besoin est explicitement formulé")
        if self._contient_forme(texte, "desire"):
            envies.append("preference_utilisateur")
            raisons.append(
                "une envie influence le choix mais ne donne aucune autorisation"
            )
        if self._contient_forme(texte, "missing"):
            manques.append("manque_exprime")

        if dommage:
            choix = "refuser"
            filtres.append("harm_prevention")
            raisons.append("dommage ou contournement explicite détecté")
        elif commande and score_risque >= self.regles["thresholds"]["confirm_min"]:
            choix = "confirmer"
        elif commande:
            choix = "executer_si_route_autorisee"
        elif type_requete in {"question", "lecon"}:
            choix = "repondre"
        elif inconnus_reels:
            choix = "clarifier"
        else:
            choix = "observer"

        prudence = self._niveau_prudence(score_risque)
        score_choix = 100 - round(score_risque * 0.35)
        score_choix -= (
            len(inconnus_reels)
            * int(self.regles["thresholds"]["unknown_penalty"])
        )
        if direction == "aligned":
            score_choix += int(
                self.regles["thresholds"]["alignment_bonus"]
            )
        intention_score = max(0, min(100, intention_score))
        raisons.append(
            f"direction {direction}; choix {choix}; confiance "
            f"{max(0, min(100, score_choix))} %"
        )

        return ProfilCognitif(
            intention=intention,
            intention_score=intention_score,
            structure_intention=lecture_intention.nature,
            direction=direction,
            besoins=self._uniques(besoins),
            envies=self._uniques(envies),
            manques=self._uniques(manques),
            risque=famille_risque,
            risque_score=score_risque,
            prudence=prudence,
            choix_recommande=choix,
            filtres=self._uniques(filtres),
            raisons=tuple(raisons),
        )

    def _intention(
        self,
        texte: str,
        type_requete: str,
        indirecte: bool,
        structure: str,
        score_structure: int,
    ) -> tuple[str, int]:
        if type_requete == "interdiction":
            return "protection", 95
        if indirecte:
            return "demande_indirecte", score_structure
        if structure in {"question_capacite", "question_information"}:
            return "obtenir_information", score_structure
        if type_requete == "ordre":
            return "ordre_direct", 92
        if self._contient_forme(texte, "need"):
            return "besoin_exprime", 88
        if self._contient_forme(texte, "desire"):
            return "envie_exprimee", 82
        if type_requete == "question":
            return "obtenir_information", 90
        if type_requete == "lecon":
            return "apprendre", 90
        if type_requete == "affirmation":
            return "informer", 75
        return "incertaine", 40

    def _risque_action(self, action: str) -> tuple[str, int]:
        if not action:
            return "none", 0
        for famille, actions in self.regles["risk_by_action"].items():
            if action in actions:
                return famille, int(self.regles["risk_scores"][famille])
        return "unknown", int(self.regles["risk_scores"]["unknown"])

    def _direction(
        self, action: str, dommage: bool, type_requete: str
    ) -> str:
        if dommage:
            return "conflict"
        if action in self.regles["objective_actions"]:
            return "aligned"
        if type_requete in {"question", "lecon"}:
            return "aligned"
        return "neutral"

    def _contient_forme(self, texte: str, groupe: str) -> bool:
        return any(
            self._normaliser(str(forme)) in texte
            for forme in self.regles["intent_patterns"][groupe]
        )

    def _est_forme_fonctionnelle(self, mot: str) -> bool:
        """Accepte aussi les clitiques : `sais-tu` devient `sais tu`."""

        parties = self._normaliser(mot).split()
        return bool(parties) and all(
            partie in self._mots_formes for partie in parties
        )

    @staticmethod
    def _mot_present(texte: str, mot: str) -> bool:
        return bool(re.search(rf"\b{re.escape(mot)}\b", texte))

    @staticmethod
    def _niveau_prudence(score: int) -> str:
        if score >= 90:
            return "maximum"
        if score >= 60:
            return "high"
        if score >= 30:
            return "moderate"
        return "low"

    @staticmethod
    def _uniques(valeurs: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(valeurs))

    def _valider(self) -> None:
        concepts = self.concepts.get("concepts", {})
        requis = {
            "intention",
            "besoin",
            "envie",
            "manque",
            "prudence",
            "direction",
            "bien_operationnel",
            "mal_operationnel",
            "choix",
        }
        absents = requis - set(concepts)
        if absents:
            raise ValueError(
                "Concepts cognitifs absents : " + ", ".join(sorted(absents))
            )
        if not self.regles.get("priorities"):
            raise ValueError("Les priorités cognitives sont obligatoires.")

    def _lire(self, relatif: str) -> dict[str, Any]:
        chemin = self.racine / relatif
        try:
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise RuntimeError(
                f"Configuration cognitive invalide : {chemin}"
            ) from erreur
        if not isinstance(donnees, dict):
            raise RuntimeError(f"{chemin} doit contenir un objet JSON.")
        return donnees

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
