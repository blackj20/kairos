"""Création traçable d'hypothèses depuis les interactions d'apprentissage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from .decision import EvenementExperience
from .memory import MemoryRepository


@dataclass(frozen=True, slots=True)
class ResultatHypothese:
    id: str
    nom: str
    statut: str
    creee: bool
    origine: str
    manques: tuple[str, ...]

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


class GestionnaireHypotheses:
    """Transforme une explication en candidate, jamais en vérité."""

    MANQUES = ("sources", "tests", "validation_secau")

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def depuis_experience(
        self,
        experience: EvenementExperience,
        *,
        acteur: str,
    ) -> ResultatHypothese | None:
        if acteur != "creator":
            return None
        relation = experience.resolution.get("candidate_semantic_relation")
        if experience.champ != "sens" and not isinstance(relation, dict):
            return None

        name = self._nom_experience(experience, relation)
        if not name:
            return None
        learning_kind = (
            "interaction.semantic_relation"
            if isinstance(relation, dict)
            else "interaction.user_explanation"
        )
        existing = self._candidate_existante(name, learning_kind)
        if existing is not None:
            self.repository.record_audit(
                "HYPOTHESIS_REUSED_FROM_INTERACTION",
                {
                    "hypothesis": existing["id"],
                    "experience": experience.id,
                },
            )
            return ResultatHypothese(
                id=str(existing["id"]),
                nom=name,
                statut="candidate",
                creee=False,
                origine="interaction",
                manques=self._manques(existing["payload"]),
            )

        payload = {
            "created_from_experience_id": experience.id,
            "name": name,
            "definition": experience.reponse.strip(),
            "domain": "language",
            "score": 60,
            "learning_kind": learning_kind,
            "question_id": experience.question_id,
            "evidence_ids": [],
            "examples": [],
            "counterexamples": [],
            "missing": list(self.MANQUES),
            "next_action": "collect_evidence",
        }
        if isinstance(relation, dict):
            payload["relation_candidate"] = dict(relation)
        hypothesis_id = self.repository.add_hypothesis(payload)
        return ResultatHypothese(
            id=hypothesis_id,
            nom=name,
            statut="candidate",
            creee=True,
            origine="interaction",
            manques=self.MANQUES,
        )

    def depuis_dialogue(
        self,
        candidate: dict[str, Any],
    ) -> ResultatHypothese:
        if candidate.get("status") != "candidate":
            raise ValueError("Le dialogue doit produire une candidate.")
        session_id = str(candidate.get("session_id", "")).strip()
        topic = str(candidate.get("topic", "")).strip()
        answers = candidate.get("answers")
        if not session_id or not topic or not isinstance(answers, dict):
            raise ValueError("Candidate de dialogue incomplète.")
        definition = str(answers.get("definition", "")).strip()
        if not definition:
            raise ValueError("La définition du dialogue est absente.")

        learning_kind = "dialogue.structured_explanation"
        existing = self._candidate_existante(topic, learning_kind)
        if existing is not None:
            self.repository.record_audit(
                "HYPOTHESIS_REUSED_FROM_DIALOGUE",
                {
                    "hypothesis": existing["id"],
                    "session": session_id,
                },
            )
            return ResultatHypothese(
                id=str(existing["id"]),
                nom=topic,
                statut="candidate",
                creee=False,
                origine="dialogue",
                manques=self._manques(existing["payload"]),
            )

        payload = {
            "created_from_experience_id": session_id,
            "name": topic,
            "definition": definition,
            "domain": "general",
            "score": 65,
            "learning_kind": learning_kind,
            "answers": dict(answers),
            "glossary": dict(candidate.get("glossary") or {}),
            "route_candidates": list(candidate.get("route_candidates") or []),
            "relation_candidates": list(
                candidate.get("relation_candidates") or []
            ),
            "evidence_ids": [],
            "examples": self._liste(answers.get("examples")),
            "counterexamples": self._liste(answers.get("counterexamples")),
            "missing": list(self.MANQUES),
            "next_action": "collect_evidence",
        }
        hypothesis_id = self.repository.add_hypothesis(payload)
        return ResultatHypothese(
            id=hypothesis_id,
            nom=topic,
            statut="candidate",
            creee=True,
            origine="dialogue",
            manques=self.MANQUES,
        )

    def statut(self, hypothesis_id: str | None = None) -> dict[str, Any]:
        if hypothesis_id:
            hypothesis = self.repository.hypothesis(hypothesis_id)
            if hypothesis is None:
                raise KeyError(hypothesis_id)
            return {
                "hypothesis": hypothesis,
                "missing": list(self._manques(hypothesis["payload"])),
            }
        candidates = self.repository.candidate_hypotheses()
        return {
            "count": len(candidates),
            "candidates": [
                {
                    "id": item["id"],
                    "name": item["payload"].get("name"),
                    "learning_kind": item["payload"].get("learning_kind"),
                    "status": item["status"],
                    "missing": list(self._manques(item["payload"])),
                    "next_action": item["payload"].get("next_action"),
                }
                for item in candidates
            ],
        }

    def _candidate_existante(
        self,
        name: str,
        learning_kind: str,
    ) -> dict[str, Any] | None:
        target = name.casefold().strip()
        for item in self.repository.candidate_hypotheses():
            payload = item["payload"]
            if (
                str(payload.get("name", "")).casefold().strip() == target
                and payload.get("learning_kind") == learning_kind
            ):
                return item
        return None

    @staticmethod
    def _nom_experience(
        experience: EvenementExperience,
        relation: object,
    ) -> str:
        if isinstance(relation, dict):
            return str(relation.get("source", "")).strip()
        cite = re.search(r"«\s*([^»]+?)\s*»", experience.question)
        if cite:
            return cite.group(1).strip()
        inconnus = experience.analyse_reponse.get("jetons_inconnus", [])
        if inconnus:
            return str(inconnus[-1]).strip()
        resolution = experience.resolution.get("value")
        return str(resolution or "").strip()

    @classmethod
    def _manques(cls, payload: dict[str, Any]) -> tuple[str, ...]:
        missing = payload.get("missing")
        if isinstance(missing, list):
            return tuple(str(item) for item in missing)
        return cls.MANQUES

    @staticmethod
    def _liste(value: object) -> list[str]:
        if not isinstance(value, str):
            return []
        return [
            item.strip()
            for item in re.split(r"[,;\n]|\bet\b", value)
            if item.strip()
        ]
