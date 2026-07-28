"""Validation finale d'une réponse composée."""

from __future__ import annotations

from dataclasses import dataclass

from .contract import ResponseContract


@dataclass(frozen=True, slots=True)
class ResponseVerification:
    """Résultat explicable du contrôle de sortie."""

    valid: bool
    reasons: tuple[str, ...]


class ResponseVerifier:
    """Vérifie les limites et la présence du périmètre demandé."""

    def verify(
        self, contract: ResponseContract, response: str
    ) -> ResponseVerification:
        """Ne corrige jamais la sortie : il mesure seulement sa conformité."""

        reasons: list[str] = []
        if len(response) > contract.max_length:
            reasons.append("longueur dépassée")
        if not response.strip():
            reasons.append("réponse vide")
        if (
            "connaissance confirmée" not in response
            and contract.concepts
            and not any(
                concept.casefold() in response.casefold()
                for concept in contract.concepts
            )
        ):
            reasons.append("concept demandé absent")
        return ResponseVerification(not reasons, tuple(reasons))
