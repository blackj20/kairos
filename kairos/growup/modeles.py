"""Contrats immuables de la couche d'évolution GrowUp."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ObservationApprentissage:
    """Vue normalisée d'une expérience ou d'un événement à étudier."""

    id: str
    source_type: str
    requete: str
    champ: str
    focus: str | None
    occurrences: int
    resolution: dict[str, Any] = field(default_factory=dict)
    creee_le: str | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GroupeApprentissage:
    """Problème unique obtenu après regroupement d'observations similaires."""

    id: str
    cle: str
    champ: str
    focus: str | None
    observation_ids: tuple[str, ...]
    experience_ids: tuple[str, ...]
    evenement_ids: tuple[str, ...]
    occurrences: int
    relation_source: str | None = None
    relation_targets: tuple[str, ...] = field(default_factory=tuple)
    contradictions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def relation_target(self) -> str | None:
        return self.relation_targets[0] if len(self.relation_targets) == 1 else None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, payload: dict[str, Any]) -> "GroupeApprentissage":
        return cls(
            id=str(payload["id"]),
            cle=str(payload["cle"]),
            champ=str(payload["champ"]),
            focus=payload.get("focus"),
            observation_ids=tuple(payload.get("observation_ids", ())),
            experience_ids=tuple(payload.get("experience_ids", ())),
            evenement_ids=tuple(payload.get("evenement_ids", ())),
            occurrences=int(payload.get("occurrences", 0)),
            relation_source=payload.get("relation_source"),
            relation_targets=tuple(payload.get("relation_targets", ())),
            contradictions=tuple(payload.get("contradictions", ())),
        )


@dataclass(frozen=True, slots=True)
class ScorePriorite:
    """Décomposition explicable du score de traitement."""

    total: int
    frequence: int
    impact: int
    risque: int
    verifiabilite: int

    def vers_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, payload: dict[str, Any]) -> "ScorePriorite":
        return cls(
            total=int(payload["total"]),
            frequence=int(payload["frequence"]),
            impact=int(payload["impact"]),
            risque=int(payload["risque"]),
            verifiabilite=int(payload["verifiabilite"]),
        )


@dataclass(frozen=True, slots=True)
class PlanApprentissage:
    """Plan produit par GrowUp sans promotion automatique."""

    id: str
    groupe_id: str
    objectif: str
    route: str
    manques: tuple[str, ...]
    questions: tuple[str, ...]
    tests_requis: int
    priorite: ScorePriorite
    statut: str = "planned"

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, payload: dict[str, Any]) -> "PlanApprentissage":
        return cls(
            id=str(payload["id"]),
            groupe_id=str(payload["groupe_id"]),
            objectif=str(payload["objectif"]),
            route=str(payload["route"]),
            manques=tuple(payload.get("manques", ())),
            questions=tuple(payload.get("questions", ())),
            tests_requis=int(payload.get("tests_requis", 0)),
            priorite=ScorePriorite.depuis_dict(dict(payload["priorite"])),
            statut=str(payload.get("statut", "planned")),
        )


@dataclass(frozen=True, slots=True)
class PreuveApprentissage:
    """Preuve explicite fournie à une consolidation."""

    source_type: str
    source_ref: str
    contenu: str
    confiance: int

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.contenu.strip():
            raise ValueError("Une preuve exige une référence et un contenu.")
        if not 0 <= self.confiance <= 100:
            raise ValueError("La confiance d'une preuve doit être entre 0 et 100.")


@dataclass(frozen=True, slots=True)
class RapportGrowUp:
    """Résultat traçable d'un scan GrowUp."""

    run_id: str
    observations: int
    groupes: tuple[GroupeApprentissage, ...]
    plans: tuple[PlanApprentissage, ...]

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResultatConsolidation:
    """Artefacts produits par la porte Réfléchir → Tester → SECAU."""

    plan_id: str
    hypothesis_id: str
    report_id: str
    verdict: str
    raison: str
    relation_id: str | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
