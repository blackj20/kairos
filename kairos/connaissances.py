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
        "lexique.json",
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
        self._construire_indexes()

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
    def lexique(self) -> dict[str, Any]:
        """Expose les mots courants avec sens, catégorie et route éventuelle."""

        entrees = self._donnees["lexique"].get("entries", {})
        if not isinstance(entrees, dict):
            raise ErreurConnaissances(
                "data/fr/lexique.json : entries doit être un objet."
            )
        return entrees

    def _construire_indexes(self) -> None:
        """Construit une fois les tables utilisées sur chaque requête."""

        self._index_verbes: dict[str, tuple[str, dict[str, Any]]] = {}
        for lemme, regle in self.verbes.items():
            for forme in regle.get("formes", []):
                self._index_verbes[cle(forme)] = (lemme, regle)

        self._index_entites: dict[str, tuple[str, str]] = {}
        for categorie, elements in self.entites.items():
            for element in elements:
                self._index_entites[cle(element)] = (
                    str(element).casefold(),
                    categorie,
                )

        self._index_fonctions: dict[str, tuple[str, ...]] = {}
        categories_fonctions: dict[str, set[str]] = {}
        for fichier in (
            "affirmations",
            "articles",
            "bruits",
            "grammaire",
            "negations",
        ):
            for categorie, valeurs in self._donnees[fichier].items():
                if not isinstance(valeurs, list):
                    continue
                nom_categorie = f"{fichier}:{categorie}"
                normalisees = {cle(valeur) for valeur in valeurs}
                categories_fonctions[nom_categorie] = normalisees
                for mot in normalisees:
                    self._index_fonctions.setdefault(mot, ())
                    self._index_fonctions[mot] += (nom_categorie,)
        self._categories_fonctions = categories_fonctions

        self._index_expressions: dict[str, tuple[str, ...]] = {}
        for categorie, expressions in self.expressions.items():
            if not isinstance(expressions, list):
                continue
            for expression in expressions:
                for mot in re.findall(
                    r"[a-zA-ZÀ-ÿ0-9_+#.-]+", str(expression)
                ):
                    mot_cle = cle(mot)
                    existantes = self._index_expressions.get(mot_cle, ())
                    if categorie not in existantes:
                        self._index_expressions[mot_cle] = (
                            *existantes,
                            categorie,
                        )

        self._index_lexique: dict[str, tuple[str, dict[str, Any]]] = {}
        for lemme, entree in self.lexique.items():
            if not isinstance(entree, dict):
                continue
            for forme in entree.get("forms", []):
                self._index_lexique[cle(forme)] = (lemme, entree)

        self._vocabulaire_statique = set(self._index_verbes)
        self._vocabulaire_statique.update(self._index_entites)
        self._vocabulaire_statique.update(self._index_fonctions)
        self._vocabulaire_statique.update(self._index_expressions)
        self._vocabulaire_statique.update(self._index_lexique)
        self._vocabulaire_statique.update(cle(mot) for mot in self.sens_ambigus)

    @property
    def nombre_verbes_indexes(self) -> int:
        return len(self._index_verbes)

    @property
    def nombre_entites_indexees(self) -> int:
        return len(self._index_entites)

    @property
    def nombre_mots_courants_indexes(self) -> int:
        return len(self._index_lexique)

    def fonctions_pour(self, mot: str) -> tuple[str, ...]:
        return self._index_fonctions.get(cle(mot), ())

    def expressions_pour(self, mot: str) -> tuple[str, ...]:
        return self._index_expressions.get(cle(mot), ())

    def trouver_mot_courant(self, mot: str) -> dict[str, Any] | None:
        trouve = self._index_lexique.get(cle(mot))
        if trouve is None:
            return None
        lemme, entree = trouve
        return {"lemma": lemme, **entree}

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
        return self._index_verbes.get(mot_cle)

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
        return self._index_entites.get(mot_cle)

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
        """Compatibilité : renvoie une copie des catégories pré-indexées."""

        return {
            categorie: set(valeurs)
            for categorie, valeurs in self._categories_fonctions.items()
        }

    def vocabulaire_connu(self) -> set[str]:
        """Retourne le vocabulaire indexé et les relations confirmées."""

        mots = set(self._vocabulaire_statique)
        for source, relation in self.relations_verbes.toutes().items():
            mots.add(cle(source))
            mots.add(cle(str(relation.get("target", ""))))
        mots.update(self.corrections.toutes())
        return mots
