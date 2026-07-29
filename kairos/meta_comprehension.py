"""Explication de soi et des analyses depuis l'état réel du système."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .modeles import Analyse, Decision
from .soi import ConnaissanceDeSoi


@dataclass(frozen=True, slots=True)
class ReponseMeta:
    route: str
    texte: str


class ModeleDeSoi:
    """Construit le self runtime depuis les registres, pas depuis des promesses."""

    def __init__(self, soi: ConnaissanceDeSoi) -> None:
        self.soi = soi
        self.racine = soi.racine

    @property
    def version_runtime(self) -> str:
        try:
            return version("kairos-artificial-brain")
        except PackageNotFoundError:
            pyproject = (self.racine / "pyproject.toml").read_text(encoding="utf-8")
            trouve = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
            return trouve.group(1) if trouve else "inconnue"

    def registre(self) -> dict[str, object]:
        actions = self._json("data/routing/actions.json").get("actions", {})
        routes = self._json("data/routing/routes.json").get("routes", {})
        capacites = self._json("data/routing/capabilities.json").get(
            "capabilities", {}
        )
        return {
            "actions": tuple(sorted(actions)),
            "routes": tuple(sorted(routes)),
            "capabilities": tuple(sorted(capacites)),
        }

    def expliquer(self) -> str:
        registre = self.registre()
        identite = self.soi.identity
        objectif = self.soi.objective
        limites = self.soi.limits["known"]
        return (
            f"Je suis {identite['name']}, un {identite['nature']}. "
            f"Ma version runtime est {self.version_runtime}. "
            f"Mon objectif prioritaire est de {objectif['current']}. "
            f"Je vérifie actuellement {len(registre['actions'])} actions, "
            f"{len(registre['routes'])} routes et "
            f"{len(registre['capabilities'])} capacités déclaratives. "
            "Je ne confonds pas ces capacités avec des actions réellement "
            "exécutables : une route bloquée ou candidate reste inexécutable. "
            f"Ma première limite est : {limites[0]}."
        )

    def capacites(self) -> str:
        registre = self.registre()
        return (
            "Mes capacités réellement cataloguées sont : "
            + ", ".join(registre["capabilities"])
            + ". Une capacité absente de ce registre n'est pas disponible."
        )

    def _json(self, relatif: str) -> dict[str, object]:
        return json.loads((self.racine / relatif).read_text(encoding="utf-8"))


class MetaComprehension:
    """Répond aux demandes sur soi, la compréhension et la dernière décision."""

    def __init__(self, soi: ConnaissanceDeSoi) -> None:
        self.modele = ModeleDeSoi(soi)

    def repondre(
        self,
        analyse: Analyse,
        precedente: Decision | None,
    ) -> ReponseMeta | None:
        texte = self._normaliser(analyse.texte_normalise)

        if self._explique_soi(texte, analyse):
            return ReponseMeta("self.explain", self.modele.expliquer())

        if any(x in texte for x in ("que peux tu faire", "tes capacites reelles")):
            return ReponseMeta("self.capabilities", self.modele.capacites())

        if any(
            x in texte
            for x in (
                "qu as tu mal compris",
                "qu est ce que tu as mal compris",
                "que n as tu pas compris",
            )
        ):
            if precedente is None:
                return ReponseMeta(
                    "understanding.explain",
                    "Je n'ai pas encore d'analyse précédente à examiner.",
                )
            inconnus = precedente.analyse.jetons_inconnus
            if inconnus:
                return ReponseMeta(
                    "understanding.explain",
                    "Dans la requête précédente, les éléments non compris étaient : "
                    + ", ".join(f"« {mot} »" for mot in inconnus)
                    + ".",
                )
            return ReponseMeta(
                "understanding.explain",
                "La requête précédente ne contenait aucun jeton totalement "
                "inconnu. Mes incertitudes restent visibles dans ses scores.",
            )

        if any(x in texte for x in ("qu as tu compris", "explique ta comprehension")):
            if precedente is None:
                return ReponseMeta(
                    "understanding.explain",
                    "Je n'ai pas encore de requête précédente à expliquer.",
                )
            return ReponseMeta(
                "understanding.explain",
                self._expliquer_analyse(precedente.analyse),
            )

        if texte == "pourquoi" or "pourquoi as tu" in texte:
            if precedente is None:
                return ReponseMeta(
                    "decision.explain",
                    "Je n'ai pas encore de décision précédente à justifier.",
                )
            raisons = "; ".join(precedente.analyse.verification.raisons)
            return ReponseMeta(
                "decision.explain",
                f"J'ai choisi la route « {precedente.route} » avec une "
                f"vérification à {precedente.analyse.verification.score} %. "
                f"Raisons : {raisons or 'aucune raison détaillée'}.",
            )
        return None

    @staticmethod
    def _explique_soi(texte: str, analyse: Analyse) -> bool:
        cible_self = analyse.cible.valeur == "self:kairos" or any(
            relation.target == "self:kairos"
            for relation in analyse.relations
            if relation.relation in {"reference", "expliquer"}
        )
        return (
            texte
            in {
                "explique toi",
                "explique-toi",
                "presente toi",
                "presente-toi",
                "qui es tu",
                "qui es-tu",
            }
            or (analyse.action.valeur == "expliquer" and cible_self)
        )

    @staticmethod
    def _expliquer_analyse(analyse: Analyse) -> str:
        relations = ", ".join(
            f"{r.source} —{r.relation}→ {r.target}"
            for r in analyse.relations
        ) or "aucune relation stable"
        return (
            f"J'ai estimé le type « {analyse.type_requete.valeur} » "
            f"à {analyse.type_requete.score} %, l'action "
            f"« {analyse.action.valeur or 'aucune'} » à {analyse.action.score} % "
            f"et la cible « {analyse.cible.valeur or 'aucune'} » à "
            f"{analyse.cible.score} %. Relations : {relations}."
        )

    @staticmethod
    def _normaliser(texte: str) -> str:
        decompose = unicodedata.normalize("NFKD", texte)
        sans_accents = "".join(
            c for c in decompose if not unicodedata.combining(c)
        )
        sans_separateurs = re.sub(r"[-'’]", " ", sans_accents.casefold())
        nettoye = re.sub(r"[^\w\s]", " ", sans_separateurs)
        return re.sub(r"\s+", " ", nettoye).strip()
