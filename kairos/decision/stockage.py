"""Stockages injectables pour isoler les effets de bord de la décision."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from .modeles import (
    EvenementApprentissage,
    EvenementExperience,
    QuestionEnAttente,
)


class StockageDecision(Protocol):
    def sauvegarder_question(self, question: QuestionEnAttente) -> None: ...

    def obtenir_question(self, question_id: str) -> QuestionEnAttente | None: ...

    def questions_en_attente(self) -> tuple[QuestionEnAttente, ...]: ...

    def mettre_a_jour_question(self, question: QuestionEnAttente) -> None: ...

    def sauvegarder_experience(self, experience: EvenementExperience) -> None: ...

    def sauvegarder_apprentissage(
        self, evenement: EvenementApprentissage
    ) -> EvenementApprentissage: ...

    def experiences(self) -> tuple[EvenementExperience, ...]: ...

    def apprentissages(self) -> tuple[EvenementApprentissage, ...]: ...


class StockageMemoire:
    """Stockage sans disque utilisé par défaut et dans les tests."""

    def __init__(self) -> None:
        self._questions: list[QuestionEnAttente] = []
        self._experiences: list[EvenementExperience] = []
        self._apprentissages: list[EvenementApprentissage] = []
        self._verrou = threading.RLock()

    def sauvegarder_question(self, question: QuestionEnAttente) -> None:
        with self._verrou:
            self._questions.append(question)

    def obtenir_question(self, question_id: str) -> QuestionEnAttente | None:
        with self._verrou:
            return next(
                (
                    question
                    for question in self._questions
                    if question.id == question_id
                ),
                None,
            )

    def questions_en_attente(self) -> tuple[QuestionEnAttente, ...]:
        with self._verrou:
            return tuple(
                question
                for question in self._questions
                if question.statut == "waiting_answer"
            )

    def mettre_a_jour_question(self, question: QuestionEnAttente) -> None:
        with self._verrou:
            for index, existante in enumerate(self._questions):
                if existante.id == question.id:
                    self._questions[index] = question
                    return
            raise KeyError(f"Question inconnue : {question.id}")

    def sauvegarder_experience(self, experience: EvenementExperience) -> None:
        with self._verrou:
            self._experiences.append(experience)

    def sauvegarder_apprentissage(
        self, evenement: EvenementApprentissage
    ) -> EvenementApprentissage:
        with self._verrou:
            for index, existant in enumerate(self._apprentissages):
                if (
                    existant.champ == evenement.champ
                    and existant.focus == evenement.focus
                    and existant.statut == "to_study"
                ):
                    consolide = replace(
                        existant,
                        occurrences=existant.occurrences + 1,
                    )
                    self._apprentissages[index] = consolide
                    return consolide
            self._apprentissages.append(evenement)
            return evenement

    def experiences(self) -> tuple[EvenementExperience, ...]:
        with self._verrou:
            return tuple(self._experiences)

    def apprentissages(self) -> tuple[EvenementApprentissage, ...]:
        with self._verrou:
            return tuple(self._apprentissages)


class StockageJson:
    """Stockage persistant limité aux trois fichiers autorisés de la V0.3."""

    FICHIERS = {
        "questions": "pending_questions.json",
        "experiences": "experiences.json",
        "apprentissages": "learning_events.json",
    }

    def __init__(self, dossier: Path | None = None) -> None:
        racine = Path(__file__).resolve().parent.parent.parent
        self.dossier = dossier or racine / "memory"
        self._verrou = threading.RLock()
        for nom in self.FICHIERS.values():
            chemin = self.dossier / nom
            if not chemin.is_file():
                raise FileNotFoundError(f"Fichier mémoire absent : {chemin}")

    def _lire_items(self, categorie: str) -> list[dict[str, Any]]:
        chemin = self.dossier / self.FICHIERS[categorie]
        with chemin.open("r", encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        items = donnees.get("items")
        if not isinstance(items, list):
            raise ValueError(f"Format mémoire invalide : {chemin}")
        return items

    def _ecrire_items(
        self, categorie: str, items: list[dict[str, Any]]
    ) -> None:
        chemin = self.dossier / self.FICHIERS[categorie]
        temporaire = chemin.with_suffix(".tmp")
        contenu = {"version": 1, "items": items}
        with temporaire.open("w", encoding="utf-8") as fichier:
            json.dump(contenu, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
        os.replace(temporaire, chemin)

    def sauvegarder_question(self, question: QuestionEnAttente) -> None:
        with self._verrou:
            items = self._lire_items("questions")
            items.append(question.vers_dict())
            self._ecrire_items("questions", items)

    def obtenir_question(self, question_id: str) -> QuestionEnAttente | None:
        with self._verrou:
            for item in self._lire_items("questions"):
                if item["id"] == question_id:
                    return QuestionEnAttente(**item)
        return None

    def questions_en_attente(self) -> tuple[QuestionEnAttente, ...]:
        with self._verrou:
            return tuple(
                QuestionEnAttente(**item)
                for item in self._lire_items("questions")
                if item["statut"] == "waiting_answer"
            )

    def mettre_a_jour_question(self, question: QuestionEnAttente) -> None:
        with self._verrou:
            items = self._lire_items("questions")
            for index, item in enumerate(items):
                if item["id"] == question.id:
                    items[index] = question.vers_dict()
                    self._ecrire_items("questions", items)
                    return
            raise KeyError(f"Question inconnue : {question.id}")

    def sauvegarder_experience(self, experience: EvenementExperience) -> None:
        with self._verrou:
            items = self._lire_items("experiences")
            items.append(experience.vers_dict())
            self._ecrire_items("experiences", items)

    def sauvegarder_apprentissage(
        self, evenement: EvenementApprentissage
    ) -> EvenementApprentissage:
        with self._verrou:
            items = self._lire_items("apprentissages")
            for index, item in enumerate(items):
                if (
                    item["champ"] == evenement.champ
                    and item.get("focus") == evenement.focus
                    and item["statut"] == "to_study"
                ):
                    item["occurrences"] += 1
                    items[index] = item
                    self._ecrire_items("apprentissages", items)
                    return EvenementApprentissage(**item)
            items.append(evenement.vers_dict())
            self._ecrire_items("apprentissages", items)
            return evenement

    def experiences(self) -> tuple[EvenementExperience, ...]:
        with self._verrou:
            return tuple(
                EvenementExperience(**item)
                for item in self._lire_items("experiences")
            )

    def apprentissages(self) -> tuple[EvenementApprentissage, ...]:
        with self._verrou:
            return tuple(
                EvenementApprentissage(**item)
                for item in self._lire_items("apprentissages")
            )
