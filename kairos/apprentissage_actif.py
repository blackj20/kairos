"""Apprentissage actif : choisir une question utile et enrichir une candidate."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from rapidfuzz import fuzz, process, utils

from .memory import MemoryRepository


def _normaliser(texte: str) -> str:
    return " ".join(
        texte.casefold().replace("’", "'").strip(" \t\n?.!").split()
    )


@dataclass(frozen=True, slots=True)
class QuestionUtile:
    """Question liée à un manque précis et à un gain attendu."""

    hypothesis_id: str
    champ: str
    texte: str
    gain_attendu: int
    raison: str
    tentative: int = 1

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TourApprentissage:
    """Résultat observable d'un tour d'apprentissage actif."""

    texte: str
    hypothesis_id: str | None
    statut: str
    question: QuestionUtile | None = None
    liens_crees: tuple[dict[str, Any], ...] = ()

    def vers_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.question is not None:
            payload["question"] = self.question.vers_dict()
        return payload


class ExtracteurLiens:
    """Extrait de petites relations explicables sans prétendre valider le fond."""

    _ARTICLES = r"(?:un|une|le|la|les|l')"
    _CIBLE = r"(?P<cible>[a-zA-ZÀ-ÿ0-9][a-zA-ZÀ-ÿ0-9_+#' -]{1,80})"

    def extraire(self, sujet: str, texte: str) -> tuple[dict[str, Any], ...]:
        brut = " ".join(texte.strip().split())
        normalise = _normaliser(brut)
        sujet_normalise = _normaliser(sujet)
        motifs = (
            (
                "est_un",
                rf"^(?:(?:{re.escape(sujet_normalise)}\s+(?:est|c[' ]?est)|c[' ]?est)\s+)?"
                rf"{self._ARTICLES}\s+{self._CIBLE}$",
            ),
            (
                "equivalent",
                rf"^(?:{re.escape(sujet_normalise)}\s+)?"
                rf"(?:signifie|veut dire|correspond [aà])\s+{self._CIBLE}$",
            ),
            (
                "fonction",
                rf"^(?:{re.escape(sujet_normalise)}\s+)?"
                rf"(?:sert [aà]|est utilis[eé] pour)\s+{self._CIBLE}$",
            ),
            (
                "permet",
                rf"^(?:{re.escape(sujet_normalise)}\s+)?"
                rf"(?:permet de|aide [aà])\s+{self._CIBLE}$",
            ),
            (
                "lie_a",
                rf"^(?:{re.escape(sujet_normalise)}\s+)?"
                rf"(?:est li[eé] [aà]|d[eé]pend de)\s+{self._CIBLE}$",
            ),
        )
        liens: list[dict[str, Any]] = []
        for relation, motif in motifs:
            correspondance = re.match(motif, normalise, flags=re.IGNORECASE)
            if correspondance is None:
                continue
            cible = correspondance.group("cible").strip(" .")
            if not cible or cible == sujet_normalise:
                continue
            liens.append(
                {
                    "source": sujet_normalise,
                    "relation": relation,
                    "target": cible,
                    "score": 70,
                    "evidence": brut,
                    "status": "candidate",
                    "provenance": "active_learning.creator_answer",
                }
            )
        return tuple(liens)


class ApprentissageActif:
    """Pose une seule question à fort gain et enrichit une hypothèse candidate."""

    GAINS = {
        "relation": 40,
        "examples": 25,
        "counterexamples": 20,
        "source": 15,
    }
    PAUSE = {
        "stop",
        "pause",
        "arrete",
        "arrête",
        "on reprend plus tard",
    }
    INCONNU = {
        "je ne sais pas",
        "j'ignore",
        "aucune idee",
        "aucune idée",
        "passe",
    }

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository
        self.extracteur = ExtracteurLiens()

    @property
    def active(self) -> bool:
        return self._candidate_active() is not None

    @property
    def attente(self) -> str | None:
        candidate = self._candidate_active()
        if candidate is None:
            return None
        session = candidate["payload"].get("active_learning", {})
        champ = session.get("pending_field")
        if not champ:
            return None
        return f"réponse sur {champ} pour {candidate['payload'].get('name', '')}"

    def demarrer(self, selecteur: str | None = None) -> TourApprentissage:
        """Choisit une candidate et pose la question au meilleur gain."""

        candidate = self._resoudre_candidate(selecteur)
        if candidate is None:
            return TourApprentissage(
                texte=(
                    "Je n'ai aucune hypothèse candidate à consolider. "
                    "Explique d'abord un mot ou réponds à une question de manque."
                ),
                hypothesis_id=None,
                statut="nothing_to_learn",
            )
        payload = dict(candidate["payload"])
        session = dict(payload.get("active_learning", {}))
        session.update(
            {
                "status": "active",
                "pending_field": None,
                "clarifications": dict(session.get("clarifications", {})),
                "skipped_fields": list(session.get("skipped_fields", [])),
                "questions": list(session.get("questions", [])),
                "raw_answers": dict(session.get("raw_answers", {})),
            }
        )
        payload["active_learning"] = session
        self.repository.update_hypothesis_payload(
            str(candidate["id"]),
            payload,
            event="ACTIVE_LEARNING_STARTED",
        )
        refreshed = self.repository.hypothesis(str(candidate["id"]))
        assert refreshed is not None
        return self._prochaine_question(refreshed)

    def recevoir(self, reponse: str) -> TourApprentissage:
        """Traite la réponse active, crée des liens candidats puis avance."""

        candidate = self._candidate_active()
        if candidate is None:
            return TourApprentissage(
                "Aucune question d'apprentissage actif n'attend de réponse.",
                None,
                "inactive",
            )
        hypothesis_id = str(candidate["id"])
        payload = dict(candidate["payload"])
        session = dict(payload.get("active_learning", {}))
        normalisee = _normaliser(reponse)
        if normalisee in {_normaliser(item) for item in self.PAUSE}:
            session["status"] = "paused"
            session["pending_field"] = None
            payload["active_learning"] = session
            self.repository.update_hypothesis_payload(
                hypothesis_id,
                payload,
                event="ACTIVE_LEARNING_PAUSED",
            )
            return TourApprentissage(
                "Apprentissage mis en pause. Dis « continue d'apprendre » pour reprendre.",
                hypothesis_id,
                "paused",
            )

        champ = str(session.get("pending_field") or "")
        if not champ:
            return self._prochaine_question(candidate)

        if normalisee in {_normaliser(item) for item in self.INCONNU}:
            ignores = list(session.get("skipped_fields", []))
            if champ not in ignores:
                ignores.append(champ)
            session["skipped_fields"] = ignores
            session["pending_field"] = None
            payload["active_learning"] = session
            self.repository.update_hypothesis_payload(
                hypothesis_id,
                payload,
                event="ACTIVE_LEARNING_FIELD_SKIPPED",
            )
            refreshed = self.repository.hypothesis(hypothesis_id)
            assert refreshed is not None
            return self._prochaine_question(
                refreshed,
                prefixe="D'accord, je marque ce point comme non résolu. ",
            )

        liens: tuple[dict[str, Any], ...] = ()
        acquis = False
        if champ == "relation":
            liens = self.extracteur.extraire(str(payload.get("name", "")), reponse)
            if liens:
                existants = list(payload.get("relation_candidates", []))
                cles = {
                    (
                        str(item.get("source")),
                        str(item.get("relation")),
                        str(item.get("target")),
                    )
                    for item in existants
                    if isinstance(item, dict)
                }
                for lien in liens:
                    cle_lien = (
                        str(lien["source"]),
                        str(lien["relation"]),
                        str(lien["target"]),
                    )
                    if cle_lien not in cles:
                        existants.append(lien)
                        cles.add(cle_lien)
                payload["relation_candidates"] = existants
                acquis = True
            else:
                clarifications = dict(session.get("clarifications", {}))
                tentative = int(clarifications.get(champ, 0)) + 1
                clarifications[champ] = tentative
                session["clarifications"] = clarifications
                if tentative <= 1:
                    payload["active_learning"] = session
                    self.repository.update_hypothesis_payload(
                        hypothesis_id,
                        payload,
                        event="ACTIVE_LEARNING_CLARIFIED",
                    )
                    question = QuestionUtile(
                        hypothesis_id,
                        champ,
                        (
                            f"Je n'arrive pas encore à relier « {payload.get('name')} ». "
                            "Réponds simplement par exemple : « c'est une salutation », "
                            "« signifie installer » ou « sert à rechercher une information »."
                        ),
                        self.GAINS[champ],
                        "une reformulation structurée évite un lien inventé",
                        tentative=2,
                    )
                    return TourApprentissage(
                        question.texte,
                        hypothesis_id,
                        "waiting_answer",
                        question=question,
                    )
                brutes = dict(session.get("raw_answers", {}))
                brutes[champ] = reponse.strip()
                session["raw_answers"] = brutes
                ignores = list(session.get("skipped_fields", []))
                if champ not in ignores:
                    ignores.append(champ)
                session["skipped_fields"] = ignores
        elif champ in {"examples", "counterexamples"}:
            minimum = 3 if champ == "examples" else 2
            valeurs = self._liste(reponse)
            existantes = [
                str(item)
                for item in payload.get(champ, [])
                if str(item).strip()
            ]
            for valeur in valeurs:
                if not self._contient_proche(valeur, existantes):
                    existantes.append(valeur)
            payload[champ] = existantes
            acquis = len(existantes) >= minimum
        elif champ == "source":
            pistes = [
                str(item)
                for item in payload.get("source_leads", [])
                if str(item).strip()
            ]
            if normalisee in {"cherche toi meme", "cherche toi-même"}:
                piste = "route:information.search"
                payload["source_strategy"] = "self_research"
            else:
                piste = reponse.strip()
            if piste and piste not in pistes:
                pistes.append(piste)
            payload["source_leads"] = pistes
            acquis = bool(pistes)

        session["pending_field"] = None
        payload["active_learning"] = session
        payload["missing"] = self._manques(payload)
        payload["next_action"] = (
            "research_and_test"
            if not self._champs_restants(payload)
            else "ask_best_question"
        )
        score = self._score_structure(payload)
        self.repository.update_hypothesis_payload(
            hypothesis_id,
            payload,
            score=score,
            event=(
                "ACTIVE_LEARNING_ANSWER_ACCEPTED"
                if acquis
                else "ACTIVE_LEARNING_ANSWER_PARTIAL"
            ),
        )
        refreshed = self.repository.hypothesis(hypothesis_id)
        assert refreshed is not None
        return self._prochaine_question(
            refreshed,
            prefixe=(
                f"J'ai créé {len(liens)} lien(s) candidat(s). "
                if liens
                else "J'ai conservé cette réponse. "
            ),
            liens=liens,
        )

    def statut(self) -> dict[str, Any]:
        candidates = self.repository.candidate_hypotheses()
        return {
            "active": self.active,
            "candidates": [
                {
                    "id": item["id"],
                    "name": item["payload"].get("name"),
                    "learning": item["payload"].get("active_learning"),
                    "missing": item["payload"].get("missing", []),
                    "structure_score": self._score_structure(item["payload"]),
                }
                for item in candidates
            ],
        }

    def _prochaine_question(
        self,
        candidate: dict[str, Any],
        *,
        prefixe: str = "",
        liens: tuple[dict[str, Any], ...] = (),
    ) -> TourApprentissage:
        hypothesis_id = str(candidate["id"])
        payload = dict(candidate["payload"])
        restants = self._champs_restants(payload)
        session = dict(payload.get("active_learning", {}))
        if not restants:
            ignores = set(session.get("skipped_fields", []))
            bloquants = sorted(
                ignores.intersection({"relation", "examples", "counterexamples"})
            )
            if bloquants:
                session["status"] = "needs_human_input"
                prochain_statut = "needs_human_input"
                prochaine_action = "await_creator"
                evenement = "ACTIVE_LEARNING_BLOCKED"
                conclusion = (
                    "Je m'arrête proprement : il manque encore "
                    + ", ".join(bloquants)
                    + ". Je conserve les réponses brutes sans inventer de lien."
                )
            else:
                session["status"] = "ready_for_research"
                prochain_statut = "ready_for_research"
                prochaine_action = "research_and_test"
                evenement = "ACTIVE_LEARNING_STRUCTURED"
                conclusion = (
                    "Le dossier est structuré. Il reste candidat : je dois encore "
                    "vérifier les sources, lancer Tester puis obtenir le verdict SECAU."
                )
            session["pending_field"] = None
            payload["active_learning"] = session
            payload["missing"] = self._manques(payload)
            payload["next_action"] = prochaine_action
            self.repository.update_hypothesis_payload(
                hypothesis_id,
                payload,
                score=self._score_structure(payload),
                event=evenement,
            )
            return TourApprentissage(
                prefixe + conclusion,
                hypothesis_id,
                prochain_statut,
                liens_crees=liens,
            )

        champ = max(restants, key=lambda item: self.GAINS[item])
        questions = list(session.get("questions", []))
        tentative = 1 + sum(item.get("field") == champ for item in questions if isinstance(item, dict))
        question = QuestionUtile(
            hypothesis_id=hypothesis_id,
            champ=champ,
            texte=self._texte_question(champ, payload),
            gain_attendu=self.GAINS[champ],
            raison=self._raison(champ),
            tentative=tentative,
        )
        session["status"] = "active"
        session["pending_field"] = champ
        questions.append(
            {
                "field": champ,
                "gain": question.gain_attendu,
                "reason": question.raison,
                "attempt": tentative,
            }
        )
        session["questions"] = questions
        payload["active_learning"] = session
        self.repository.update_hypothesis_payload(
            hypothesis_id,
            payload,
            event="ACTIVE_LEARNING_QUESTION_ASKED",
        )
        return TourApprentissage(
            prefixe + question.texte,
            hypothesis_id,
            "waiting_answer",
            question=question,
            liens_crees=liens,
        )

    def _resoudre_candidate(self, selecteur: str | None) -> dict[str, Any] | None:
        candidates = self.repository.candidate_hypotheses()
        if not candidates:
            return None
        if not selecteur:
            return max(
                candidates,
                key=lambda item: (
                    len(self._champs_restants(item["payload"])),
                    -int(item.get("score", 0)),
                ),
            )
        brut = selecteur.strip()
        for candidate in candidates:
            if str(candidate["id"]) == brut:
                return candidate
            if _normaliser(str(candidate["payload"].get("name", ""))) == _normaliser(brut):
                return candidate
        noms = [
            str(item["payload"].get("name", ""))
            for item in candidates
            if item["payload"].get("name")
        ]
        correspondance = process.extractOne(
            brut,
            noms,
            scorer=fuzz.WRatio,
            processor=utils.default_process,
            score_cutoff=82,
        )
        if correspondance is None:
            return None
        nom = str(correspondance[0])
        return next(
            item for item in candidates
            if str(item["payload"].get("name", "")) == nom
        )

    def _candidate_active(self) -> dict[str, Any] | None:
        for candidate in self.repository.candidate_hypotheses():
            session = candidate["payload"].get("active_learning", {})
            if isinstance(session, dict) and session.get("status") == "active":
                return candidate
        return None

    def _champs_restants(self, payload: dict[str, Any]) -> list[str]:
        session = payload.get("active_learning", {})
        ignores = set(session.get("skipped_fields", [])) if isinstance(session, dict) else set()
        restants: list[str] = []
        relation_presente = bool(payload.get("relation_candidate")) or bool(
            payload.get("relation_candidates")
        )
        if not relation_presente and "relation" not in ignores:
            restants.append("relation")
        if len(payload.get("examples", [])) < 3 and "examples" not in ignores:
            restants.append("examples")
        if (
            len(payload.get("counterexamples", [])) < 2
            and "counterexamples" not in ignores
        ):
            restants.append("counterexamples")
        if (
            not payload.get("source_leads")
            and not payload.get("evidence_ids")
            and "source" not in ignores
        ):
            restants.append("source")
        return restants

    @staticmethod
    def _manques(payload: dict[str, Any]) -> list[str]:
        manques: list[str] = []
        if not payload.get("relation_candidate") and not payload.get("relation_candidates"):
            manques.append("relation")
        if len(payload.get("examples", [])) < 3:
            manques.append("examples")
        if len(payload.get("counterexamples", [])) < 2:
            manques.append("counterexamples")
        if not payload.get("evidence_ids"):
            manques.append("sources")
        manques.extend(["tests", "validation_secau"])
        return list(dict.fromkeys(manques))

    @staticmethod
    def _score_structure(payload: dict[str, Any]) -> int:
        score = 20
        if payload.get("definition"):
            score += 20
        if payload.get("relation_candidate") or payload.get("relation_candidates"):
            score += 20
        score += min(15, 5 * len(payload.get("examples", [])))
        score += min(10, 5 * len(payload.get("counterexamples", [])))
        if payload.get("source_leads") or payload.get("evidence_ids"):
            score += 15
        return min(100, score)

    @staticmethod
    def _liste(texte: str) -> list[str]:
        morceaux = [
            item.strip(" -\t\n")
            for item in re.split(r"[,;\n]|\bet\b", texte, flags=re.IGNORECASE)
            if item.strip(" -\t\n")
        ]
        return morceaux or ([texte.strip()] if texte.strip() else [])

    @staticmethod
    def _contient_proche(valeur: str, existantes: list[str]) -> bool:
        if not existantes:
            return False
        correspondance = process.extractOne(
            valeur,
            existantes,
            scorer=fuzz.WRatio,
            processor=utils.default_process,
            score_cutoff=92,
        )
        return correspondance is not None

    @staticmethod
    def _texte_question(champ: str, payload: dict[str, Any]) -> str:
        sujet = str(payload.get("name", "ce concept"))
        if champ == "relation":
            return (
                f"Pour relier « {sujet} » à ce que je connais : "
                "c'est un type de quoi, que signifie-t-il ou à quoi sert-il ?"
            )
        if champ == "examples":
            manque = max(1, 3 - len(payload.get("examples", [])))
            return (
                f"Donne {manque} exemple(s) concret(s) où « {sujet} » "
                "garde exactement ce sens."
            )
        if champ == "counterexamples":
            manque = max(1, 2 - len(payload.get("counterexamples", [])))
            return (
                f"Donne {manque} cas où « {sujet} » ne doit pas avoir ce sens. "
                "Cela m'aide à éviter une mauvaise généralisation."
            )
        return (
            f"Où puis-je vérifier l'explication de « {sujet} » ? "
            "Donne une piste précise ou réponds « cherche toi-même »."
        )

    @staticmethod
    def _raison(champ: str) -> str:
        return {
            "relation": "un lien interne rend l'information réutilisable",
            "examples": "les exemples testent la généralisation positive",
            "counterexamples": "les contre-exemples délimitent le sens",
            "source": "une piste de source prépare la vérification",
        }[champ]
