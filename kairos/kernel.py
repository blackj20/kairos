"""Chef d'orchestre : analyse, décision et routage."""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable
from dataclasses import replace
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from .apprentissage_naturel import DialogueApprentissage
from .cognition import Reflechir
from .comprendre import Comprendre
from .connaissances import Connaissances
from .corrections import MemoireCorrections
from .decision import EvenementExperience, MoteurDecision
from .filtres_cognitifs import FiltresCognitifs
from .information import CapacitesInformation, FournisseurRecherche, WikipediaFR
from .memory import MemoryRepository
from .meta_comprehension import MetaComprehension
from .modeles import Analyse, Decision
from .relations_verbes import MemoireRelationsVerbes
from .repondre import Repondre
from .routing import PlanRoute, RouteurDynamique, StatutRoute
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
        routeur: RouteurDynamique | None = None,
        cognitive_repository: MemoryRepository | None = None,
        web_provider: FournisseurRecherche | None = None,
        allow_network: bool = False,
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
        self.filtres_cognitifs = FiltresCognitifs(self.soi.racine)
        self.moteur_decision = moteur_decision or MoteurDecision(
            comprendre=self.comprendre,
            persister=persister_decisions,
        )
        self.routeur = routeur or RouteurDynamique()
        self.meta_comprehension = MetaComprehension(self.soi)
        self._derniere_decision: Decision | None = None
        if cognitive_repository is None:
            racine = Path(__file__).resolve().parent.parent
            chemin_cognitif: str | Path = (
                racine / "memory" / "cognition.db"
                if persister_decisions
                else ":memory:"
            )
            self.cognitive_repository = MemoryRepository(chemin_cognitif)
            self._owns_cognitive_repository = True
        else:
            self.cognitive_repository = cognitive_repository
            self._owns_cognitive_repository = False
        fournisseur = web_provider
        if fournisseur is None and allow_network:
            fournisseur = WikipediaFR()
        self.information = CapacitesInformation(
            self.cognitive_repository,
            knowledge_base=self.repondre.knowledge_base,
            fournisseur_web=fournisseur,
        )
        self.information.enregistrer(self.routeur)
        racine = Path(__file__).resolve().parent.parent
        chemin_seance = (
            racine / "memory" / "learning_sessions.json"
            if persister_decisions
            else None
        )
        self.apprentissage = DialogueApprentissage(
            self.comprendre.connaissances,
            chemin=chemin_seance,
        )
        self._competences: dict[str, Competence] = {}
        self._dernier_plan_route: PlanRoute | None = None

    def enregistrer_competence(self, action: str, competence: Competence) -> None:
        """Associe un verbe canonique à une fonction d'exécution."""

        if not action.strip():
            raise ValueError("Une compétence doit avoir un nom d'action.")
        self._competences[action.casefold()] = competence

    def enregistrer_capacite(
        self,
        nom: str,
        capacite: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        permissions: tuple[str, ...] = (),
    ) -> None:
        """Enregistre une brique atomique explicitement autorisée."""

        self.routeur.enregistrer_capacite(
            nom, capacite, permissions=permissions
        )

    @property
    def attente_pedagogique(self) -> str | None:
        """Décrit l'aide du tour actif sans imposer un format artificiel."""

        return self.apprentissage.attente

    def traiter(
        self,
        requete: str,
        acteur: str = "creator",
    ) -> Decision:
        """Analyse la requête puis appelle un seul composant spécialisé."""

        if self.apprentissage.active:
            return self._traiter_reponse_pedagogique(requete)

        apprentissage_mot = re.match(
            r"^\s*apprends(?:-moi)?\s+(?:le\s+)?mot\s+(.+?)[?.!]*\s*$",
            requete,
            flags=re.IGNORECASE,
        )
        if apprentissage_mot:
            analyse = self._enrichir_analyse(self.comprendre.analyser(requete))
            topic = apprentissage_mot.group(1).strip()
            topic, correction = self._corriger_sujet_pedagogique(topic)
            reponse = self.apprentissage.demarrer(topic, correction=correction)
            return Decision(
                route="competence",
                analyse=analyse,
                reponse=reponse,
            )

        self._dernier_plan_route = None
        analyse = self._enrichir_analyse(self.comprendre.analyser(requete))
        reponse_meta = self.meta_comprehension.repondre(
            analyse,
            self._derniere_decision,
        )
        if reponse_meta is not None:
            return Decision(
                route=reponse_meta.route,
                analyse=analyse,
                reponse=reponse_meta.texte,
            )

        processus = self.moteur_decision.decider(analyse, acteur)
        verdict = processus.verdict
        route_interne = verdict.route.value
        # ETUDIER reste présenté comme une clarification tant que GrowUp ne
        # conduit pas encore automatiquement toute la consolidation.
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
        elif route == "refuser":
            raisons = "; ".join(
                str(raison)
                for raison in analyse.cognition.get("raisons", ())
            )
            reponse = (
                "Je refuse cette action : les filtres de sécurité ou "
                "d'autorisation détectent un conflit. "
                f"{raisons}"
            )
        elif verdict.question is not None:
            reponse = verdict.question.texte
        else:
            reponse = self.repondre.demander_clarification()

        decision = Decision(
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
            routage=(
                self._dernier_plan_route.vers_dict()
                if self._dernier_plan_route is not None
                else None
            ),
        )
        self._derniere_decision = decision
        return decision

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
        """Ajoute une relation seulement depuis des sources conformes.

        Une provenance locale explicite peut être unique. Dès qu'une URL est
        fournie, toutes les sources doivent être HTTPS et provenir d'au moins
        deux domaines distincts.
        """

        if acteur != "creator":
            raise PermissionError(
                "Seul le créateur peut confirmer une relation verbale."
            )
        sources_uniques = tuple(
            dict.fromkeys(source.strip() for source in sources if source.strip())
        )
        if not sources_uniques:
            raise ValueError("L'enseignement exige au moins une source.")

        analyses = tuple(urllib.parse.urlparse(source) for source in sources_uniques)
        contient_url = any(analyse.scheme or analyse.netloc for analyse in analyses)
        if contient_url:
            if any(
                analyse.scheme != "https" or not analyse.hostname
                for analyse in analyses
            ):
                raise ValueError(
                    "Les relations Internet exigent uniquement des URLs HTTPS valides."
                )
            domaines = {
                str(analyse.hostname).casefold()
                for analyse in analyses
                if analyse.hostname
            }
            if len(sources_uniques) < 2 or len(domaines) < 2:
                raise ValueError(
                    "Une relation Internet exige deux domaines HTTPS distincts."
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
            # Une seule question est visible. Les clarifications conservent
            # l'objectif parent et sont limitées par le schéma déclaratif.
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
            return self.apprentissage.demarrer(topic, correction=correction)

        if action == "donner":
            lesson = self.repondre.knowledge_base.find(
                analyse.texte_original
            )
            if lesson is not None:
                return self.repondre.knowledge_base.compose(lesson)

        competence = self._competences.get(action.casefold())
        if competence is not None:
            return competence(analyse)

        plan = self.routeur.planifier(action, analyse.cible.valeur)
        self._dernier_plan_route = plan
        if plan.id == "unresolved":
            return self.repondre.signaler_competence_absente(action)
        if plan.statut is StatutRoute.BLOCKED:
            manquantes = ", ".join(plan.capacites_manquantes)
            detail = (
                f" Capacités manquantes : {manquantes}."
                if manquantes
                else f" {plan.raison}."
            )
            return (
                f"Action « {action} » comprise et route « {plan.id} » "
                f"construite, mais bloquée.{detail}"
            )
        if plan.statut is StatutRoute.CANDIDATE:
            return (
                f"Route candidate « {plan.id} » composée pour « {action} ». "
                "Elle doit passer par Tester et SECAU avant toute exécution."
            )

        resultat = self.routeur.executer(plan, {"analyse": analyse})
        reponse = resultat.get("response")
        return str(reponse) if reponse else (
            f"Route « {plan.id} » exécutée avec succès."
        )

    def _corriger_sujet_pedagogique(self, topic: str) -> tuple[str, bool]:
        """Corrige une faute évidente avec le vocabulaire réellement connu."""

        candidats = tuple(sorted(self.comprendre.connaissances.vocabulaire_connu()))
        correspondance = get_close_matches(
            topic.casefold(),
            candidats,
            n=1,
            cutoff=0.86,
        )
        if correspondance and correspondance[0] != topic.casefold():
            return correspondance[0], True
        return topic, False

    def _traiter_reponse_pedagogique(self, requete: str) -> Decision:
        """Délègue le tour à la séance bornée puis reprend l'objectif parent."""

        analyse = self._enrichir_analyse(self.comprendre.analyser(requete))
        resultat = self.apprentissage.traiter(requete)
        return Decision(
            route="repondre",
            analyse=analyse,
            reponse=resultat.texte,
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

    def _enrichir_analyse(self, analyse: Analyse) -> Analyse:
        """Ajoute les filtres cognitifs sans altérer l'analyse linguistique."""

        profil = self.filtres_cognitifs.evaluer(analyse)
        return replace(analyse, cognition=profil.vers_dict())

    def close(self) -> None:
        """Ferme uniquement la mémoire cognitive créée par ce Kernel."""

        if self._owns_cognitive_repository:
            self.cognitive_repository.close()
