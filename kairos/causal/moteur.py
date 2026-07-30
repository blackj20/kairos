"""Moteur prédire → exécuter → observer → évaluer → rejouer."""

from __future__ import annotations

from typing import Any

from ..kernel import Kernel
from ..routing import PlanRoute, StatutRoute
from .contrats import CatalogueResultats
from .modeles import (
    EvaluationCausale,
    ObservationCausale,
    PredictionCausale,
    ResultatReplay,
    StatutEpisode,
)
from .stockage import StockageCausal


class PredicteurCausal:
    def __init__(self, catalogue: CatalogueResultats) -> None:
        self.catalogue = catalogue

    def predire(self, plan: PlanRoute) -> PredictionCausale:
        contrat_route = self.catalogue.route(plan.id)
        sorties: dict[str, dict[str, str]] = {}
        for etape in plan.etapes:
            contrat = self.catalogue.capacite(etape.capacite)
            if contrat is not None:
                sorties[etape.capacite] = {
                    str(cle): str(type_attendu)
                    for cle, type_attendu in dict(
                        contrat.get("required_outputs", {})
                    ).items()
                }
        disponible = contrat_route is not None and all(
            self.catalogue.capacite(etape.capacite) is not None
            for etape in plan.etapes
            if etape.obligatoire
        )
        conditions = tuple(
            dict(item)
            for item in (contrat_route or {}).get("success_conditions", [])
        )
        return PredictionCausale(
            objectif=str((contrat_route or {}).get("goal") or plan.objectif),
            route_id=plan.id,
            resultat_attendu=conditions,
            sorties_attendues=sorties,
            contrat_disponible=disponible,
        )


class ObservateurCausal:
    """Capture les faits bruts sans décider si l'objectif est atteint."""

    @staticmethod
    def capturer(
        plan: PlanRoute,
        *,
        execution_tentee: bool,
        sortie: dict[str, Any] | None = None,
        erreur: Exception | str | None = None,
    ) -> ObservationCausale:
        donnees = dict(sortie or {})
        trace = tuple(dict(item) for item in donnees.pop("trace", []))
        message_erreur = None
        if erreur is not None:
            message_erreur = (
                f"{type(erreur).__name__}: {erreur}"
                if isinstance(erreur, Exception)
                else str(erreur)
            )
        return ObservationCausale(
            execution_tentee=execution_tentee,
            succes_technique=execution_tentee and message_erreur is None,
            route_id=plan.id,
            trace=trace,
            sortie=donnees,
            erreur=message_erreur,
        )


