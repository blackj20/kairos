"""Interface de commande officielle de K.A.I.R.O.S."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .kernel import Kernel
from .modeles import Decision


def afficher(decision: Decision) -> None:
    """Affiche une décision déjà produite par le kernel."""

    analyse = decision.analyse

    def ligne(titre: str, valeur: str | None, score: int) -> None:
        print(f"{titre:<11}: {valeur or 'aucune'} ({score}%)")

    ligne("Type", analyse.type_requete.valeur, analyse.type_requete.score)
    ligne("Démarche", analyse.demarche.valeur, analyse.demarche.score)
    ligne("Action", analyse.action.valeur, analyse.action.score)
    ligne("Cible", analyse.cible.valeur, analyse.cible.score)
    ligne(
        "Alternative",
        analyse.alternative_type.valeur,
        analyse.alternative_type.score,
    )
    ligne(
        "Vérifié",
        "oui" if analyse.verification.valide else "non",
        analyse.verification.score,
    )
    print(f"{'Route':<11}: {decision.route}")
    print(f"{'Réponse':<11}: {decision.reponse}")


def smoke_test() -> int:
    """Vérifie le démarrage, le chargement et une analyse minimale."""

    kernel = Kernel()
    decision = kernel.traiter("salut cv ?")
    if decision.analyse.type_requete.valeur != "question":
        print("SMOKE_TEST_FAILED: intention inattendue")
        return 1
    if not decision.reponse:
        print("SMOKE_TEST_FAILED: réponse absente")
        return 1
    print("SMOKE_TEST_OK: kernel, connaissances, décision et réponse opérationnels")
    return 0


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(prog="kairos")
    parseur.add_argument(
        "--smoke-test",
        action="store_true",
        help="vérifie le démarrage et quitte avec un code mesurable",
    )
    parseur.add_argument("message", nargs="*")
    return parseur


def main(argv: Sequence[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    if args.smoke_test:
        return smoke_test()

    kernel = Kernel(persister_decisions=True)
    if args.message:
        afficher(kernel.traiter(" ".join(args.message)))
        return 0

    print("K.A.I.R.O.S. prototype — écrivez quit pour quitter.")
    question_en_attente: str | None = None
    while True:
        try:
            attente = kernel.attente_pedagogique
            invite = f"Vous [{attente}] > " if attente else "Vous > "
            requete = input(invite).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if requete.casefold() in {"quit", "exit", "stop"}:
            return 0
        if not requete:
            continue

        if question_en_attente is not None:
            experience = kernel.repondre_a(question_en_attente, requete)
            print(
                "Kairos > Réponse reliée à l'expérience "
                f"{experience.id}. Elle n'est pas encore confirmée."
            )
            question_en_attente = None
            continue

        decision = kernel.traiter(requete)
        afficher(decision)
        question_en_attente = decision.question_id


if __name__ == "__main__":
    raise SystemExit(main())
