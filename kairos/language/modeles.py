"""Contrats structurés échangés avec un moteur linguistique local."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _score(value: Any, default: int = 0) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if 0.0 <= number <= 1.0:
        number *= 100
    return max(0, min(100, round(number)))


@dataclass(frozen=True, slots=True)
class RelationCandidateLangage:
    """Relation proposée par le modèle, jamais considérée comme une preuve."""

    source: str
    relation: str
    cible: str
    confiance: int = 0

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.relation.strip() or not self.cible.strip():
            raise ValueError("Une relation candidate doit être complète.")
        if not 0 <= self.confiance <= 100:
            raise ValueError("La confiance doit être comprise entre 0 et 100.")


@dataclass(frozen=True, slots=True)
class LectureLangage:
    """Analyse candidate produite par un LLM local."""

    type_requete: str | None
    demarche: str | None
    action: str | None
    cible: str | None
    negation: bool
    confiance: int
    informations_manquantes: tuple[str, ...] = field(default_factory=tuple)
    relations: tuple[RelationCandidateLangage, ...] = field(default_factory=tuple)
    modele: str = "unknown"
    brut: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.confiance <= 100:
            raise ValueError("La confiance doit être comprise entre 0 et 100.")

    @classmethod
    def depuis_dict(
        cls,
        payload: dict[str, Any],
        *,
        modele: str,
    ) -> "LectureLangage":
        relations: list[RelationCandidateLangage] = []
        for item in payload.get("relations", ()) or ():
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or "").strip()
            relation = str(item.get("relation") or "").strip()
            cible = str(item.get("target") or item.get("cible") or "").strip()
            if not source or not relation or not cible:
                continue
            relations.append(
                RelationCandidateLangage(
                    source=source,
                    relation=relation,
                    cible=cible,
                    confiance=_score(item.get("confidence"), 0),
                )
            )
        raw_missing = payload.get("missing_information") or ()
        if isinstance(raw_missing, str):
            raw_missing = (raw_missing,)
        missing = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in raw_missing
                if str(item).strip()
            )
        )
        return cls(
            type_requete=_optional(payload.get("request_type") or payload.get("type_requete")),
            demarche=_optional(payload.get("approach") or payload.get("demarche")),
            action=_optional(payload.get("action")),
            cible=_optional(payload.get("target") or payload.get("cible")),
            negation=bool(payload.get("negation", False)),
            confiance=_score(payload.get("confidence"), 0),
            informations_manquantes=missing,
            relations=tuple(relations),
            modele=modele,
            brut=dict(payload),
        )

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
