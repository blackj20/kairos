"""Outils de normalisation partagés sans décision linguistique."""

from __future__ import annotations

import unicodedata


def sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(
        caractere
        for caractere in decompose
        if not unicodedata.combining(caractere)
    )


def cle(texte: str) -> str:
    """Produit une clé comparable en conservant le texte humain d'origine."""

    return sans_accents(" ".join(texte.casefold().strip().split()))
