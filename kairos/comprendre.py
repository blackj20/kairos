"""Orchestrateur du pipeline linguistique de K.A.I.R.O.S."""

from __future__ import annotations

from .connaissances import Connaissances
from .contexte import Contexte
from .decouper import Decouper
from .estimation import Estimer
from .modeles import Analyse
from .sens import Sens
from .verifier_analyse import VerifierAnalyse


class Comprendre:
    """Coordonne les étapes sans parler, agir ou modifier la mémoire."""

    def __init__(self, connaissances: Connaissances | None = None) -> None:
        self.connaissances = connaissances or Connaissances()
        self.decouper = Decouper()
        self.sens = Sens(self.connaissances)
        self.contexte = Contexte()
        self.estimer = Estimer(self.connaissances)
        self.verifier = VerifierAnalyse(self.connaissances)

    def analyser(
        self,
        texte: str,
        historique: tuple[str, ...] = (),
    ) -> Analyse:
        """Retourne un rapport vérifié au kernel, sans effet de bord."""

        decoupage = self.decouper.analyser(texte)
        sens_possibles = self.sens.analyser(decoupage)
        sens_contextuels = self.contexte.analyser(
            decoupage,
            sens_possibles,
            historique,
        )
        resultat = self.estimer.analyser(decoupage, sens_contextuels)
        verification = self.verifier.analyser(resultat)

        return Analyse(
            texte_original=texte,
            texte_normalise=decoupage.texte_normalise,
            type_requete=resultat.type_requete,
            demarche=resultat.demarche,
            action=resultat.action,
            cible=resultat.cible,
            indices=resultat.indices,
            jetons_inconnus=resultat.jetons_inconnus,
            alternative_type=resultat.alternative_type,
            decoupage=decoupage,
            sens_contextuels=sens_contextuels,
            verification=verification,
        )
