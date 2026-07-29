"""Deuxième étape : recherche des sens possibles, sans choix contextuel."""

from __future__ import annotations

from .connaissances import Connaissances
from .modeles import CandidatSens, Decoupage, SensJeton


class Sens:
    """Consulte les connaissances pour chaque mot et conserve les ambiguïtés."""

    def __init__(self, connaissances: Connaissances) -> None:
        self.connaissances = connaissances

    def analyser(self, decoupage: Decoupage) -> tuple[SensJeton, ...]:
        resultats: list[SensJeton] = []
        mots_contexte = tuple(jeton.normalise for jeton in decoupage.mots)

        for jeton in decoupage.mots:
            candidats: list[CandidatSens] = []
            relation_contextuelle = (
                self.connaissances.trouver_relation_contextuelle(
                    jeton.normalise,
                    mots_contexte,
                )
            )
            if relation_contextuelle:
                cible, relation = relation_contextuelle
                regle_cible = self.connaissances.verbes[cible]
                candidats.append(
                    CandidatSens(
                        lemme=cible,
                        categorie="verbe_action",
                        sens=str(regle_cible["sens"]),
                        score=int(relation.get("score", 80)),
                        source=(
                            "data/fr/sens.json:"
                            + str(relation.get("id", "relation"))
                        ),
                    )
                )
            verbe = self.connaissances.trouver_verbe(jeton.normalise)
            if verbe:
                lemme, regle = verbe
                forme_apprise = self.connaissances.corrections.obtenir(
                    jeton.normalise
                )
                relation_apprise = (
                    self.connaissances.relations_verbes.obtenir(
                        jeton.normalise
                    )
                )
                candidats.append(
                    CandidatSens(
                        lemme=lemme,
                        categorie="verbe_action",
                        sens=str(regle["sens"]),
                        score=int(regle.get("score_base", 60)),
                        source=(
                            "memory/semantic_relations"
                            if relation_apprise is not None
                            else (
                                "memory/corrections"
                                if forme_apprise is not None
                                else "data/fr/verbes.json"
                            )
                        ),
                    )
                )
            else:
                # La correction floue reste un candidat faible. Elle permet de
                # comprendre l'intention, mais force la couche Décision à demander
                # une confirmation avant toute éventuelle exécution.
                proposition = self.connaissances.proposer_correction_verbe(
                    jeton.normalise
                )
                if proposition:
                    lemme, regle, forme_correcte, score = proposition
                    candidats.append(
                        CandidatSens(
                            lemme=lemme,
                            categorie="verbe_action",
                            sens=str(regle["sens"]),
                            score=score,
                            source=f"correction_candidate:{forme_correcte}",
                        )
                    )

            entite = self.connaissances.trouver_entite(jeton.normalise)
            if entite:
                valeur, categorie = entite
                forme_apprise = self.connaissances.corrections.obtenir(
                    jeton.normalise
                )
                candidats.append(
                    CandidatSens(
                        lemme=valeur,
                        categorie=f"entite:{categorie}",
                        sens=valeur,
                        score=100,
                        source=(
                            "memory/corrections"
                            if forme_apprise is not None
                            else "data/fr/entites.json"
                        ),
                    )
                )
            else:
                proposition_entite = (
                    self.connaissances.proposer_correction_entite(
                        jeton.normalise
                    )
                )
                if proposition_entite:
                    valeur, categorie, score = proposition_entite
                    candidats.append(
                        CandidatSens(
                            lemme=valeur,
                            categorie=f"entite:{categorie}",
                            sens=valeur,
                            score=score,
                            source=f"correction_candidate:{valeur}",
                        )
                    )

            for entree in self.connaissances.sens_ambigus.get(
                jeton.normalise, []
            ):
                candidats.append(
                    CandidatSens(
                        lemme=str(entree["lemme"]),
                        categorie=str(entree["categorie"]),
                        sens=str(entree["sens"]),
                        score=int(entree["score_base"]),
                        source="data/fr/sens.json",
                    )
                )

            for categorie in self.connaissances.fonctions_pour(
                jeton.normalise
            ):
                candidats.append(
                    CandidatSens(
                        lemme=jeton.normalise,
                        categorie=categorie,
                        sens=jeton.normalise,
                        score=95,
                        source=f"data/fr/{categorie.split(':')[0]}.json",
                    )
                )

            for categorie in self.connaissances.expressions_pour(
                jeton.normalise
            ):
                candidats.append(
                    CandidatSens(
                        lemme=jeton.normalise,
                        categorie=f"expression:{categorie}",
                        sens=jeton.normalise,
                        score=85,
                        source="data/fr/expressions.json",
                    )
                )

            courant = self.connaissances.trouver_mot_courant(
                jeton.normalise
            )
            if courant:
                candidats.append(
                    CandidatSens(
                        lemme=str(courant["lemma"]),
                        categorie=f"lexique:{courant['category']}",
                        sens=str(courant["meaning"]),
                        score=90,
                        source="data/fr/lexique.json",
                    )
                )

            if not candidats:
                candidats.append(
                    CandidatSens(
                        lemme=jeton.normalise,
                        categorie="inconnu",
                        sens="inconnu",
                        score=0,
                        source="aucune",
                    )
                )

            # Plusieurs sources peuvent décrire le même sens. Une seule trace suffit.
            uniques: dict[tuple[str, str, str], CandidatSens] = {}
            for candidat in candidats:
                cle_candidat = (
                    candidat.lemme,
                    candidat.categorie,
                    candidat.sens,
                )
                precedent = uniques.get(cle_candidat)
                if precedent is None or candidat.score > precedent.score:
                    uniques[cle_candidat] = candidat

            resultats.append(
                SensJeton(
                    jeton=jeton,
                    candidats=tuple(
                        sorted(
                            uniques.values(),
                            key=lambda candidat: candidat.score,
                            reverse=True,
                        )
                    ),
                )
            )

        return tuple(resultats)
