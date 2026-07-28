"""Objets échangés entre les composants de K.A.I.R.O.S."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Estimation:
    """Une hypothèse produite par un composant avec un score de confiance."""

    valeur: str | None
    score: int

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("Un score doit être compris entre 0 et 100.")


@dataclass(frozen=True, slots=True)
class Jeton:
    """Élément conservant sa forme, sa position et sa nature mécanique."""

    valeur: str
    normalise: str
    position: int
    debut: int
    fin: int
    ponctuation: bool = False


@dataclass(frozen=True, slots=True)
class Decoupage:
    """Sortie de Découper, sans interprétation sémantique."""

    texte_original: str
    texte_normalise: str
    jetons: tuple[Jeton, ...]

    @property
    def mots(self) -> tuple[Jeton, ...]:
        return tuple(jeton for jeton in self.jetons if not jeton.ponctuation)


@dataclass(frozen=True, slots=True)
class CandidatSens:
    """Un sens possible trouvé dans les connaissances ou la mémoire."""

    lemme: str
    categorie: str
    sens: str
    score: int
    source: str


@dataclass(frozen=True, slots=True)
class SensJeton:
    """Tous les sens possibles d'un jeton."""

    jeton: Jeton
    candidats: tuple[CandidatSens, ...]


@dataclass(frozen=True, slots=True)
class SensContextuel:
    """Sens retenu après lecture du contexte, avec ses alternatives."""

    jeton: Jeton
    choisi: CandidatSens | None
    alternatives: tuple[CandidatSens, ...] = field(default_factory=tuple)
    indices: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ResultatEstimation:
    """Hypothèses globales produites avant la vérification finale."""

    type_requete: Estimation
    alternative_type: Estimation
    demarche: Estimation
    action: Estimation
    cible: Estimation
    indices: tuple[str, ...] = field(default_factory=tuple)
    jetons_inconnus: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Verification:
    """Verdict transmis au kernel par la dernière couche de Comprendre."""

    valide: bool
    route: str
    score: int
    raisons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Analyse:
    """Résultat complet retourné par Comprendre au kernel."""

    texte_original: str
    texte_normalise: str
    type_requete: Estimation
    demarche: Estimation
    action: Estimation
    cible: Estimation
    indices: tuple[str, ...] = field(default_factory=tuple)
    jetons_inconnus: tuple[str, ...] = field(default_factory=tuple)
    alternative_type: Estimation = field(
        default_factory=lambda: Estimation(None, 0)
    )
    decoupage: Decoupage | None = None
    sens_contextuels: tuple[SensContextuel, ...] = field(default_factory=tuple)
    verification: Verification = field(
        default_factory=lambda: Verification(
            valide=False,
            route="clarification",
            score=0,
            raisons=("analyse non vérifiée",),
        )
    )

    def vers_dict(self) -> dict[str, Any]:
        """Expose une forme sérialisable pour les logs et futurs fichiers mémoire."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class Decision:
    """Décision finale du kernel après réception d'une analyse."""

    route: str
    analyse: Analyse
    reponse: str
    question_id: str | None = None
    question: str | None = None
    evaluation: dict[str, Any] | None = None
    verdict: dict[str, Any] | None = None

    def vers_dict(self) -> dict[str, Any]:
        return asdict(self)
