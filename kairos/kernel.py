"""Chef d'orchestre : analyse, décision et routage."""

from __future__ import annotations

import re
from difflib import get_close_matches
from collections.abc import Callable
from pathlib import Path

from .comprendre import Comprendre
from .cognition import Reflechir
from .connaissances import Connaissances
from .corrections import MemoireCorrections
from .decision import EvenementExperience, MoteurDecision
from .modeles import Analyse, Decision
from .repondre import Repondre
from .relations_verbes import MemoireRelationsVerbes
from .soi import ConnaissanceDeSoi

Competence = Callable[[Analyse], str]


class Kernel:
    """Coordonne les composants sans contenir de logique linguistique."""

    def __init__(
        self,
        comprendre: Comprendre | None = None,
        repondre: Repondre | None = None,
        soi: ConnaissanceDeSoi | None = None,
        moteur_decision: MoteurDecision | None = None,
        persister_decisions: bool = False,
    ) -> None:
        if comprendre is None:
            corrections = None
            if persister_decisions:
                racine = Path(__file__).resolve().parent.parent
                corrections = MemoireCorrections(
                    racine / "memory" / "corrections.json"
                )
                relations_verbes = MemoireRelationsVerbes(
                    racine / "memory" / "semantic_relations.json"
                )
            else:
                relations_verbes = None
            comprendre = Comprendre(
                connaissances=Connaissances(
                    corrections=corrections,
                    relations_verbes=relations_verbes,
                )
            )
        self.comprendre = comprendre
        self.repondre = repondre or Repondre(
            connaissances=self.comprendre.connaissances
        )
        self.soi = soi or ConnaissanceDeSoi()
        self.moteur_decision = moteur_decision or MoteurDecision(
            comprendre=self.comprendre,
            persister=persister_decisions,
        )
        self._competences: dict[str, Competence] = {}
        # Une séance pédagogique est volontairement locale à la conversation :
        # une question est posée, puis KAIROS attend et évalue sa réponse avant
        # de continuer. Les réponses ne deviennent jamais des vérités confirmées.
        self._session_pedagogique: dict[str, object] | None = None

    def enregistrer_competence(self, action: str, competence: Competence) -> None:
        """Associe un verbe canonique à une fonction d'exécution."""

        if not action.strip():
            raise ValueError("Une compétence doit avoir un nom d'action.")
        self._competences[action.casefold()] = competence

    @property
    def attente_pedagogique(self) -> str | None:
        """Décrit précisément le type de réponse attendu par la console."""

        if self._session_pedagogique is None:
            return None
        champs = tuple(self._session_pedagogique["champs"])
        index = int(self._session_pedagogique["index"])
        attentes = {
            "definition": "définition : une phrase d'au moins 5 mots",
            "examples": "3 exemples distincts, séparés par des virgules",
            "counterexamples": "contre-exemple expliqué en au moins 4 mots",
            "relations": "relations avec d'autres concepts, en au moins 4 mots",
        }
        return attentes[champs[index]]

    def traiter(
        self,
        requete: str,
        acteur: str = "creator",
    ) -> Decision:
        """Analyse la requête puis appelle un seul composant spécialisé."""

        if self._session_pedagogique is not None:
            return self._traiter_reponse_pedagogique(requete)

        analyse = self.comprendre.analyser(requete)
        processus = self.moteur_decision.decider(analyse, acteur)
        verdict = processus.verdict
        route_interne = verdict.route.value
        # Tant que GrowUp n'existe pas, ETUDIER produit extérieurement une
        # clarification tout en créant son événement d'apprentissage.
        route = (
            "clarification"
            if route_interne == "etudier"
            else route_interne
        )

        if route == "repondre":
            reponse = self.repondre.formuler(analyse)
        elif route == "competence":
            reponse = self._executer_competence(analyse)
        elif route == "controle":
            reponse = self.repondre.confirmer_interdiction(analyse)
        elif verdict.question is not None:
            reponse = verdict.question.texte
        else:
            reponse = self.repondre.demander_clarification()

        return Decision(
            route=route,
            analyse=analyse,
            reponse=reponse,
            question_id=(
                verdict.question.id if verdict.question is not None else None
            ),
            question=(
                verdict.question.texte
                if verdict.question is not None
                else None
            ),
            evaluation=processus.evaluation.vers_dict(),
            verdict=verdict.vers_dict(),
        )

    def repondre_a(
        self,
        question_id: str,
        reponse: str,
        acteur: str = "creator",
    ) -> EvenementExperience:
        """Lie une réponse à sa question sans confirmer une connaissance."""

        return self.moteur_decision.repondre_a(
            question_id,
            reponse,
            acteur,
        )

    def enseigner_relation_verbe(
        self,
        alias: str,
        cible: str,
        *,
        sources: tuple[str, ...],
        acteur: str = "creator",
    ) -> None:
        """Ajoute une équivalence depuis le créateur ou des sources vérifiées.

        Une relation Internet exige au moins deux références distinctes afin
        qu'une page isolée ne modifie jamais seule la compréhension.
        """

        if acteur != "creator":
            raise PermissionError(
                "Seul le créateur peut confirmer une relation verbale."
            )
        sources_uniques = tuple(dict.fromkeys(source.strip() for source in sources if source.strip()))
        if not sources_uniques:
            raise ValueError("L'enseignement exige au moins une source.")
        sources_internet = tuple(
            source
            for source in sources_uniques
            if source.startswith(("https://", "http://"))
        )
        if sources_internet and len(sources_internet) < 2:
            raise ValueError(
                "Une relation Internet exige au moins deux sources."
            )
        self.comprendre.connaissances.enseigner_relation_verbe(
            alias,
            cible,
            provenance=" | ".join(sources_uniques),
        )

    def _executer_competence(self, analyse: Analyse) -> str:
        action = analyse.action.valeur
        if action is None:
            return self.repondre.demander_clarification()

        if action == "poser":
            # Le dernier manque observé devient prioritaire ; sinon Kairos
            # questionne sa compréhension. Une seule question est exposée :
            # la suivante dépendra réellement de la réponse du client.
            events = self.moteur_decision.stockage.apprentissages()
            topic_match = re.search(
                r"\bsur\s+(.+?)(?:[?.!]|$)",
                analyse.texte_normalise,
            )
            topic = (
                topic_match.group(1).strip()
                if topic_match
                else (
                    events[-1].focus
                    if events and events[-1].focus
                    else "ma compréhension actuelle"
                )
            )
            topic, correction = self._corriger_sujet_pedagogique(topic)
            champs = ("definition", "examples", "counterexamples", "relations")
            self._session_pedagogique = {
                "topic": topic,
                "champs": champs,
                "index": 0,
                "reponses": {},
            }
            question = Reflechir.questions_for(topic, (champs[0],))[0]
            prefixe = (
                f"J'ai corrigé le sujet en « {topic} ». "
                if correction
                else ""
            )
            return (
                f"{prefixe}Question 1/{len(champs)} : {question}\n"
                f"Type de réponse attendu : {self.attente_pedagogique}.\n"
                "J'attends ta réponse avant de continuer."
            )

        if action == "donner":
            lesson = self.repondre.knowledge_base.find(
                analyse.texte_original
            )
            if lesson is not None:
                return self.repondre.knowledge_base.compose(lesson)

        competence = self._competences.get(action.casefold())
        if competence is None:
            return self.repondre.signaler_competence_absente(action)
        return competence(analyse)

    def _corriger_sujet_pedagogique(self, topic: str) -> tuple[str, bool]:
        """Corrige une faute évidente sans transformer un mot inconnu en certitude."""

        candidats = tuple(self.comprendre.connaissances.conversations["salutations"])
        correspondance = get_close_matches(
            topic.casefold(),
            candidats,
            n=1,
            cutoff=0.82,
        )
        if correspondance and correspondance[0] != topic.casefold():
            return correspondance[0], True
        return topic, False

    def _traiter_reponse_pedagogique(self, requete: str) -> Decision:
        """Évalue un tour pédagogique et pose au plus une question suivante."""

        analyse = self.comprendre.analyser(requete)
        session = self._session_pedagogique
        assert session is not None
        topic = str(session["topic"])
        champs = tuple(session["champs"])
        index = int(session["index"])
        champ = champs[index]
        reponse = requete.strip()

        if reponse.casefold() in {"annule", "annuler", "stop", "arrete", "arrête"}:
            self._session_pedagogique = None
            texte = "Séance arrêtée. Aucune réponse n'a été confirmée comme connaissance."
        else:
            valide, conseil = self._evaluer_reponse_pedagogique(
                champ,
                reponse,
                topic,
            )
            question = Reflechir.questions_for(topic, (champ,))[0]
            if not valide:
                texte = (
                    f"Réponse à améliorer : {conseil}\n"
                    f"Je garde la même question : {question}"
                )
            else:
                reponses = dict(session["reponses"])
                reponses[champ] = reponse
                proposition = reponse[0].upper() + reponse[1:]
                if proposition[-1] not in ".!?":
                    proposition += "."
                prochain_index = index + 1
                if prochain_index == len(champs):
                    self._session_pedagogique = None
                    texte = (
                        f"Réponse acceptée. Proposition corrigée : {proposition}\n"
                        "Séance terminée : les quatre réponses ont été évaluées "
                        "pendant cette séance. Elles ne sont pas transformées "
                        "en connaissances confirmées."
                    )
                else:
                    session["index"] = prochain_index
                    session["reponses"] = reponses
                    prochain_champ = champs[prochain_index]
                    prochaine = Reflechir.questions_for(
                        topic,
                        (prochain_champ,),
                    )[0]
                    texte = (
                        f"Réponse acceptée. Proposition corrigée : {proposition}\n"
                        f"Question {prochain_index + 1}/{len(champs)} : {prochaine}\n"
                        f"Type de réponse attendu : {self.attente_pedagogique}.\n"
                        "J'attends ta réponse avant de continuer."
                    )

        return Decision(
            route="repondre",
            analyse=analyse,
            reponse=texte,
        )

    @staticmethod
    def _evaluer_reponse_pedagogique(
        champ: str,
        reponse: str,
        topic: str,
    ) -> tuple[bool, str]:
        """Vérifie la forme attendue sans prétendre connaître le fond."""

        mots = re.findall(r"\b[\wÀ-ÿ'-]+\b", reponse)
        if champ == "definition" and len(mots) < 5:
            return False, (
                f"donne une phrase d'au moins cinq mots qui explique « {topic} »"
            )
        if champ == "examples":
            elements = [
                element.strip()
                for element in re.split(r"[,;\n]|\bet\b", reponse, flags=re.IGNORECASE)
                if element.strip()
            ]
            if len(elements) < 3:
                return False, "donne trois exemples distincts, séparés par des virgules"
        if champ in {"counterexamples", "relations"} and len(mots) < 4:
            return False, "développe la réponse avec au moins quatre mots"
        return True, "réponse exploitable"
