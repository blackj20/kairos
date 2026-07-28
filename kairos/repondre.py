"""Formulation de réponses sans responsabilité de classification."""

from __future__ import annotations

import re
import unicodedata

from .connaissances import Connaissances
from .knowledge_base import KnowledgeBase
from .modeles import Analyse
from .soi import ConnaissanceDeSoi


class Repondre:
    """Produit une réponse simple à partir d'une analyse déjà effectuée."""

    def __init__(
        self,
        connaissances: Connaissances | None = None,
        knowledge_base: KnowledgeBase | None = None,
        soi: ConnaissanceDeSoi | None = None,
    ) -> None:
        self.connaissances = connaissances or Connaissances()
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.soi = soi or ConnaissanceDeSoi()

    @staticmethod
    def _sans_accents(texte: str) -> str:
        decompose = unicodedata.normalize("NFKD", texte)
        return "".join(
            caractere
            for caractere in decompose
            if not unicodedata.combining(caractere)
        )

    def _repondre_sur_soi(self, texte: str) -> str | None:
        """Répond depuis les fichiers protégés de ``self/``, jamais par invention."""

        normalise = self._sans_accents(texte).casefold()
        normalise = re.sub(r"[^\w\s'-]", " ", normalise)
        normalise = re.sub(r"\s+", " ", normalise).strip()

        identite = (
            "qui es tu",
            "qui es-tu",
            "quel est ton nom",
            "comment tu t appelles",
            "comment t appelles tu",
        )
        if any(indice in normalise for indice in identite):
            donnees = self.soi.identity
            return (
                f"Je suis {donnees['name']} — {donnees['full_name']}. "
                f"Je suis un {donnees['nature']}. Version déclarée : "
                f"{donnees['version']}."
            )

        objectifs = (
            "ton objectif",
            "ta mission",
            "ton but",
            "objectif actuel",
            "objectif courant",
        )
        if any(indice in normalise for indice in objectifs):
            donnees = self.soi.objective
            return (
                f"Mon objectif courant est de {donnees['current']}. "
                f"Priorité : {donnees['priority']}. Statut : {donnees['status']}."
            )

        maison = (
            "ou est ta maison",
            "ou habites tu",
            "ton dossier racine",
            "ta racine",
        )
        if any(indice in normalise for indice in maison):
            donnees = self.soi.home
            return (
                f"Ma racine est « {donnees['root']} ». Ma mémoire évolutive se "
                f"trouve dans « {donnees['memory']} » et mes connaissances sur "
                f"moi-même dans « {donnees['self']} »."
            )

        capacites = (
            "que sais tu faire",
            "tes capacites",
            "tes competences",
        )
        if any(indice in normalise for indice in capacites):
            donnees = self.soi.capabilities
            declarees = "; ".join(str(item) for item in donnees["declared"])
            return f"Mes capacités déclarées sont : {declarees}."

        limites = (
            "tes limites",
            "que ne peux tu pas faire",
            "quelles sont tes limites",
        )
        if any(indice in normalise for indice in limites):
            donnees = self.soi.limits
            connues = "; ".join(str(item) for item in donnees["known"])
            return f"Mes limites connues sont : {connues}."

        createur = (
            "qui est ton createur",
            "qui t a cree",
            "ton createur",
        )
        if any(indice in normalise for indice in createur):
            donnees = self.soi.creator
            return f"Mon créateur déclaré est {donnees['name']}."

        return None

    def formuler(self, analyse: Analyse) -> str:
        reponse_soi = self._repondre_sur_soi(analyse.texte_normalise)
        if reponse_soi is not None:
            return reponse_soi

        lesson = self.knowledge_base.find(analyse.texte_original)
        if lesson is not None:
            return self.knowledge_base.compose(lesson)
        conversations = self.connaissances.conversations
        reponses = conversations["reponses"]
        texte = self._sans_accents(analyse.texte_normalise)
        salutations = conversations["salutations"]
        questions_etat = [
            self._sans_accents(element)
            for element in conversations["questions_etat"]
        ]

        salutation = any(
            mot in analyse.texte_normalise.split() for mot in salutations
        )
        etat = any(expression in texte for expression in questions_etat)

        if salutation and etat:
            return str(reponses["salutation_etat"])
        if salutation:
            return str(reponses["salutation"])
        if etat:
            return str(reponses["question_etat"])
        # Une connaissance absente ne doit produire ni invention ni impasse.
        # KAIROS rend plutôt la recherche reproductible pour que le client (ou
        # une future compétence Internet) puisse trouver puis vérifier la réponse.
        if analyse.type_requete.valeur in {"question", "lecon"}:
            return self.guider_recherche(analyse)
        return str(reponses["incompris"])

    def guider_recherche(self, analyse: Analyse) -> str:
        """Propose comment trouver une connaissance absente sans la fabriquer."""

        sujet = analyse.cible.valeur or analyse.texte_normalise
        sujet = re.sub(r"\s+", " ", sujet).strip(" ?!.")
        sujet = re.sub(
            r"\ben js\b",
            "en JavaScript",
            sujet,
            flags=re.IGNORECASE,
        )

        texte = self._sans_accents(analyse.texte_normalise).casefold()
        if any(
            indice in texte
            for indice in ("javascript", " js", "console.log")
        ):
            requete = f"MDN {sujet}"
            sources = (
                "la documentation MDN, puis la spécification ECMAScript "
                "si un détail reste ambigu"
            )
            verification = (
                "copier le plus petit exemple dans la console du navigateur, "
                "observer le résultat et tester aussi un cas limite"
            )
        elif "python" in texte:
            requete = f"documentation Python {sujet}"
            sources = (
                "docs.python.org, puis la documentation de la bibliothèque "
                "concernée"
            )
            verification = (
                "exécuter un exemple minimal dans un environnement isolé "
                "et comparer le résultat à la documentation"
            )
        else:
            requete = f"{sujet} documentation officielle exemples"
            sources = (
                "une documentation officielle, puis une seconde source "
                "indépendante et identifiable"
            )
            verification = (
                "tester un exemple minimal et un contre-exemple avant de "
                "considérer l'information comme confirmée"
            )

        return (
            f"Je n'ai pas encore de connaissance confirmée sur « {sujet} ».\n"
            "Pour la trouver sans inventer :\n"
            f"1. Cherche : « {requete} ».\n"
            f"2. Consulte d'abord {sources}.\n"
            f"3. Vérifie ainsi : {verification}.\n"
            f"Commande possible : cherche en ligne | sujet={sujet} | "
            "sources=2 | exemples=3 | contre-exemples=2.\n"
            f"Sans Internet : donne-moi un extrait de documentation sur "
            f"« {sujet} » et je préparerai les vérifications."
        )

    def signaler_competence_absente(self, action: str) -> str:
        """Formule l'état d'un ordre compris mais impossible à exécuter."""

        return (
            f"Action comprise, mais aucune compétence « {action} » "
            "n'est enregistrée."
        )

    def confirmer_interdiction(self, analyse: Analyse) -> str:
        """Accuse réception d'une contrainte sans prétendre l'avoir mémorisée."""

        if analyse.action.valeur:
            return (
                f"Interdiction comprise : ne pas « {analyse.action.valeur} ». "
                "Le gestionnaire de contraintes n'est pas encore construit."
            )
        return (
            "Interdiction détectée, mais son action reste imprécise. "
            "Le gestionnaire de contraintes n'est pas encore construit."
        )

    @staticmethod
    def demander_clarification() -> str:
        return (
            "Je ne suis pas assez certain de la demande. "
            "Reformule-la avec une action et une cible précises."
        )
