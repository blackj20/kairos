"""Dialogue d'apprentissage naturel, borné et persistant."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .cognition import Reflechir
from .connaissances import Connaissances
from .normalisation import cle


@dataclass(frozen=True, slots=True)
class ResultatDialogue:
    """Résultat observable d'un tour d'apprentissage."""

    texte: str
    termine: bool = False
    candidate: dict[str, Any] | None = None


class StockageSeance:
    """Persistance atomique d'une séance, sans promotion en connaissance."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin
        self._memoire: dict[str, Any] | None = None
        if chemin is not None and chemin.exists():
            try:
                charge = json.loads(chemin.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as erreur:
                raise RuntimeError(f"Séance d'apprentissage illisible : {erreur}") from erreur
            if isinstance(charge, dict):
                self._memoire = charge

    def charger_active(self) -> dict[str, Any] | None:
        if self._memoire and self._memoire.get("status") == "active":
            return dict(self._memoire)
        return None

    def sauvegarder(self, session: dict[str, Any]) -> None:
        self._memoire = dict(session)
        if self.chemin is None:
            return
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = self.chemin.with_suffix(self.chemin.suffix + ".tmp")
        temporaire.write_text(
            json.dumps(session, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporaire.replace(self.chemin)


class DialogueApprentissage:
    """Garde l'objectif parent pendant les clarifications secondaires."""

    CHAMPS = ("definition", "examples", "counterexamples", "relations")

    def __init__(
        self,
        connaissances: Connaissances,
        chemin: Path | None = None,
        configuration: Path | None = None,
    ) -> None:
        self.connaissances = connaissances
        racine = Path(__file__).resolve().parent.parent
        config_path = configuration or racine / "data" / "learning" / "dialogue.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.stockage = StockageSeance(chemin)
        self.session = self.stockage.charger_active()

    @property
    def active(self) -> bool:
        return self.session is not None and self.session.get("status") == "active"

    @property
    def attente(self) -> str | None:
        if not self.active:
            return None
        assert self.session is not None
        pending = self.session.get("pending")
        if pending:
            return str(pending["attente"])
        champ = self.CHAMPS[int(self.session["index"])]
        return str(self.config["fields"][champ]["expectation"])

    def demarrer(self, topic: str, *, correction: bool = False) -> str:
        topic = topic.strip() or "ma compréhension actuelle"
        self.session = {
            "id": str(uuid4()),
            "status": "active",
            "topic": topic,
            "index": 0,
            "answers": {},
            "glossary": {},
            "pending": None,
            "clarifications": 0,
            "corrections_confirmed": 0,
            "unknown_words_explained": 0,
        }
        self.stockage.sauvegarder(self.session)
        prefixe = (
            f"J'ai interprété le sujet comme « {topic} ». "
            "Cette correction reste temporaire tant qu'elle n'est pas confirmée.\n"
            if correction
            else ""
        )
        return prefixe + self._question_courante()

    def traiter(self, texte: str) -> ResultatDialogue:
        if not self.active:
            raise RuntimeError("Aucune séance d'apprentissage active.")
        assert self.session is not None
        reponse = texte.strip()
        normalisee = cle(reponse)
        if normalisee in {cle(x) for x in self.config["commands"]["cancel"]}:
            self.session["status"] = "cancelled"
            self.stockage.sauvegarder(self.session)
            self.session = None
            return ResultatDialogue(
                "Séance arrêtée. Aucune réponse n'a été confirmée comme connaissance.",
                termine=True,
            )

        pending = self.session.get("pending")
        if pending:
            return self._traiter_clarification(reponse, pending)

        correction = self._proposer_correction(reponse)
        if correction and int(self.session["clarifications"]) < int(self.config["max_clarifications_per_field"]):
            original, corrige = correction
            self.session["pending"] = {
                "type": "spelling",
                "original": original,
                "corrected": corrige,
                "answer": reponse,
                "attente": "oui ou non",
            }
            self.session["clarifications"] = int(self.session["clarifications"]) + 1
            self.stockage.sauvegarder(self.session)
            return ResultatDialogue(
                f"Je pense que « {original} » signifie « {corrige} ». "
                "Est-ce bien ce que tu voulais écrire ? "
                "Après ta réponse, je reprendrai la question principale."
            )

        inconnu = self._mot_inconnu_isole(reponse)
        if inconnu and int(self.session["clarifications"]) < int(self.config["max_clarifications_per_field"]):
            self.session["pending"] = {
                "type": "unknown",
                "word": inconnu,
                "answer": reponse,
                "attente": f"signification de « {inconnu} » dans cette phrase",
            }
            self.session["clarifications"] = int(self.session["clarifications"]) + 1
            self.stockage.sauvegarder(self.session)
            return ResultatDialogue(
                f"Je ne comprends pas encore « {inconnu} » dans ta réponse. "
                "Que signifie ce mot ici ? Je garderai ensuite ta réponse et "
                "reprendrai la question principale."
            )
        return self._evaluer_et_avancer(reponse)

    def _traiter_clarification(
        self, reponse: str, pending: dict[str, Any]
    ) -> ResultatDialogue:
        assert self.session is not None
        if pending["type"] == "spelling":
            normalisee = cle(reponse)
            positifs = {cle(x) for x in self.config["commands"]["yes"]}
            if normalisee in positifs:
                original = str(pending["original"])
                corrige = str(pending["corrected"])
                self.connaissances.corrections.confirmer(original, corrige)
                texte = re.sub(
                    rf"\b{re.escape(original)}\b",
                    corrige,
                    str(pending["answer"]),
                    flags=re.IGNORECASE,
                )
                self.session["corrections_confirmed"] = (
                    int(self.session["corrections_confirmed"]) + 1
                )
                self.session["pending"] = None
                self.stockage.sauvegarder(self.session)
                return self._evaluer_et_avancer(texte, prefixe="Correction confirmée. ")
            self.session["pending"] = None
            self.stockage.sauvegarder(self.session)
            return ResultatDialogue(
                "D'accord, je n'enregistre pas cette correction. "
                "Reformule ta réponse, puis je reprendrai la même question.\n"
                + self._question_courante()
            )

        mot = str(pending["word"])
        self.session["glossary"][mot] = reponse
        self.session["unknown_words_explained"] = (
            int(self.session["unknown_words_explained"]) + 1
        )
        originale = str(pending["answer"])
        self.session["pending"] = None
        self.stockage.sauvegarder(self.session)
        return self._evaluer_et_avancer(
            originale,
            prefixe=f"J'associe provisoirement « {mot} » à ton explication. ",
            ignorer_inconnus=True,
        )

    def _evaluer_et_avancer(
        self,
        reponse: str,
        *,
        prefixe: str = "",
        ignorer_inconnus: bool = False,
    ) -> ResultatDialogue:
        assert self.session is not None
        index = int(self.session["index"])
        champ = self.CHAMPS[index]
        valide, conseil = self._evaluer(champ, reponse)
        if not valide:
            self.stockage.sauvegarder(self.session)
            return ResultatDialogue(
                prefixe
                + f"Je n'ai pas encore assez d'éléments : {conseil}\n"
                + "Je garde l'objectif principal et la même question : "
                + self._question_texte(champ)
            )

        self.session["answers"][champ] = reponse
        route = self._route_candidate(reponse)
        if route:
            self.session.setdefault("route_candidates", [])
            if route not in self.session["route_candidates"]:
                self.session["route_candidates"].append(route)
        prochain = index + 1
        if prochain == len(self.CHAMPS):
            self.session["status"] = "candidate"
            candidate = {
                "session_id": self.session["id"],
                "topic": self.session["topic"],
                "answers": dict(self.session["answers"]),
                "glossary": dict(self.session["glossary"]),
                "route_candidates": list(self.session.get("route_candidates", [])),
                "status": "candidate",
                "reusable": False,
            }
            self.stockage.sauvegarder(self.session)
            self.session = None
            return ResultatDialogue(
                prefixe
                + "Séance terminée. J'ai créé une connaissance candidate "
                "structurée, mais elle n'est ni confirmée ni réutilisable avant "
                "Tester et SECAU.",
                termine=True,
                candidate=candidate,
            )

        self.session["index"] = prochain
        self.session["clarifications"] = 0
        self.stockage.sauvegarder(self.session)
        resume = self._resume(reponse)
        return ResultatDialogue(
            prefixe
            + f"J'ai compris provisoirement : {resume}\n"
            + self._question_courante()
        )

    def _question_courante(self) -> str:
        assert self.session is not None
        index = int(self.session["index"])
        champ = self.CHAMPS[index]
        config = self.config["fields"][champ]
        return (
            f"Question {index + 1}/{len(self.CHAMPS)} : "
            f"{self._question_texte(champ)}\n"
            f"Réponds naturellement. {config['help']}\n"
            "J'attends ta réponse avant de continuer."
        )

    def _question_texte(self, champ: str) -> str:
        assert self.session is not None
        return Reflechir.questions_for(str(self.session["topic"]), (champ,))[0]

    @staticmethod
    def _resume(texte: str) -> str:
        compact = " ".join(texte.split())
        return compact[:157] + ("…" if len(compact) > 157 else "")

    @staticmethod
    def _distance_edition(a: str, b: str) -> int:
        precedent = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            courant = [i]
            for j, cb in enumerate(b, 1):
                courant.append(
                    min(courant[-1] + 1, precedent[j] + 1, precedent[j - 1] + (ca != cb))
                )
            precedent = courant
        return precedent[-1]

    def _proposer_correction(self, texte: str) -> tuple[str, str] | None:
        assert self.session is not None
        topic = cle(str(self.session["topic"]))
        for brut in re.findall(r"[a-zA-ZÀ-ÿ0-9_+#.-]+", texte):
            mot = cle(brut)
            if mot == topic or len(mot) < 4:
                continue
            proposition_verbe = self.connaissances.proposer_correction_verbe(mot)
            proposition_entite = self.connaissances.proposer_correction_entite(mot)
            corrige = (
                proposition_verbe[2]
                if proposition_verbe is not None
                else proposition_entite[0]
                if proposition_entite is not None
                else None
            )
            if corrige and self._distance_edition(mot, cle(corrige)) == 1:
                return brut, corrige
        return None

    def _mot_inconnu_isole(self, texte: str) -> str | None:
        assert self.session is not None
        connus = self.connaissances.vocabulaire_connu()
        connus.update(cle(x) for x in self.session["glossary"])
        connus.add(cle(str(self.session["topic"])))
        mots = [
            cle(mot)
            for mot in re.findall(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ'-]+", texte)
            if len(cle(mot)) >= 4
        ]
        inconnus = [mot for mot in mots if mot not in connus]
        connus_dans_phrase = sum(mot in connus for mot in mots)
        if len(inconnus) == 1 and connus_dans_phrase >= 2:
            return inconnus[0]
        return None

    def _route_candidate(self, texte: str) -> str | None:
        for mot in re.findall(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ'-]+", texte):
            entree = self.connaissances.trouver_mot_courant(mot)
            if entree and entree.get("route"):
                return str(entree["route"])
        return None

    def _evaluer(self, champ: str, reponse: str) -> tuple[bool, str]:
        mots = re.findall(r"\b[\wÀ-ÿ'-]+\b", reponse)
        minimum = int(self.config["fields"][champ]["minimum_words"])
        if len(mots) < minimum:
            return False, str(self.config["fields"][champ]["retry"])
        if champ == "examples":
            elements = [
                x.strip()
                for x in re.split(r"[,;\n]|\bet\b", reponse, flags=re.IGNORECASE)
                if x.strip()
            ]
            if len(elements) < 2:
                return False, str(self.config["fields"][champ]["retry"])
        return True, "réponse exploitable"
