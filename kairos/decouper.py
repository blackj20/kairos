"""Première étape : découpage mécanique et conservation des positions."""

from __future__ import annotations

import re

from .modeles import Decoupage, Jeton
from .normalisation import cle


class Decouper:
    """Découpe sans attribuer de sens aux éléments."""

    _MOT_OU_PONCTUATION = re.compile(
        r"[a-zA-ZÀ-ÿ0-9_+#.-]+|[?!,;:]",
        flags=re.UNICODE,
    )

    def analyser(self, texte: str) -> Decoupage:
        if not isinstance(texte, str):
            raise TypeError("Découper attend une chaîne de caractères.")

        jetons: list[Jeton] = []
        for position, correspondance in enumerate(
            self._MOT_OU_PONCTUATION.finditer(texte)
        ):
            valeur = correspondance.group(0)
            jetons.append(
                Jeton(
                    valeur=valeur,
                    normalise=cle(valeur),
                    position=position,
                    debut=correspondance.start(),
                    fin=correspondance.end(),
                    ponctuation=valeur in {"?", "!", ",", ";", ":"},
                )
            )

        return Decoupage(
            texte_original=texte,
            texte_normalise=" ".join(texte.casefold().strip().split()),
            jetons=tuple(jetons),
        )
