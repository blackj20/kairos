"""Acquisition Internet bornée, multi-source et traçable."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol

from ..memory import MemoryRepository


class Fetcher(Protocol):
    """Contrat injectable afin de tester sans dépendre du réseau."""

    def fetch(self, url: str, max_bytes: int) -> tuple[str, str]: ...


class _TextExtractor(HTMLParser):
    """Extrait le texte visible d'un HTML sans exécuter son contenu."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


class UrlFetcher:
    """Client HTTPS minimal avec timeout, taille limite et protection réseau local."""

    def __init__(self, timeout_seconds: int = 8) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _validate_public_https(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Seules les sources HTTPS publiques sont autorisées.")
        for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(info[4][0])
            if not address.is_global:
                raise ValueError("Une source Internet ne peut viser le réseau local.")

    def fetch(self, url: str, max_bytes: int) -> tuple[str, str]:
        self._validate_public_https(url)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "KAIROS-Learning/0.1"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain", "application/json"}:
                raise ValueError(f"Type de contenu refusé : {content_type}")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError("Source Internet trop volumineuse.")
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
        if content_type == "text/html":
            parser = _TextExtractor()
            parser.feed(text)
            text = "\n".join(parser.parts)
        return text, content_type


@dataclass(frozen=True, slots=True)
class InternetDocument:
    """Document collecté avec son identifiant de preuve."""

    url: str
    content: str
    content_type: str
    evidence_id: str


class InternetAcquire:
    """Collecte au moins deux domaines distincts avant toute hypothèse."""

    def __init__(
        self,
        repository: MemoryRepository,
        fetcher: Fetcher | None = None,
        max_bytes: int = 1_000_000,
    ) -> None:
        self.repository = repository
        self.fetcher = fetcher or UrlFetcher()
        self.max_bytes = max_bytes

    def fetch_many(self, urls: tuple[str, ...]) -> tuple[InternetDocument, ...]:
        """Télécharge et enregistre chaque source comme Evidence indépendante."""

        unique_urls = tuple(dict.fromkeys(urls))
        domains = {
            urllib.parse.urlparse(url).hostname
            for url in unique_urls
            if urllib.parse.urlparse(url).hostname
        }
        if len(unique_urls) < 2 or len(domains) < 2:
            raise ValueError("L'apprentissage Internet exige deux domaines distincts.")
        documents: list[InternetDocument] = []
        for url in unique_urls:
            content, content_type = self.fetcher.fetch(url, self.max_bytes)
            if len(content.strip()) < 40:
                raise ValueError(f"Source trop pauvre : {url}")
            evidence_id = self.repository.add_evidence(
                "internet",
                url,
                content,
                70,
            )
            documents.append(
                InternetDocument(url, content, content_type, evidence_id)
            )
        return tuple(documents)
