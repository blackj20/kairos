"""Cycle interne unifié, observable et hors ligne par défaut."""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..memory import MemoryRepository
from ..self_correction import SelfCorrectionLab
from .modeles import (
    QuestionInterne,
    RapportCycleInterne,
    TacheInterne,
    TypeTravail,
)


def _run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"internal_{stamp}_{uuid.uuid4().hex[:8]}"


def _normaliser(texte: str) -> str:
    return " ".join(texte.casefold().replace("’", "'").split())


class MoteurInterne:
    """Transforme l'état cognitif existant en un prochain travail explicable.

    Le moteur ne fabrique aucune preuve et ne promeut rien en production. Il
    exploite d'abord la mémoire locale, lance le laboratoire SECAU lorsqu'un
    contrat Tester existe, puis prépare au maximum une question humaine.
    """

    GAINS = {
        "relation": 40,
        "examples": 25,
        "counterexamples": 20,
        "source": 15,
    }
    STOPWORDS = {
        "avec",
        "dans",
        "pour",
        "sans",
        "plus",
        "moins",
        "comme",
        "cette",
        "cela",
        "elle",
        "elles",
        "nous",
        "vous",
        "leur",
        "leurs",
        "mais",
        "donc",
        "ainsi",
        "tout",
        "tous",
        "être",
        "avoir",
        "faire",
    }
    DEFAULT_CONFIG: dict[str, Any] = {
        "mode": "offline_first",
        "max_candidates": 32,
        "max_seconds": 12,
        "run_lab": True,
        "ask_one_question": True,
        "network": False,
        "production_promotion": False,
    }

    def __init__(
        self,
        racine: Path | None = None,
        *,
        repository: MemoryRepository | None = None,
        lab_factory: Callable[[Path], Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.racine = racine or Path(__file__).resolve().parents[2]
        self.memoire = self.racine / "memory"
        self.memoire.mkdir(parents=True, exist_ok=True)
        self.repository_path = self.memoire / "cognition.db"
        self.config = dict(config or self._lire_config())
        self._valider_config()
        self.repository = repository or MemoryRepository(self.repository_path)
        self._owns_repository = repository is None
        self.lab_factory = lab_factory or (lambda root: SelfCorrectionLab(root))

    @property
    def dossier(self) -> Path:
        return self.memoire / "internal_runs"

    def run(self) -> RapportCycleInterne:
        """Exécute un cycle utile, synchrone et reproductible."""

        self.dossier.mkdir(parents=True, exist_ok=True)
        run_id = _run_id()
        report_path = self.dossier / f"{run_id}.json"
        started = time.monotonic()
        avant = self.repository.cognitive_counts()
        candidats = self.repository.candidate_hypotheses()[
            : int(self.config["max_candidates"])
        ]

        enrichis: list[dict[str, Any]] = []
        for candidat in candidats:
            payload = dict(candidat.get("payload") or {})
            contexte = self._contexte_local(payload)
            if contexte and payload.get("internal_context") != list(contexte):
                payload["internal_context"] = list(contexte)
                self.repository.update_hypothesis_payload(
                    str(candidat["id"]),
                    payload,
                    event="INTERNAL_CONTEXT_MINED",
                )
            enrichis.append({**candidat, "payload": payload})

        taches = tuple(
            sorted(
                (self._classer(item) for item in enrichis),
                key=lambda item: (-item.priorite, item.hypothesis_id),
            )
        )
        laboratoire: dict[str, Any] | None = None
        executees = 0

        if (
            any(item.type is TypeTravail.REVUE_LOCALE for item in taches)
            and bool(self.config["run_lab"])
            and time.monotonic() - started < float(self.config["max_seconds"])
        ):
            resultat = self.lab_factory(self.racine).run(
                source_path=self.repository_path
            )
            laboratoire = (
                resultat.vers_dict()
                if hasattr(resultat, "vers_dict")
                else dict(resultat)
            )
            executees += 1

        question: QuestionInterne | None = None
        questions = [
            item for item in taches
            if item.type is TypeTravail.QUESTION_HUMAINE
        ]
        if (
            questions
            and bool(self.config["ask_one_question"])
            and time.monotonic() - started < float(self.config["max_seconds"])
        ):
            meilleure = questions[0]
            candidat = next(
                item for item in enrichis
                if str(item["id"]) == meilleure.hypothesis_id
            )
            question = self._preparer_question(candidat, meilleure)
            executees += 1

        apres = self.repository.cognitive_counts()
        production_changee = (
            self._projection_connaissance(avant)
            != self._projection_connaissance(apres)
        )
        if not taches:
            etat, arret = "sleeping", "no_internal_work"
        elif question is not None:
            etat, arret = "waiting_human", "best_question_selected"
        elif laboratoire is not None:
            etat, arret = "worked", "laboratory_completed"
        else:
            etat, arret = "blocked", "no_executable_contract"

        rapport = RapportCycleInterne(
            run_id=run_id,
            etat=etat,
            cycles=1 if taches else 0,
            candidats_vus=len(candidats),
            taches_executees=executees,
            taches=taches,
            question=question,
            laboratoire=laboratoire,
            avant=avant,
            apres=apres,
            connaissances_production_modifiees=production_changee,
            reseau_utilise=False,
            ratio_hors_ligne=1.0,
            arret=arret,
            report_path=str(report_path),
        )
        payload = rapport.vers_dict()
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.dossier / "latest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.repository.record_audit(
            "INTERNAL_ENGINE_COMPLETED",
            {
                "run": run_id,
                "state": etat,
                "candidates": len(candidats),
                "executed": executees,
                "network_used": False,
                "production_knowledge_changed": production_changee,
            },
        )
        return rapport

    def status(self) -> dict[str, Any]:
        latest = self.dossier / "latest.json"
        if not latest.exists():
            return {
                "etat": "never_run",
                "mode": self.config["mode"],
                "reseau_utilise": False,
                "ratio_hors_ligne": 1.0,
            }
        return json.loads(latest.read_text(encoding="utf-8"))

    @staticmethod
    def off() -> dict[str, Any]:
        return {
            "etat": "idle",
            "background_process": False,
            "detail": "Le moteur interne est synchrone : aucun daemon ne tourne.",
        }

    @staticmethod
    def parse_command(message: str) -> str | None:
        normalise = "".join(message.casefold().split())
        aliases = {
            "internal-engine=on": "on",
            "internal-engine=off": "off",
            "internal-engine=status": "status",
            "moteur-interne=on": "on",
            "moteur-interne=off": "off",
            "moteur-interne=statut": "status",
            "growup=on": "on",
        }
        return aliases.get(normalise)

    def _classer(self, candidat: dict[str, Any]) -> TacheInterne:
        hypothesis_id = str(candidat["id"])
        payload = dict(candidat.get("payload") or {})
        nom = str(payload.get("name") or hypothesis_id)
        score = max(0, min(100, int(candidat.get("score", 0))))
        contexte = tuple(payload.get("internal_context") or ())
        if self._a_contrat_tester(hypothesis_id, payload):
            return TacheInterne(
                hypothesis_id,
                nom,
                TypeTravail.REVUE_LOCALE,
                min(200, 100 + score),
                "un contrat Tester ou un rapport local permet une revue SECAU",
                True,
                contexte_local=contexte,
            )

        manques = tuple(self._champs_manquants(payload))
        if manques:
            gain = max(self.GAINS[item] for item in manques)
            return TacheInterne(
                hypothesis_id,
                nom,
                TypeTravail.QUESTION_HUMAINE,
                min(150, 50 + gain + score // 5),
                "la meilleure question réduit un manque structurel précis",
                True,
                manques=manques,
                contexte_local=contexte,
            )

        return TacheInterne(
            hypothesis_id,
            nom,
            TypeTravail.BLOQUE,
            score,
            "aucun contrat Tester et aucun manque humain exploitable",
            False,
            contexte_local=contexte,
        )

    def _a_contrat_tester(
        self,
        hypothesis_id: str,
        payload: dict[str, Any],
    ) -> bool:
        if payload.get("research_kind") == "information.search":
            return True
        if payload.get("causal_kind") == "behavior.change":
            return True
        return self.repository.latest_report_for(hypothesis_id) is not None

    def _champs_manquants(self, payload: dict[str, Any]) -> list[str]:
        session = payload.get("active_learning")
        ignores = (
            set(session.get("skipped_fields", []))
            if isinstance(session, dict)
            else set()
        )
        restants: list[str] = []
        if (
            not payload.get("relation_candidate")
            and not payload.get("relation_candidates")
            and "relation" not in ignores
        ):
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

    def _preparer_question(
        self,
        candidat: dict[str, Any],
        tache: TacheInterne,
    ) -> QuestionInterne:
        payload = dict(candidat.get("payload") or {})
        session = dict(payload.get("active_learning") or {})
        pending = str(session.get("pending_field") or "")
        champ = pending or max(tache.manques, key=lambda item: self.GAINS[item])
        question = QuestionInterne(
            hypothesis_id=tache.hypothesis_id,
            champ=champ,
            texte=self._texte_question(champ, tache),
            gain_attendu=self.GAINS[champ],
            raison=self._raison_question(champ),
        )
        if not pending:
            questions = list(session.get("questions", []))
            questions.append(
                {
                    "field": champ,
                    "gain": question.gain_attendu,
                    "reason": question.raison,
                    "selected_by": "internal_engine",
                }
            )
            session.update(
                {
                    "status": "needs_human_input",
                    "pending_field": champ,
                    "questions": questions,
                }
            )
            payload["active_learning"] = session
            payload["next_action"] = "await_creator"
            self.repository.update_hypothesis_payload(
                tache.hypothesis_id,
                payload,
                event="INTERNAL_QUESTION_SELECTED",
            )
        return question

    def _texte_question(self, champ: str, tache: TacheInterne) -> str:
        nom = tache.nom
        if champ == "relation":
            voisins = [
                str(item.get("label"))
                for item in tache.contexte_local[:3]
                if item.get("label")
            ]
            contexte = (
                " Ma mémoire locale contient : "
                + ", ".join(voisins)
                + ". Tu peux répondre « aucun » si ces pistes sont mauvaises."
                if voisins
                else ""
            )
            return (
                f"Quelle relation principale relie « {nom} » à un concept ? "
                "Réponds sous la forme « c'est un… », « signifie… » ou « sert à… »."
                + contexte
            )
        if champ == "examples":
            return f"Donne trois exemples différents où « {nom} » est utilisé correctement."
        if champ == "counterexamples":
            return (
                f"Donne deux cas proches qui ne doivent pas être classés comme « {nom} »."
            )
        return (
            f"Quelle source locale, documentation ou référence vérifiable peut soutenir « {nom} » ?"
        )

    @staticmethod
    def _raison_question(champ: str) -> str:
        raisons = {
            "relation": "une relation réduit le plus fortement l'ambiguïté du concept",
            "examples": "les exemples testent les usages positifs",
            "counterexamples": "les contre-exemples fixent les limites de la règle",
            "source": "une piste vérifiable est nécessaire avant Tester et SECAU",
        }
        return raisons[champ]

    def _contexte_local(self, payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        connection = getattr(self.repository, "connection", None)
        if connection is None:
            return ()
        texte = " ".join(
            str(item)
            for item in (
                payload.get("name", ""),
                payload.get("definition", ""),
                *[
                    relation.get("target", "")
                    for relation in payload.get("relation_candidates", [])
                    if isinstance(relation, dict)
                ],
            )
        )
        tokens = self._tokens(texte)
        if not tokens:
            return ()
        suggestions: list[dict[str, Any]] = []
        try:
            concepts = connection.execute(
                "SELECT id, name, domain, definition FROM concepts "
                "WHERE status='confirmed' ORDER BY mastery_score DESC, name LIMIT 250"
            )
            for row in concepts:
                label = str(row["name"])
                score = self._recouvrement(
                    tokens,
                    self._tokens(label + " " + str(row["definition"] or "")),
                )
                if (
                    score > 0
                    and _normaliser(label)
                    != _normaliser(str(payload.get("name", "")))
                ):
                    suggestions.append(
                        {
                            "kind": "concept",
                            "ref": f"concept:{row['id']}",
                            "label": label,
                            "score": score,
                            "domain": str(row["domain"]),
                        }
                    )
            relations = connection.execute(
                "SELECT id, source, relation_type, target FROM semantic_relations "
                "WHERE status='confirmed' ORDER BY mastery_score DESC LIMIT 250"
            )
            for row in relations:
                label = f"{row['source']} {row['relation_type']} {row['target']}"
                score = self._recouvrement(tokens, self._tokens(label))
                if score > 0:
                    suggestions.append(
                        {
                            "kind": "relation",
                            "ref": f"relation:{row['id']}",
                            "label": label,
                            "score": score,
                        }
                    )
        except Exception:
            return ()
        suggestions.sort(
            key=lambda item: (-int(item["score"]), str(item["ref"]))
        )
        return tuple(suggestions[:5])

    @classmethod
    def _tokens(cls, texte: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-ZÀ-ÿ0-9_+#'-]+", _normaliser(texte))
            if len(token) >= 4 and token not in cls.STOPWORDS
        }

    @staticmethod
    def _recouvrement(gauche: set[str], droite: set[str]) -> int:
        if not gauche or not droite:
            return 0
        communs = gauche & droite
        return int(round(100 * len(communs) / max(1, len(gauche))))

    @staticmethod
    def _projection_connaissance(compteurs: dict[str, int]) -> dict[str, int]:
        cles = {
            "promoted_hypotheses",
            "rejected_hypotheses",
            "concepts",
            "relations",
            "quarantined_relations",
        }
        return {key: int(compteurs.get(key, 0)) for key in sorted(cles)}

    def _lire_config(self) -> dict[str, Any]:
        path = self.racine / "data" / "cognition" / "internal_engine.json"
        if not path.exists():
            return dict(self.DEFAULT_CONFIG)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Configuration moteur interne invalide : {path}"
            ) from error
        return {**self.DEFAULT_CONFIG, **loaded}

    def _valider_config(self) -> None:
        if self.config.get("network") is not False:
            raise ValueError("Le moteur interne V0.18 doit rester hors ligne.")
        if self.config.get("production_promotion") is not False:
            raise ValueError("La promotion autonome en production est interdite.")
        if int(self.config.get("max_candidates", 0)) <= 0:
            raise ValueError("max_candidates doit être positif.")
        if float(self.config.get("max_seconds", 0)) <= 0:
            raise ValueError("max_seconds doit être positif.")

    def close(self) -> None:
        if self._owns_repository:
            self.repository.close()