class EvaluateurCausal:
    TYPES = {
        "bool": lambda value: isinstance(value, bool),
        "dict": lambda value: isinstance(value, dict),
        "list": lambda value: isinstance(value, list),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "str": lambda value: isinstance(value, str),
        "nullable": lambda value: value is None,
    }

    def evaluer(
        self,
        prediction: PredictionCausale,
        observation: ObservationCausale,
    ) -> EvaluationCausale:
        controles: list[dict[str, Any]] = []
        erreurs: list[str] = []
        if not prediction.contrat_disponible:
            erreurs.append("missing_outcome_contract")
        if not observation.execution_tentee:
            erreurs.append("route_not_executed")
        elif not observation.succes_technique:
            erreurs.append("execution_error")

        executees = {
            str(item.get("capability", ""))
            for item in observation.trace
            if item.get("status") == "success"
        }
        for capacite in sorted(executees):
            for champ, type_attendu in prediction.sorties_attendues.get(
                capacite, {}
            ).items():
                valeur = observation.sortie.get(champ)
                valideur = self.TYPES.get(type_attendu)
                reussi = bool(valideur and champ in observation.sortie and valideur(valeur))
                controles.append(
                    {
                        "id": f"{capacite}:{champ}",
                        "kind": "output_contract",
                        "passed": reussi,
                    }
                )
                if not reussi:
                    erreurs.append("output_contract_violation")

        for condition in prediction.resultat_attendu:
            reussi = self._condition(condition, observation.sortie)
            controles.append(
                {
                    "id": str(condition.get("id", "condition")),
                    "kind": "goal_condition",
                    "passed": reussi,
                }
            )
            if not reussi:
                code = (
                    "information_not_found"
                    if condition.get("id") == "information_found"
                    else "goal_condition_failed"
                )
                erreurs.append(code)

        total = len(controles)
        reussis = sum(1 for item in controles if item["passed"])
        score = round(100 * reussis / total) if total else 0
        objectif_atteint = bool(
            prediction.contrat_disponible
            and observation.succes_technique
            and total
            and reussis == total
        )
        return EvaluationCausale(
            succes_technique=observation.succes_technique,
            objectif_atteint=objectif_atteint,
            comprehension_validee=objectif_atteint,
            score_resultat=score,
            controles=tuple(controles),
            erreurs=tuple(dict.fromkeys(erreurs)),
        )

    def _condition(self, condition: dict[str, Any], sortie: dict[str, Any]) -> bool:
        if "any" in condition:
            enfants = condition.get("any")
            return isinstance(enfants, list) and any(
                self._condition(dict(item), sortie)
                for item in enfants
                if isinstance(item, dict)
            )
        if "all" in condition:
            enfants = condition.get("all")
            return isinstance(enfants, list) and bool(enfants) and all(
                self._condition(dict(item), sortie)
                for item in enfants
                if isinstance(item, dict)
            )
        path = str(condition.get("path", ""))
        present, valeur = self._lire(sortie, path)
        operateur = str(condition.get("operator", "exists"))
        if operateur == "exists":
            return present
        if operateur == "equals":
            return present and valeur == condition.get("value")
        if operateur == "non_empty":
            return present and valeur is not None and bool(valeur)
        return False

    @staticmethod
    def _lire(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
        courant: Any = payload
        for segment in path.split("."):
            if not isinstance(courant, dict) or segment not in courant:
                return False, None
            courant = courant[segment]
        return True, courant


class MoteurCausal:
    """Orchestre un épisode sans modifier les connaissances confirmées."""

    def __init__(
        self,
        *,
        kernel: Kernel | None = None,
        stockage: StockageCausal | None = None,
        catalogue: CatalogueResultats | None = None,
    ) -> None:
        self.kernel = kernel or Kernel()
        self.stockage = stockage or StockageCausal()
        self.catalogue = catalogue or CatalogueResultats()
        self.predicteur = PredicteurCausal(self.catalogue)
        self.observateur = ObservateurCausal()
        self.evaluateur = EvaluateurCausal()
        self._owns_kernel = kernel is None
        self._owns_stockage = stockage is None

    def executer_message(
        self,
        requete: str,
        *,
        replay_of: str | None = None,
    ) -> dict[str, Any]:
        analyse = self.kernel.comprendre.analyser(requete)
        action = analyse.action.valeur
        cible = analyse.cible.valeur
        return self.executer(
            str(action or ""),
            str(cible) if cible is not None else None,
            requete=requete,
            replay_of=replay_of,
        )

    def executer(
        self,
        action: str,
        cible: str | None,
        *,
        requete: str | None = None,
        replay_of: str | None = None,
    ) -> dict[str, Any]:
        texte = requete or " ".join(item for item in (action, cible) if item)
        plan = self.kernel.routeur.planifier(action, cible)
        episode_id = self.stockage.creer(
            texte, action or None, cible, plan.id, replay_of=replay_of
        )
        prediction = self.predicteur.predire(plan)
        self.stockage.transition(
            episode_id, StatutEpisode.PREDICTED, prediction.vers_dict()
        )

        peut_executer = (
            plan.statut is StatutRoute.READY
            and prediction.contrat_disponible
        )
        self.stockage.transition(
            episode_id,
            StatutEpisode.EXECUTED,
            {
                "attempted": peut_executer,
                "route_status": plan.statut.value,
                "contract_available": prediction.contrat_disponible,
            },
        )
        if peut_executer:
            try:
                resultat = self.kernel.routeur.executer(
                    plan, {"request": texte}
                )
                observation = self.observateur.capturer(
                    plan,
                    execution_tentee=True,
                    sortie=resultat,
                )
            except Exception as erreur:
                observation = self.observateur.capturer(
                    plan,
                    execution_tentee=True,
                    erreur=erreur,
                )
        else:
            raison = (
                "contrat de résultat absent"
                if not prediction.contrat_disponible
                else f"route {plan.statut.value}: {plan.raison}"
            )
            observation = self.observateur.capturer(
                plan,
                execution_tentee=False,
                erreur=raison,
            )
        self.stockage.transition(
            episode_id, StatutEpisode.OBSERVED, observation.vers_dict()
        )
        evaluation = self.evaluateur.evaluer(prediction, observation)
        self.stockage.transition(
            episode_id, StatutEpisode.EVALUATED, evaluation.vers_dict()
        )
        episode = self.stockage.episode(episode_id)
        assert episode is not None
        episode["transitions"] = self.stockage.transitions(episode_id)
        return episode

    def rejouer(self, episode_id: str) -> dict[str, Any]:
        source = self.stockage.episode(episode_id)
        if source is None:
            raise KeyError(episode_id)
        replay = self.executer_message(
            str(source["request"]), replay_of=episode_id
        )
        avant = dict(source.get("evaluation") or {})
        apres = dict(replay.get("evaluation") or {})
        score_avant = int(avant.get("score_resultat", 0))
        score_apres = int(apres.get("score_resultat", 0))
        succes_avant = bool(avant.get("objectif_atteint"))
        succes_apres = bool(apres.get("objectif_atteint"))
        comparaison = ResultatReplay(
            source_episode_id=episode_id,
            replay_episode_id=str(replay["id"]),
            score_avant=score_avant,
            score_apres=score_apres,
            difference=score_apres - score_avant,
            meme_resultat=(succes_avant == succes_apres),
            regression=succes_avant and not succes_apres,
        )
        return {"comparison": comparaison.vers_dict(), "episode": replay}

    def close(self) -> None:
        if self._owns_kernel:
            self.kernel.close()
        if self._owns_stockage:
            self.stockage.close()
