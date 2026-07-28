"""Interface de commande officielle de K.A.I.R.O.S."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .growup import MoteurGrowUp, StockageGrowUp
from .kernel import Kernel
from .memory import MemoryRepository
from .modeles import Decision
from .skills import SkillFactory, SkillFactoryStore, SkillRegistry
from .soi import ConnaissanceDeSoi


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


def _racine() -> Path:
    return Path(__file__).resolve().parent.parent


def growup_scan() -> int:
    """Analyse la mémoire persistante et produit des plans sans promotion."""

    dossier_memoire = _racine() / "memory"
    dossier_memoire.mkdir(parents=True, exist_ok=True)
    kernel = Kernel(persister_decisions=True)
    cognitive = MemoryRepository(dossier_memoire / "cognition.db")
    stockage = StockageGrowUp(dossier_memoire / "growup.db")
    try:
        moteur = MoteurGrowUp(
            kernel.moteur_decision.stockage,
            cognitive_repository=cognitive,
            growup_storage=stockage,
            relations_memory=kernel.comprendre.connaissances.relations_verbes,
        )
        rapport = moteur.analyser()
        print(json.dumps(rapport.vers_dict(), ensure_ascii=False, indent=2))
        return 0
    finally:
        cognitive.close()
        stockage.close()


def _ouvrir_skill_factory() -> tuple[
    SkillFactory,
    StockageGrowUp,
    SkillFactoryStore,
]:
    racine = _racine()
    memoire = racine / "memory"
    memoire.mkdir(parents=True, exist_ok=True)
    growup = StockageGrowUp(memoire / "growup.db")
    store = SkillFactoryStore(memoire / "skills.db")
    registre = SkillRegistry(memoire / "skill_registry.json")
    createur = str(ConnaissanceDeSoi(racine).creator["name"])
    factory = SkillFactory(
        growup,
        candidates_dir=racine / "skills" / "candidates",
        active_dir=racine / "skills" / "active",
        registry=registre,
        store=store,
        authorized_approvers=(createur,),
    )
    return factory, growup, store


def _skill_action(action: str, **options: Any) -> int:
    factory, growup, store = _ouvrir_skill_factory()
    try:
        if action == "scan":
            payload = {
                "eligible_plans": [
                    plan.vers_dict() for plan in factory.eligible_plans()
                ],
                "candidates": [
                    candidate.vers_dict() for candidate in store.candidates()
                ],
                "active_skills": factory.registry.candidates({}),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if action == "generate":
            candidate = factory.generate_from_plan(
                str(options["plan_id"]),
                skill_id=options.get("skill_id"),
                version=str(options.get("version") or "0.1.0"),
            )
            print(json.dumps(candidate.vers_dict(), ensure_ascii=False, indent=2))
            return 0
        if action == "validate":
            report = factory.validate_candidate(str(options["candidate_id"]))
            print(json.dumps(report.vers_dict(), ensure_ascii=False, indent=2))
            return 0 if report.passed else 1
        if action == "activate":
            report_id = options.get("report_id")
            approved_by = options.get("approved_by")
            if not report_id or not approved_by:
                raise ValueError(
                    "--skill-activate exige --report-id et --approved-by."
                )
            result = factory.activate_candidate(
                str(options["candidate_id"]),
                str(report_id),
                approved_by=str(approved_by),
            )
            print(json.dumps(result.vers_dict(), ensure_ascii=False, indent=2))
            return 0
        if action == "rollback":
            approved_by = options.get("approved_by")
            if not approved_by:
                raise ValueError("--skill-rollback exige --approved-by.")
            result = factory.rollback(
                str(options["skill_id"]),
                approved_by=str(approved_by),
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        raise ValueError(f"Action Skill Factory inconnue : {action}")
    except (KeyError, ValueError, PermissionError, FileExistsError) as erreur:
        print(f"SKILL_FACTORY_ERROR: {erreur}")
        return 1
    finally:
        store.close()
        growup.close()


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(prog="kairos")
    actions = parseur.add_mutually_exclusive_group()
    actions.add_argument(
        "--smoke-test",
        action="store_true",
        help="vérifie le démarrage et quitte avec un code mesurable",
    )
    actions.add_argument(
        "--growup-scan",
        action="store_true",
        help="regroupe et planifie les expériences sans les promouvoir",
    )
    actions.add_argument(
        "--skill-factory-scan",
        action="store_true",
        help="liste les plans promus, candidates et skills actives",
    )
    actions.add_argument(
        "--skill-generate",
        metavar="PLAN_ID",
        help="génère une candidate inactive depuis un plan GrowUp promu",
    )
    actions.add_argument(
        "--skill-validate",
        metavar="CANDIDATE_ID",
        help="analyse et teste une candidate sans l'activer",
    )
    actions.add_argument(
        "--skill-activate",
        metavar="CANDIDATE_ID",
        help="active explicitement une candidate validée",
    )
    actions.add_argument(
        "--skill-rollback",
        metavar="SKILL_ID",
        help="restaure la version active précédente",
    )
    parseur.add_argument("--skill-id", help="identifiant explicite de la skill")
    parseur.add_argument(
        "--skill-version",
        default="0.1.0",
        help="version sémantique de la candidate",
    )
    parseur.add_argument("--report-id", help="rapport réussi utilisé à l'activation")
    parseur.add_argument("--approved-by", help="approbateur humain déclaré")
    parseur.add_argument("message", nargs="*")
    return parseur


def main(argv: Sequence[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    if args.smoke_test:
        return smoke_test()
    if args.growup_scan:
        return growup_scan()
    if args.skill_factory_scan:
        return _skill_action("scan")
    if args.skill_generate:
        return _skill_action(
            "generate",
            plan_id=args.skill_generate,
            skill_id=args.skill_id,
            version=args.skill_version,
        )
    if args.skill_validate:
        return _skill_action("validate", candidate_id=args.skill_validate)
    if args.skill_activate:
        return _skill_action(
            "activate",
            candidate_id=args.skill_activate,
            report_id=args.report_id,
            approved_by=args.approved_by,
        )
    if args.skill_rollback:
        return _skill_action(
            "rollback",
            skill_id=args.skill_rollback,
            approved_by=args.approved_by,
        )

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
