"""Fournisseurs Web bornés et injectables pour des tests hors ligne."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Protocol

from .modeles import SourceInformation


class ErreurRechercheWeb(RuntimeError):
    """Signale une recherche externe impossible sans casser le Kernel."""


class FournisseurRecherche(Protocol):
    def rechercher(
        self, requete: str, *, limite: int = 3
    ) -> tuple[SourceInformation, ...]:
        """Retourne au plus ``limite`` sources sans modifier la mémoire."""


class FournisseurStatique:
    """Fournisseur déterministe pour tests, simulation et sources supervisées."""

    def __init__(self, sources: Iterable[SourceInformation]) -> None:
        self.sources = tuple(sources)

    def rechercher(
        self, requete: str, *, limite: int = 3
    ) -> tuple[SourceInformation, ...]:
        del requete
        return self.sources[:limite]


class WikipediaFR:
    """Recherche encyclopédique HTTPS limitée au domaine Wikipédia français."""

    ENDPOINT = "https://fr.wikipedia.org/w/api.php"
    MAX_OCTETS = 1_000_000

    def __init__(self, *, timeout: float = 6.0) -> None:
        self.timeout = timeout

    def rechercher(
        self, requete: str, *, limite: int = 3
    ) -> tuple[SourceInformation, ...]:
        cible = requete.strip()
        if not cible:
            return ()
        limite = max(1, min(int(limite), 5))
        parametres = urllib.parse.urlencode(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": cible,
                "gsrlimit": limite,
                "prop": "extracts|info",
                "exintro": 1,
                "explaintext": 1,
                "inprop": "url",
                "format": "json",
                "formatversion": 2,
            }
        )
        requete_http = urllib.request.Request(
            f"{self.ENDPOINT}?{parametres}",
            headers={"User-Agent": "KAIROS/0.7 (read-only knowledge research)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                requete_http, timeout=self.timeout
            ) as reponse:
                contenu = reponse.read(self.MAX_OCTETS + 1)
        except (OSError, TimeoutError, urllib.error.URLError) as erreur:
            raise ErreurRechercheWeb(
                f"Wikipédia indisponible : {erreur}"
            ) from erreur
        if len(contenu) > self.MAX_OCTETS:
            raise ErreurRechercheWeb("Réponse Web trop volumineuse.")
        try:
            donnees = json.loads(contenu.decode("utf-8"))
            pages = donnees.get("query", {}).get("pages", [])
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as erreur:
            raise ErreurRechercheWeb("Réponse Web invalide.") from erreur

        sources: list[SourceInformation] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            extrait = " ".join(str(page.get("extract", "")).split())
            url = str(page.get("fullurl", ""))
            if not extrait or not url.startswith("https://fr.wikipedia.org/"):
                continue
            sources.append(
                SourceInformation(
                    titre=str(page.get("title") or cible),
                    url=url,
                    extrait=extrait[:1200],
                    confiance=65,
                )
            )
        return tuple(sources[:limite])
