"""Extraction explicable de petites relations grammaticales françaises."""

from __future__ import annotations

from .connaissances import Connaissances
from .modeles import Decoupage, RelationSemantique, SensContextuel


class Relier:
    """Transforme quelques constructions stables en arêtes sémantiques."""

    def __init__(self, connaissances: Connaissances) -> None:
        self.connaissances = connaissances

    def analyser(
        self,
        decoupage: Decoupage,
        contextuels: tuple[SensContextuel, ...],
    ) -> tuple[RelationSemantique, ...]:
        mots = [element.jeton.normalise for element in contextuels]
        relations: list[RelationSemantique] = []

        # Les références restent explicites : « toi » ne devient jamais une
        # cible implicite inventée par le routeur.
        for element in contextuels:
            morphologies = self._morphologies(element)
            for categorie, _, entree in morphologies:
                if categorie != "reference":
                    continue
                referent = str(entree.get("referent", ""))
                if referent:
                    relations.append(
                        RelationSemantique(
                            source=element.jeton.normalise,
                            relation="reference",
                            target=referent,
                            score=100,
                            evidence="pronom ou déterminant personnel déclaré",
                        )
                    )

        relations.extend(self._relations_etat(mots, contextuels))
        relations.extend(self._relations_actions(contextuels))
        return self._uniques(relations)

    def _relations_etat(
        self,
        mots: list[str],
        contextuels: tuple[SensContextuel, ...],
    ) -> list[RelationSemantique]:
        verbes_etat = {
            str(mot) for mot in self.connaissances.obtenir("grammaire")["verbes_etat"]
        }
        relations: list[RelationSemantique] = []
        for index, mot in enumerate(mots):
            if mot not in verbes_etat:
                continue
            sujet = self._concept_avant(contextuels, index)
            if sujet is None:
                continue
            cible = self._premier_concept_apres(contextuels, index)
            if cible is not None:
                position, concept, categorie = cible
                relation = "est_un" if categorie == "nom_commun" else "attribut"
                relations.append(
                    RelationSemantique(
                        source=sujet,
                        relation=relation,
                        target=concept,
                        score=92,
                        evidence=f"construction avec verbe d'état « {mot} »",
                    )
                )
                # Une qualité placée après le nom décrit ce nom ; sinon elle
                # décrit directement le sujet.
                for element in contextuels[position + 1 :]:
                    adjectif = self._concept_morphologique(element, "adjectif")
                    if adjectif:
                        relations.append(
                            RelationSemantique(
                                source=concept,
                                relation="qualite",
                                target=adjectif,
                                score=90,
                                evidence="adjectif lié au nom attribut",
                            )
                        )
            for element in contextuels[index + 1 :]:
                adjectif = self._concept_morphologique(element, "adjectif")
                if adjectif and not any(
                    r.relation == "qualite" and r.target == adjectif for r in relations
                ):
                    relations.append(
                        RelationSemantique(
                            source=sujet,
                            relation="qualite",
                            target=adjectif,
                            score=90,
                            evidence="adjectif après un verbe d'état",
                        )
                    )
        return relations

    def _relations_actions(
        self,
        contextuels: tuple[SensContextuel, ...],
    ) -> list[RelationSemantique]:
        relations: list[RelationSemantique] = []
        for index, element in enumerate(contextuels):
            choisi = element.choisi
            if choisi is None or choisi.categorie != "verbe_action":
                continue
            source = self._concept_avant(contextuels, index) or "actor:user"
            cible = self._premier_concept_apres(contextuels, index)
            target = cible[1] if cible else None

            # Les clitiques liés par un tiret restent lisibles, par exemple
            # « explique-toi ».
            parties = element.jeton.normalise.split("-")
            if "toi" in parties or "te" in parties:
                target = "self:kairos"
            elif "moi" in parties or "me" in parties:
                target = "actor:user"

            if target:
                relations.append(
                    RelationSemantique(
                        source=source,
                        relation=choisi.lemme,
                        target=target,
                        score=min(95, max(80, choisi.score)),
                        evidence="sujet, verbe d'action et cible reliés par position",
                    )
                )
        return relations

    def _concept_avant(
        self, contextuels: tuple[SensContextuel, ...], index: int
    ) -> str | None:
        for element in reversed(contextuels[:index]):
            concept = self._concept(element)
            if concept:
                return concept[0]
        return None

    def _premier_concept_apres(
        self, contextuels: tuple[SensContextuel, ...], index: int
    ) -> tuple[int, str, str] | None:
        for position in range(index + 1, len(contextuels)):
            concept = self._concept(contextuels[position])
            if concept:
                return position, concept[0], concept[1]
        return None

    def _concept(self, element: SensContextuel) -> tuple[str, str] | None:
        for categorie in ("reference", "nom_propre", "nom_commun", "adjectif"):
            valeur = self._concept_morphologique(element, categorie)
            if valeur:
                return valeur, categorie
        candidats = (element.choisi, *element.alternatives)
        for candidat in candidats:
            if candidat is None:
                continue
            if candidat.categorie.startswith("entite:"):
                return candidat.lemme, "entite"
            if candidat.categorie.startswith("lexique:"):
                return candidat.lemme, "nom_commun"
        return None

    def _concept_morphologique(
        self, element: SensContextuel, categorie_voulue: str
    ) -> str | None:
        for categorie, lemme, entree in self._morphologies(element):
            if categorie != categorie_voulue:
                continue
            return str(entree.get("referent") or lemme)
        return None

    @staticmethod
    def _morphologies(
        element: SensContextuel,
    ) -> tuple[tuple[str, str, dict[str, object]], ...]:
        resultat: list[tuple[str, str, dict[str, object]]] = []
        for candidat in (element.choisi, *element.alternatives):
            if candidat is None or not candidat.categorie.startswith("morphologie:"):
                continue
            categorie = candidat.categorie.partition(":")[2]
            # Le sens encode seulement la définition ; le référent sera relu
            # depuis Connaissances par l'appelant.
            resultat.append((categorie, candidat.lemme, {}))
        return tuple(resultat)

    @staticmethod
    def _uniques(
        relations: list[RelationSemantique],
    ) -> tuple[RelationSemantique, ...]:
        uniques: dict[tuple[str, str, str], RelationSemantique] = {}
        for relation in relations:
            cle = (relation.source, relation.relation, relation.target)
            precedente = uniques.get(cle)
            if precedente is None or relation.score > precedente.score:
                uniques[cle] = relation
        return tuple(uniques.values())
