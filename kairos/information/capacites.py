"""Capacités atomiques de la route ``information.search``."""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
import uuid
from typing import Any

from ..knowledge_base import KnowledgeBase
from ..memory import MemoryRepository
from ..routing import RouteurDynamique
from .modeles import SourceInformation
from .providers import ErreurRechercheWeb, FournisseurRecherche


def _mots(texte: str) -> set[str]:
    normalise = unicodedata.normalize("NFKD", texte.casefold())
    normalise = "".join(
        caractere
        for caractere in normalise
        if not unicodedata.combining(caractere)
    )
    return {
        mot
        for mot in re.findall(r"[a-z0-9]{3,}", normalise)
        if mot not in {"avec", "dans", "pour", "plus", "une", "des", "les"}
    }


class CapacitesInformation:
    """Lie recherche, comparaison, candidature et réponse au routeur."""

    def __init__(
        self,
        repository: MemoryRepository,
        *,
        knowledge_base: KnowledgeBase | None = None,
        fournisseur_web: FournisseurRecherche | None = None,
    ) -> None:
        self.repository = repository
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.fournisseur_web = fournisseur_web

    def enregistrer(self, routeur: RouteurDynamique) -> None:
        routeur.enregistrer_capacite(
            "memory.search",
            self.rechercher_memoire,
            permissions=("memory.read",),
        )
        if self.fournisseur_web is not None:
            routeur.enregistrer_capacite(
                "web.search",
                self.rechercher_web,
                permissions=("network.read",),
            )
        routeur.enregistrer_capacite("sources.compare", self.comparer_sources)
        routeur.enregistrer_capacite(
            "knowledge.propose",
            self.proposer_connaissance,
            permissions=("memory.candidate.write",),
        )
        routeur.enregistrer_capacite("response.explain", self.expliquer)

    @staticmethod
    def _cible(contexte: dict[str, Any]) -> str:
        return str(contexte.get("target") or "").strip()

    def rechercher_memoire(
        self, contexte: dict[str, Any]
    ) -> dict[str, Any]:
        cible = self._cible(contexte)
        sources: list[dict[str, Any]] = []
        lecon = self.knowledge_base.find(cible)
        if lecon is not None:
            sources.append(
                SourceInformation(
                    titre=str(lecon.get("topic") or cible),
                    url=str((lecon.get("sources") or ["memory://core"])[0]),
                    extrait=str(lecon["answer"]),
                    type_source="memoire_confirmee",
                    confiance=100,
                ).vers_dict()
            )
        for concept in self.repository.search({"text": cible}):
            sources.append(
                SourceInformation(
                    titre=str(concept["name"]),
                    url=f"memory://concept/{concept['id']}",
                    extrait=str(concept.get("definition") or ""),
                    type_source="memoire_confirmee",
                    confiance=int(concept.get("mastery_score", 100)),
                ).vers_dict()
            )
        return {"memory_sources": sources, "memory_hit": bool(sources)}

    def rechercher_web(
        self, contexte: dict[str, Any]
    ) -> dict[str, Any]:
        if self.fournisseur_web is None:
            return {"web_sources": [], "web_error": "réseau non autorisé"}
        try:
            sources = self.fournisseur_web.rechercher(
                self._cible(contexte), limite=3
            )
        except ErreurRechercheWeb as erreur:
            return {"web_sources": [], "web_error": str(erreur)}
        return {
            "web_sources": [source.vers_dict() for source in sources],
            "web_error": None,
        }

    def comparer_sources(
        self, contexte: dict[str, Any]
    ) -> dict[str, Any]:
        sources = [
            *contexte.get("memory_sources", []),
            *contexte.get("web_sources", []),
        ]
        domaines = {
            str(urllib.parse.urlparse(str(source.get("url", ""))).hostname).casefold()
            for source in sources
            if urllib.parse.urlparse(str(source.get("url", ""))).hostname
        }
        ensembles = [_mots(str(source.get("extrait", ""))) for source in sources]
        recouvrements: list[float] = []
        for index, gauche in enumerate(ensembles):
            for droite in ensembles[index + 1:]:
                union = gauche | droite
                if union:
                    recouvrements.append(len(gauche & droite) / len(union))
        accord = (
            round(100 * sum(recouvrements) / len(recouvrements))
            if recouvrements
            else (100 if contexte.get("memory_hit") else 0)
        )
        return {
            "comparison": {
                "source_count": len(sources),
                "independent_domains": len(domaines),
                "agreement_score": accord,
                "enough_for_tests": (
                    bool(contexte.get("memory_hit")) or len(domaines) >= 2
                ),
            }
        }

    def proposer_connaissance(
        self, contexte: dict[str, Any]
    ) -> dict[str, Any]:
        cible = self._cible(contexte)
        if contexte.get("memory_hit"):
            return {
                "candidate_id": None,
                "candidate_status": "already_confirmed",
                "secau_status": "not_needed",
            }
        sources = list(contexte.get("web_sources", []))
        if not sources:
            return {
                "candidate_id": None,
                "candidate_status": "no_evidence",
                "secau_status": "not_reviewed",
            }
        existante = self.repository.candidate_for(cible)
        if existante is not None:
            return {
                "candidate_id": str(existante["id"]),
                "candidate_status": "candidate",
                "candidate_reused": True,
                "secau_status": "waiting_for_tests",
            }
        preuves = [
            self.repository.add_evidence(
                "web",
                str(source["url"]),
                str(source["extrait"]),
                int(source.get("confiance", 50)),
            )
            for source in sources
        ]
        comparaison = dict(contexte.get("comparison", {}))
        score = min(
            85,
            35
            + 15 * int(comparaison.get("independent_domains", 0))
            + int(comparaison.get("agreement_score", 0)) // 4,
        )
        recherche_id = f"research_{uuid.uuid4().hex}"
        candidate_id = self.repository.add_hypothesis(
            {
                "created_from_experience_id": recherche_id,
                "name": cible,
                "domain": "general",
                "definition": str(sources[0]["extrait"]),
                "evidence_ids": preuves,
                "source_urls": [str(source["url"]) for source in sources],
                "source_claims": [
                    str(source["extrait"]) for source in sources
                ],
                "source_domains": sorted(
                    {
                        str(
                            urllib.parse.urlparse(
                                str(source["url"])
                            ).hostname
                        ).casefold()
                        for source in sources
                        if urllib.parse.urlparse(
                            str(source["url"])
                        ).hostname
                    }
                ),
                "comparison": comparaison,
                "research_kind": "information.search",
                "score": score,
            }
        )
        self.repository.record_audit(
            "RESEARCH_CANDIDATE_CREATED",
            {
                "research": recherche_id,
                "hypothesis": candidate_id,
                "target": cible,
                "evidence_count": len(preuves),
                "secau": "waiting_for_tests",
            },
        )
        return {
            "candidate_id": candidate_id,
            "candidate_status": "candidate",
            "candidate_reused": False,
            "secau_status": "waiting_for_tests",
        }

    def expliquer(self, contexte: dict[str, Any]) -> dict[str, Any]:
        cible = self._cible(contexte)
        memoire = list(contexte.get("memory_sources", []))
        web = list(contexte.get("web_sources", []))
        if memoire:
            source = memoire[0]
            return {
                "response": (
                    f"{source['extrait']} Source confirmée : {source['url']}"
                )
            }
        if web:
            source = web[0]
            urls = ", ".join(str(item["url"]) for item in web)
            candidate_id = contexte.get("candidate_id")
            return {
                "response": (
                    f"Résultat de recherche sur « {cible} » : "
                    f"{source['extrait']} Sources consultées : {urls}. "
                    f"Mémoire : hypothèse candidate {candidate_id}; "
                    "SECAU attend les tests, cette information n'est pas "
                    "encore une connaissance confirmée."
                )
            }
        erreur = contexte.get("web_error")
        detail = f" Détail : {erreur}." if erreur else ""
        return {
            "response": (
                f"Aucune connaissance confirmée trouvée sur « {cible} »."
                f"{detail} Autorise une recherche externe avec --online."
            )
        }
