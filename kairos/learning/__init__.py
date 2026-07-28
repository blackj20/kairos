"""Acquisition et extraction de sources structurées."""

from .acquire import Acquire
from .extract import Extractor
from .internet import InternetAcquire, InternetDocument, UrlFetcher
from .pipeline import InternetLearningPipeline, LearningResult

__all__ = [
    "Acquire",
    "Extractor",
    "InternetAcquire",
    "InternetDocument",
    "InternetLearningPipeline",
    "LearningResult",
    "UrlFetcher",
]
