"""Troisième étape : résolution des nuances à partir du voisinage."""

from __future__ import annotations

from dataclasses import replace

from .modeles import CandidatSens, Decoupage, SensContextuel, SensJeton
from .normalisation import cle


class Contexte:
    """Choisit un sens local sans décider de l'intention globale."""

    _EMPLOI = {"emploi", "recrutement", "travail", "candidature"}
    _CONVERSATION = {"bonjour", "bonsoir", "coucou", "hey", "salut"}
    _ESCALIER = {"escalier", "escalade", "pied"}

    def analyser(
        self,
        decoupage: Decoupage,
        sens: tuple[SensJeton, ...],
        historique: tuple[str, ...] = (),
    ) -> tuple[SensContextuel, ...]:
        mots = [jeton.normalise for jeton in decoupage.mots]
        contexte_global = set(mots)
        contexte_global.update(
            cle(mot)
            for message in historique[-3:]
            for mot in message.split()
        )

        resultats: list[SensContextuel] = []
        for position_mot, sens_jeton in enumerate(sens):
            candidats = list(sens_jeton.candidats)
            indices: list[str] = []
            choisi = candidats[0] if candidats else None

            if sens_jeton.jeton.normalise == "marche":
                choisi, indices = self._resoudre_marche(
                    sens_jeton, mots, contexte_global, position_mot
                )
            elif sens_jeton.jeton.normalise == "cv":
                choisi, indices = self._resoudre_cv(
                    sens_jeton, contexte_global
                )
            else:
                verbe = self._candidat(sens_jeton, "verbe_action")
                if verbe and self._position_directive(mots, position_mot):
                    if verbe.source.startswith("correction_candidate:"):
                        # La position confirme la nature verbale, pas l'orthographe.
                        # Le score faible oblige donc encore une confirmation.
                        choisi = verbe
                        correction = verbe.source.partition(":")[2]
                        indices = [
                            f"correction orthographique candidate : "
                            f"{sens_jeton.jeton.normalise} → {correction}"
                        ]
                    else:
                        choisi = replace(verbe, score=max(verbe.score, 90))
                        indices = [
                            "position directive : sens verbal privilégié"
                        ]
                elif (
                    choisi is not None
                    and choisi.categorie == "verbe_action"
                    and choisi.source.startswith("correction_candidate:")
                ):
                    # Une ressemblance située comme adjectif ou complément ne
                    # doit jamais devenir une action. Exemple : « cassée » est
                    # proche de « classe », mais suit ici le verbe d'état « est ».
                    choisi = None
                    indices = [
                        "ressemblance verbale ignorée hors position directive"
                    ]

            alternatives = tuple(
                candidat for candidat in candidats if candidat != choisi
            )
            resultats.append(
                SensContextuel(
                    jeton=sens_jeton.jeton,
                    choisi=choisi,
                    alternatives=alternatives,
                    indices=tuple(indices),
                )
            )

        return tuple(resultats)

    def _resoudre_marche(
        self,
        sens_jeton: SensJeton,
        mots: list[str],
        contexte_global: set[str],
        position: int,
    ) -> tuple[CandidatSens | None, list[str]]:
        precedent = mots[position - 1] if position > 0 else None
        suivant = mots[position + 1] if position + 1 < len(mots) else None

        categorie_voulue = "verbe_action"
        score = 90
        indices = ["position ou voisinage compatible avec une action"]

        if precedent in {"la", "une", "cette"} or contexte_global & self._ESCALIER:
            categorie_voulue = "nom"
            score = 94
            indices = ["article ou contexte d'escalier : sens nominal"]
        elif position == 0 or suivant == "vers":
            score = 96
            indices = ["début de phrase ou direction : sens verbal"]

        candidat = self._candidat(sens_jeton, categorie_voulue)
        return (
            replace(candidat, score=score) if candidat else None,
            indices,
        )

    def _resoudre_cv(
        self,
        sens_jeton: SensJeton,
        contexte_global: set[str],
    ) -> tuple[CandidatSens | None, list[str]]:
        if contexte_global & self._EMPLOI:
            candidat = self._candidat(sens_jeton, "nom_document")
            return (
                replace(candidat, score=96) if candidat else None,
                ["contexte professionnel : curriculum vitae"],
            )
        if contexte_global & self._CONVERSATION:
            candidat = self._candidat(sens_jeton, "question_etat")
            return (
                replace(candidat, score=94) if candidat else None,
                ["salutation voisine : « ça va »"],
            )
        candidat = self._candidat(sens_jeton, "nom_document")
        return (
            replace(candidat, score=55) if candidat else None,
            ["contexte insuffisant : sens le plus fréquent conservé faiblement"],
        )

    @staticmethod
    def _candidat(
        sens_jeton: SensJeton, categorie: str
    ) -> CandidatSens | None:
        return next(
            (
                candidat
                for candidat in sens_jeton.candidats
                if candidat.categorie == categorie
            ),
            None,
        )

    @staticmethod
    def _position_directive(mots: list[str], position: int) -> bool:
        avant = mots[:position]
        if not avant:
            return True
        if set(avant) <= {"euh", "heu", "n", "ne", "stp", "svp"}:
            return True
        return avant in (
            ["merci", "de"],
            ["s", "il", "te", "plait"],
            ["s", "il", "vous", "plait"],
        )
