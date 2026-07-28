"""Liaison contrôlée entre une question en attente et sa réponse."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from .modeles import EvenementExperience
from .stockage import StockageDecision
from ..comprendre import Comprendre


class Experience:
    """Enregistre un épisode sans promouvoir de connaissance."""

    def __init__(
        self,
        stockage: StockageDecision,
        comprendre: Comprendre,
    ) -> None:
        self.stockage = stockage
        self.comprendre = comprendre

    def enregistrer_reponse(
        self,
        question_id: str,
        reponse: str,
        acteur: str = "creator",
    ) -> EvenementExperience:
        if not reponse.strip():
            raise ValueError("Une réponse vide ne peut pas devenir une expérience.")

        question = self.stockage.obtenir_question(question_id)
        if question is None:
            raise KeyError(f"Question inconnue : {question_id}")
        if question.statut != "waiting_answer":
            raise ValueError("Cette question n'attend plus de réponse.")

        analyse = self.comprendre.analyser(reponse)
        resolution = self._resoudre_champ(
            question.champ_manquant,
            reponse,
            analyse,
        )
        # Une réponse positive à une confirmation est le seul passage qui
        # transforme les ressemblances orthographiques en relations réutilisables.
        if (
            question.champ_manquant == "confirmation"
            and resolution.get("value") is True
        ):
            relations = (
                self.comprendre.connaissances.confirmer_corrections_de(
                    question.requete_originale
                )
            )
            if relations:
                resolution["learned_relations"] = relations
        # Une explication courte du créateur peut relier un mot inconnu à un
        # verbe canonique. L'épisode reste conservé, mais la relation est
        # immédiatement réutilisable car sa source est explicitement le créateur.
        if question.champ_manquant == "sens" and acteur == "creator":
            relation = self._apprendre_relation_verbe(question, reponse, analyse)
            if relation is not None:
                resolution["learned_semantic_relation"] = relation
        maintenant = datetime.now(timezone.utc).isoformat()
        question_resolue = replace(
            question,
            statut="answered",
            reponse=reponse,
            resolue_le=maintenant,
        )
        self.stockage.mettre_a_jour_question(question_resolue)

        evenement = EvenementExperience(
            id=f"experience_{uuid4().hex}",
            question_id=question.id,
            requete_originale=question.requete_originale,
            question=question.texte,
            reponse=reponse,
            champ=question.champ_manquant,
            resolution=resolution,
            analyse_reponse=analyse.vers_dict(),
            statut="recorded_not_confirmed",
            cree_le=maintenant,
        )
        self.stockage.sauvegarder_experience(evenement)
        return evenement

    def _apprendre_relation_verbe(
        self,
        question,
        reponse: str,
        analyse,
    ) -> dict[str, str] | None:
        """Relie le mot inconnu à un verbe connu cité dans la réponse."""

        inconnus = question.analyse.get("jetons_inconnus", [])
        if not inconnus:
            return None
        alias = str(inconnus[-1])
        cible = None
        for jeton in analyse.decoupage.mots if analyse.decoupage else ():
            verbe = self.comprendre.connaissances.trouver_verbe(jeton.normalise)
            if verbe is not None:
                cible = verbe[0]
                break
        if cible is None or alias == cible:
            return None
        provenance = f"creator_answer:{question.id}"
        self.comprendre.connaissances.enseigner_relation_verbe(
            alias,
            cible,
            provenance,
        )
        return {
            "source": alias,
            "relation": "equivalent_appris",
            "target": cible,
            "provenance": provenance,
        }

    def _resoudre_champ(
        self,
        champ: str,
        reponse: str,
        analyse,
    ) -> dict[str, object]:
        if champ == "cible":
            for jeton in analyse.decoupage.mots if analyse.decoupage else ():
                entite = self.comprendre.connaissances.trouver_entite(
                    jeton.normalise
                )
                if entite:
                    valeur, categorie = entite
                    return {
                        "field": "cible",
                        "value": valeur,
                        "score": 100,
                        "category": categorie,
                    }
            return {
                "field": "cible",
                "value": reponse.strip(),
                "score": 60,
                "status": "hypothesis",
            }

        if champ == "action":
            if analyse.action.valeur:
                return {
                    "field": "action",
                    "value": analyse.action.valeur,
                    "score": analyse.action.score,
                }
            for jeton in analyse.decoupage.mots if analyse.decoupage else ():
                verbe = self.comprendre.connaissances.trouver_verbe(
                    jeton.normalise
                )
                if verbe:
                    return {
                        "field": "action",
                        "value": verbe[0],
                        "score": 80,
                    }

        if champ == "type_requete":
            return {
                "field": "type_requete",
                "value": analyse.type_requete.valeur,
                "score": analyse.type_requete.score,
            }

        if champ == "confirmation":
            valeur = analyse.texte_normalise.casefold()
            positive = valeur in {
                "exact",
                "exactement",
                "oui",
                "ouais",
            }
            return {
                "field": "confirmation",
                "value": positive,
                "raw": reponse.strip(),
                "score": 100 if positive else 60,
            }

        return {
            "field": champ,
            "value": reponse.strip(),
            "score": 60,
            "status": "hypothesis",
        }
