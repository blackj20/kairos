"""Barrière de performance du squelette linguistique V0.9."""

from __future__ import annotations

import json
import time

from kairos import Kernel


CORPUS = (
    "salut cv ?",
    "cherche des informations sur les atomes",
    "installe python",
    "ne ferme pas le fichier",
    "pose-moi des questions sur la mémoire",
    "vérifie cette source",
    "merci pour la réponse",
    "planifie les étapes suivantes",
)


def main() -> int:
    kernel = Kernel()
    tours = 80
    debut = time.perf_counter()
    analyses = 0
    for _ in range(tours):
        for phrase in CORPUS:
            kernel.comprendre.analyser(phrase)
            analyses += 1
    duree = time.perf_counter() - debut
    debit = round(analyses / max(duree, 0.000001), 2)
    resultat = {
        "analyses": analyses,
        "duration_seconds": round(duree, 4),
        "analyses_per_second": debit,
        "minimum_required": 100.0,
        "indexed_verbs": kernel.comprendre.connaissances.nombre_verbes_indexes,
        "indexed_entities": kernel.comprendre.connaissances.nombre_entites_indexees,
        "indexed_common_words": kernel.comprendre.connaissances.nombre_mots_courants_indexes,
    }
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0 if debit >= 100.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
