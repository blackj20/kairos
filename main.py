"""Interface en ligne de commande du prototype K.A.I.R.O.S."""

from __future__ import annotations

import sys

from kairos import Decision, Kernel


def afficher(decision: Decision) -> None:
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


def main() -> None:
    kernel = Kernel(persister_decisions=True)

    if len(sys.argv) > 1:
        afficher(kernel.traiter(" ".join(sys.argv[1:])))
        return

    print("K.A.I.R.O.S. prototype — écrivez quit pour quitter.")
    question_en_attente: str | None = None
    while True:
        try:
            attente = kernel.attente_pedagogique
            invite = (
                f"Vous [{attente}] > "
                if attente is not None
                else "Vous > "
            )
            requete = input(invite).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if requete.casefold() in {"quit", "exit", "stop"}:
            break
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
    main()
