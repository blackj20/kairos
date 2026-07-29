"""Chargement centralisé des connaissances linguistiques déclaratives."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .corrections import MemoireCorrections
from .normalisation import cle
from .relations_verbes import MemoireRelationsVerbes


class ErreurConnaissances(RuntimeError):
    """Signale une connaissance absente ou invalide."""


class Connaissances:
    """Lecture seule des connaissances utilisées par Comprendre."""

    FICHIERS_REQUIS = (
        "affirmations.json",
        "articles.json",
        "bruits.json",
        "conditions.json",
        "entites.json",
        "expressions.json",
        "grammaire.json",
        "negations.json",
        "sens.json",
        "verbes.json",
    )

    def __init__(
        self,
        dossier: Path | None = None,
        corrections: MemoireCorrections | None = None,
        relations_verbes: MemoireRelationsVerbes | None = None,
    ) -> None:
        """Charge le lexique statique et injecte la mémoire orthographique."""

        racine = Path(__file__).resolve().parent.parent
        self.dossier = dossier or racine / "data" / "fr"
        self.corrections = corrections or MemoireCorrections()
        self.relations_verbes = relations_verbes or MemoireRelationsVerbes()
        self._donnees = {
            nom.removesuffix(".json"): self._charger_json(nom)
            for nom in self.FICHIERS_REQUIS
        }

    def _charger_json(self, nom: str) -> dict[str, Any]:
        chemin = self.dossier / nom
        if not chemin.is_file():
            raise ErreurConnaissances(f"Connaissance absente : {chemin}")
        try:
            with chemin.open("r", encoding="utf-8") as fichier:
                donnees = json.load(fichier)
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurConnaissances(
                f"Impossible de charger {chemin} : {erreur}"
            ) from erreur
        if not isinstance(donnees, dict):
            raise ErreurConnaissances(f"{chemin} doit contenir un objet JSON.")
        return donnees

    def obtenir(self, nom: str) -> dict[str, Any]:
        return self._donnees[nom]

    @property
    def verbes(self) -> dict[str, Any]:
        return self._donnees["verbes"]

    @property
    def conditions(self) -> dict[str, Any]:
        return self._donnees["conditions"]

    @property
    def expressions(self) -> dict[str, Any]:
        return self._donnees["expressions"]

    @property
    def entites(self) -> dict[str, Any]:
        return self._donnees["entites"]

    @property
    def sens_ambigus(self) -> dict[str, Any]:
        return self._donnees["sens"]

    @property
    def conversations(self) -> dict[str, Any]:
        """Compatibilité avec Repondre, sans dupliquer les données."""

        return {
            "salutations": self.expressions["salutations"],
            "questions_etat": self.expressions["questions_etat"],
            "reponses": self.expressions["reponses"],
        }

    def trouver_verbe(self, mot: str) -> tuple[str, dict[str, Any]] | None:
        """Trouve une forme exacte ou une relation orthographique confirmée."""

        mot_cle = cle(mot)
        relation_apprise = self.relations_verbes.obtenir(mot_cle)
        if relation_apprise is not None:
            cible = str(relation_apprise["target"])
            regle = self.verbes.get(cible)
            if regle is not None:
                return cible, regle
        forme_confirmee = self.corrections.obtenir(mot_cle)
        if forme_confirmee is not None:
            mot_cle = forme_confirmee
        for lemme, regle in self.verbes.items():
            formes = {cle(forme) for forme in regle.get("formes", [])}
            if mot_cle in formes:
                return lemme, regle
        return None

    @property
    def relations_semantiques(self) -> tuple[dict[str, Any], ...]:
        """Expose les arêtes statiques du graphe défini dans sens.json."""

        relations = self.sens_ambigus.get("__relations__", [])
        if not isinstance(relations, list):
            raise ErreurConnaissances(
                "data/fr/sens.json : __relations__ doit être une liste."
            )
        return tuple(dict(relation) for relation in relations)

    def trouver_relation_contextuelle(
        self, mot: str, mots_contexte: tuple[str, ...]
    ) -> tuple[str, dict[str, Any]] | None:
        """Résout une équivalence si ses contraintes de contexte sont satisfaites."""

        source = self.trouver_verbe(mot)
        source_lemme = source[0] if source is not None else cle(mot)
        categories: set[str] = set()
        valeurs: set[str] = set()
        for mot_contexte in mots_contexte:
            entite = self.trouver_entite(mot_contexte)
            if entite:
                valeur, categorie = entite
                valeurs.add(valeur)
                categories.add(categorie)
        for relation in self.relations_semantiques:
            if relation.get("relation") != "action_equivalente":
                continue
            if cle(str(relation.get("source", ""))) != source_lemme:
                continue
            categories_requises = set(relation.get("target_categories", []))
            valeurs_requises = {cle(item) for item in relation.get("target_values", [])}
            mots_requis = {
                cle(item) for item in relation.get("context_words", [])
            }
            if categories_requises and not categories.intersection(categories_requises):
                continue
            if valeurs_requises and not valeurs.intersection(valeurs_requises):
                continue
            if mots_requis and not mots_requis.intersection(mots_contexte):
                continue
            cible = cle(str(relation.get("target", "")))
            regle = self.verbes.get(cible)
            if regle is not None:
                return cible, relation
        return None

    def enseigner_relation_verbe(
        self, alias: str, cible: str, provenance: str
    ) -> None:
        """Valide la cible canonique avant d'enrichir la mémoire évolutive."""

        cible_trouvee = self.trouver_verbe(cible)
        if cible_trouvee is None:
            raise ValueError(f"Verbe canonique inconnu : {cible}")
        self.relations_verbes.enseigner(
            alias,
            cible_trouvee[0],
            provenance=provenance,
        )

    def proposer_correction_verbe(
        self, mot: str
    ) -> tuple[str, dict[str, Any], str, int] | None:
        """Propose une correction unique, sans l'ajouter à la mémoire.

        Le seuil et l'écart avec le second candidat empêchent de deviner quand
        deux verbes sont presque aussi plausibles.
        """

        original = cle(mot)
        salutations = {
            cle(expression)
            for expression in self.expressions.get("salutations", [])
        }
        if (
            len(original) < 4
            or original in salutations
            or self.trouver_verbe(original)
        ):
            return None
        # On conserve une seule meilleure forme par lemme. Sans ce regroupement,
        # « ouvre » et « ouvrir » se concurrenceraient alors qu'ils représentent
        # exactement la même action.
        par_lemme: dict[str, tuple[float, str, dict[str, Any], str]] = {}
        for lemme, regle in self.verbes.items():
            for forme in regle.get("formes", []):
                forme_cle = cle(forme)
                ratio = SequenceMatcher(None, original, forme_cle).ratio()
                if ratio >= 0.74:
                    candidat = (ratio, lemme, regle, forme_cle)
                    precedent = par_lemme.get(lemme)
                    if precedent is None or ratio > precedent[0]:
                        par_lemme[lemme] = candidat
        candidats = list(par_lemme.values())
        if not candidats:
            return None
        candidats.sort(key=lambda item: item[0], reverse=True)
        meilleur = candidats[0]
        second_ratio = candidats[1][0] if len(candidats) > 1 else 0.0
        if meilleur[0] < 0.80 or meilleur[0] - second_ratio < 0.05:
            return None
        # Une proposition reste sous le seuil d'autorisation. Après confirmation,
        # trouver_verbe la traitera comme une forme exacte au prochain passage.
        return meilleur[1], meilleur[2], meilleur[3], 50

    def confirmer_corrections_de(self, texte: str) -> tuple[tuple[str, str], ...]:
        """Confirme les propositions non ambiguës présentes dans un texte."""

        confirmees: list[tuple[str, str]] = []
        for mot in re.findall(r"[a-zA-ZÀ-ÿ0-9_+#.-]+", texte):
            proposition_verbe = self.proposer_correction_verbe(mot)
            proposition_entite = self.proposer_correction_entite(mot)
            if proposition_verbe is not None:
                _, _, forme_correcte, _ = proposition_verbe
            elif proposition_entite is not None:
                forme_correcte, _, _ = proposition_entite
            else:
                continue
            self.corrections.confirmer(mot, forme_correcte)
            confirmees.append((cle(mot), forme_correcte))
        return tuple(confirmees)

    def trouver_entite(self, mot: str) -> tuple[str, str] | None:
        """Trouve une entité exacte ou une graphie déjà confirmée."""

        mot_cle = cle(mot)
        forme_confirmee = self.corrections.obtenir(mot_cle)
        if forme_confirmee is not None:
            mot_cle = forme_confirmee
        for categorie, elements in self.entites.items():
            for element in elements:
                if mot_cle == cle(element):
                    return str(element).casefold(), categorie
        return None

    def proposer_correction_entite(
        self, mot: str
    ) -> tuple[str, str, int] | None:
        """Propose une entité proche seulement si le résultat est unique."""

        original = cle(mot)
        if len(original) < 4 or self.trouver_entite(original):
            return None
        candidats: list[tuple[float, str, str]] = []
        for categorie, elements in self.entites.items():
            for element in elements:
                element_cle = cle(element)
                ratio = SequenceMatcher(None, original, element_cle).ratio()
                if ratio >= 0.80:
                    candidats.append((ratio, element_cle, categorie))
        if not candidats:
            return None
        candidats.sort(reverse=True)
        meilleur = candidats[0]
        second_ratio = candidats[1][0] if len(candidats) > 1 else 0.0
        if meilleur[0] - second_ratio < 0.05:
            return None
        # Une entité seulement ressemblante reste sous toute forme exacte
        # connue, y compris un verbe homographe comme « fonctionne ».
        return meilleur[1], meilleur[2], 55

    def expressions_normalisees(self, categorie: str) -> tuple[str, ...]:
        return tuple(cle(expression) for expression in self.expressions[categorie])

    def mots_fonctions(self) -> dict[str, set[str]]:
        categories: dict[str, set[str]] = {}
        for fichier in (
            "affirmations",
            "articles",
            "bruits",
            "grammaire",
            "negations",
        ):
            for categorie, valeurs in self._donnees[fichier].items():
                if isinstance(valeurs, list):
                    categories[f"{fichier}:{categorie}"] = {
                        cle(valeur) for valeur in valeurs
                    }
        return categories

    def vocabulaire_connu(self) -> set[str]:
        mots: set[str] = set()

        def ajouter(expression: object) -> None:
            mots.update(
                cle(morceau)
                for morceau in re.findall(
                    r"[a-zA-ZÀ-ÿ0-9_+#.-]+", str(expression)
                )
            )

        for regle in self.verbes.values():
            for forme in regle.get("formes", []):
                ajouter(forme)
        for valeurs in self.entites.values():
            for valeur in valeurs:
                ajouter(valeur)
        for valeurs in self.expressions.values():
            if isinstance(valeurs, list):
                for valeur in valeurs:
                    ajouter(valeur)
        for valeurs in self.mots_fonctions().values():
            mots.update(valeurs)
        mots.update(cle(mot) for mot in self.sens_ambigus)
        return mots
