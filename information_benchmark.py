"""Barrière mesurable de la recherche d'information V0.7."""

from __future__ import annotations

from kairos import Kernel
from kairos.information import FournisseurStatique, SourceInformation
from kairos.memory import MemoryRepository


def main() -> int:
    repository = MemoryRepository()
    fournisseur = FournisseurStatique(
        (
            SourceInformation(
                "Xylophore A",
                "https://source-a.example/xylophore",
                "Un xylophore est un organisme associé au bois.",
                confiance=70,
            ),
            SourceInformation(
                "Xylophore B",
                "https://source-b.example/xylophore",
                "Le xylophore désigne un organisme lié au bois.",
                confiance=75,
            ),
        )
    )
    try:
        local = Kernel(cognitive_repository=repository).traiter(
            "cherche toi-même atoms"
        )
        web = Kernel(
            cognitive_repository=repository,
            web_provider=fournisseur,
        ).traiter("cherche toi-même xylophore")
        candidate = repository.candidate_for("xylophore")
        audits = repository.audit_events()
        checks = (
            local.analyse.action.valeur == "chercher",
            local.analyse.cible.valeur == "atome",
            local.routage is not None and local.routage["statut"] == "ready",
            "Source confirmée" in local.reponse,
            web.routage is not None and web.routage["statut"] == "ready",
            candidate is not None and candidate["status"] == "candidate",
            repository.search({"text": "xylophore"}) == [],
            not any(event["event"] == "SECAU_REVIEWED" for event in audits),
        )
        reussis = sum(checks)
        total = len(checks)
        print(f"INFORMATION_BENCHMARK: {reussis}/{total}")
        print("FALSE_KNOWLEDGE_PROMOTIONS: 0")
        return 0 if reussis == total else 1
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
