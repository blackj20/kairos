"""Interface de commande officielle de K.A.I.R.O.S."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .apprentissage_actif import ApprentissageActif
from .autonomie import MoteurAutonomie, StockageButs
from .causal import MoteurCausal, StockageCausal
from .growup import MoteurGrowUp, StockageGrowUp
from .hypotheses import GestionnaireHypotheses
from .information import ConsolidateurRecherche
from .kernel import Kernel
from .memory import MemoryRepository
from .modeles import Decision
from .self_correction import SelfCorrectionLab
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
    if decision.apprentissage is not None:
        apprentissage_id = (
            decision.apprentissage.get("id")
            or decision.apprentissage.get("hypothesis_id")
        )
        statut = decision.apprentissage.get("statut", "en cours")
        if apprentissage_id:
            print(
                f"{'Hypothèse':<11}: {apprentissage_id} "
                f"({statut})"
            )
        manques = decision.apprentissage.get("manques", ())
        if manques:
            print(f"{'À compléter':<11}: {', '.join(str(manque) for manque in manques)}")
        question = decision.apprentissage.get("question")
        if isinstance(question, dict):
            print(
                f"{'Gain':<11}: {question.get('gain_attendu', 0)}% "
                f"— {question.get('raison', '')}"
            )
    if decision.routage is not None:
        print(
            f"{'Plan':<11}: {decision.routage['id']} "
            f"({decision.routage['statut']})"
        )
        manquantes = decision.routage.get("capacites_manquantes", ())
        if manquantes:
            print(f"{'Manquantes':<11}: {', '.join(manquantes)}")


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


def self_correction(action: str) -> int:
    """Lance ou inspecte le laboratoire SECAU isolé."""

    lab = SelfCorrectionLab(_racine())
    if action == "on":
        payload = lab.run().vers_dict()
    elif action == "status":
        payload = lab.status()
    elif action == "off":
        payload = lab.off()
    else:
        print(f"SELF_CORRECTION_ERROR: action inconnue « {action} »")
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def causal_action(action: str, value: str | None = None) -> int:
    """Exécute, rejoue ou inspecte les expériences causales."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    stockage = StockageCausal(dossier / "causal_experiences.db")
    if action == "status":
        try:
            dernier = stockage.dernier()
            payload = {
                "state": "ready" if dernier is not None else "empty",
                "last_episode": dernier,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        finally:
            stockage.close()

    kernel = Kernel()
    moteur = MoteurCausal(kernel=kernel, stockage=stockage)
    try:
        if action == "run":
            if not str(value or "").strip():
                raise ValueError("--causal-run exige une mission.")
            payload = moteur.executer_message(str(value))
        elif action == "replay":
            if not str(value or "").strip():
                raise ValueError("--causal-replay exige un identifiant.")
            payload = moteur.rejouer(str(value))
        else:
            raise ValueError(f"Action causale inconnue : {action}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, ValueError) as erreur:
        print(f"CAUSAL_ERROR: {erreur}")
        return 1
    finally:
        kernel.close()
        stockage.close()



def goal_action(
    action: str,
    value: str | None = None,
    *,
    goal_id: str | None = None,
    priorite: int = 50,
    max_etapes: int = 3,
    raison: str | None = None,
) -> int:
    """Crée, exécute ou inspecte un but persistant borné."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    buts = StockageButs(dossier / "goals.db")
    causal_store = StockageCausal(dossier / "causal_experiences.db")
    kernel = Kernel()
    causal = MoteurCausal(kernel=kernel, stockage=causal_store)
    moteur = MoteurAutonomie(causal=causal, stockage=buts)
    try:
        if action == "create":
            but = moteur.creer_but(
                str(value or ""),
                priorite=priorite,
                max_etapes=max_etapes,
            )
            payload = moteur.statut(but.id)
        elif action == "run":
            payload = moteur.lancer(
                str(value or ""),
                priorite=priorite,
                max_etapes=max_etapes,
            ).vers_dict()
        elif action == "step":
            payload = moteur.executer_prochaine_etape(
                str(goal_id or value or "")
            ).vers_dict()
        elif action == "status":
            payload = moteur.statut(goal_id)
        elif action == "invalidate":
            identifiant = str(goal_id or value or "")
            but = moteur.invalider(
                identifiant,
                str(raison or "objectif invalidé explicitement"),
            )
            payload = moteur.statut(but.id)
        else:
            raise ValueError(f"Action de but inconnue : {action}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, ValueError) as erreur:
        print(f"GOAL_ERROR: {erreur}")
        return 1
    finally:
        kernel.close()
        causal_store.close()
        buts.close()



def hypothesis_status(hypothesis_id: str | None = None) -> int:
    """Affiche les hypothèses candidates et les éléments manquants."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    repository = MemoryRepository(dossier / "cognition.db")
    try:
        payload = GestionnaireHypotheses(repository).statut(hypothesis_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except KeyError as erreur:
        print(f"HYPOTHESIS_ERROR: hypothèse inconnue {erreur}")
        return 1
    finally:
        repository.close()


def active_learning_status() -> int:
    """Affiche les sessions de consolidation et leur score structurel."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    repository = MemoryRepository(dossier / "cognition.db")
    try:
        print(
            json.dumps(
                ApprentissageActif(repository).statut(),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        repository.close()


def _demande_apprentissage(texte: str) -> bool:
    normalise = " ".join(
        texte.casefold().replace("’", "'").strip(" ?.!").split()
    )
    return normalise in {
        "statut apprentissage",
        "statut de l'apprentissage",
        "ou en est mon apprentissage",
        "où en est mon apprentissage",
    }


def _demande_hypotheses(texte: str) -> bool:
    normalise = " ".join(
        texte.casefold().replace("’", "'").strip(" ?.!").split()
    )
    return normalise in {
        "hypothèses",
        "hypotheses",
        "mes hypothèses",
        "mes hypotheses",
        "montre mes hypothèses",
        "montre mes hypotheses",
    }


def growup_scan() -> int:
    """Analyse la mémoire persistante et produit des plans sans promotion."""

    dossier_memoire = _racine() / "memory"
    dossier_memoire.mkdir(parents=True, exist_ok=True)
    cognitive = MemoryRepository(dossier_memoire / "cognition.db")
    kernel = Kernel(
        persister_decisions=True,
        cognitive_repository=cognitive,
    )
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


def route_plan(action: str, target: str | None = None) -> int:
    """Compile une action en route sans exécuter la moindre capacité."""

    plan = Kernel().routeur.planifier(action, target)
    print(json.dumps(plan.vers_dict(), ensure_ascii=False, indent=2))
    return 0


def secau_status() -> int:
    """Expose les verdicts SECAU conservés dans l'audit cognitif."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    repository = MemoryRepository(dossier / "cognition.db")
    try:
        evenements = [
            evenement
            for evenement in repository.audit_events()
            if evenement.get("event") == "SECAU_REVIEWED"
        ]
        print(
            json.dumps(
                {"count": len(evenements), "events": evenements},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        repository.close()


def research_status() -> int:
    """Liste les candidates de recherche et les verdicts SECAU associés."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    repository = MemoryRepository(dossier / "cognition.db")
    try:
        candidates = [
            {
                "id": item["id"],
                "name": item["payload"].get("name"),
                "score": item["score"],
                "status": item["status"],
            }
            for item in repository.research_candidates()
        ]
        reviews = [
            event
            for event in repository.audit_events()
            if event.get("event") == "SECAU_REVIEWED"
        ]
        print(
            json.dumps(
                {"candidates": candidates, "secau_reviews": reviews},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        repository.close()


def research_review(hypothesis_id: str) -> int:
    """Prépare, teste et soumet une candidate de recherche à SECAU."""

    dossier = _racine() / "memory"
    dossier.mkdir(parents=True, exist_ok=True)
    repository = MemoryRepository(dossier / "cognition.db")
    try:
        result = ConsolidateurRecherche(repository).consolider(hypothesis_id)
        print(json.dumps(result.vers_dict(), ensure_ascii=False, indent=2))
        return 0 if result.secau.verdict.value != "reject" else 1
    except (KeyError, ValueError) as error:
        print(f"RESEARCH_REVIEW_ERROR: {error}")
        return 1
    finally:
        repository.close()


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
        "--causal-run",
        metavar="MISSION",
        help="prédit, exécute, observe et évalue une mission interne",
    )
    actions.add_argument(
        "--causal-replay",
        metavar="EPISODE_ID",
        help="rejoue un épisode causal et détecte une régression",
    )
    actions.add_argument(
        "--causal-status",
        action="store_true",
        help="affiche le dernier épisode causal persistant",
    )
    actions.add_argument(
        "--goal-create",
        metavar="MISSION",
        help="crée un but persistant sans l'exécuter",
    )
    actions.add_argument(
        "--goal-run",
        metavar="MISSION",
        help="exécute un but de façon synchrone et bornée",
    )
    actions.add_argument(
        "--goal-step",
        metavar="GOAL_ID",
        help="exécute exactement la prochaine étape d'un but",
    )
    actions.add_argument(
        "--goal-status",
        action="store_true",
        help="affiche le dernier but ou celui indiqué par --goal-id",
    )
    actions.add_argument(
        "--goal-invalidate",
        metavar="GOAL_ID",
        help="invalide explicitement un but non terminal",
    )
    actions.add_argument(
        "--hypothesis-status",
        action="store_true",
        help="affiche les hypothèses candidates et leurs manques",
    )
    actions.add_argument(
        "--learning-status",
        action="store_true",
        help="affiche la consolidation active et les scores structurels",
    )
    actions.add_argument(
        "--growup-scan",
        action="store_true",
        help="regroupe et planifie les expériences sans les promouvoir",
    )
    actions.add_argument(
        "--route-plan",
        metavar="ACTION",
        help="compile une action en route sans l'exécuter",
    )
    actions.add_argument(
        "--secau-status",
        action="store_true",
        help="affiche les verdicts SECAU audités",
    )
    actions.add_argument(
        "--research-status",
        action="store_true",
        help="liste les candidates de recherche et leurs revues",
    )
    actions.add_argument(
        "--research-review",
        metavar="HYPOTHESIS_ID",
        help="teste une candidate de recherche puis appelle SECAU",
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
    parseur.add_argument(
        "--hypothesis-id",
        help="identifiant précis utilisé avec --hypothesis-status",
    )
    parseur.add_argument("--goal-id", help="identifiant de but pour --goal-status")
    parseur.add_argument(
        "--goal-priority",
        type=int,
        default=50,
        help="priorité du but entre 0 et 100",
    )
    parseur.add_argument(
        "--goal-max-steps",
        type=int,
        default=3,
        help="budget borné de 1 à 20 étapes",
    )
    parseur.add_argument("--reason", help="raison d'une invalidation explicite")
    parseur.add_argument(
        "--route-target",
        help="cible utilisée avec --route-plan",
    )
    parseur.add_argument("--skill-id", help="identifiant explicite de la skill")
    parseur.add_argument(
        "--skill-version",
        default="0.1.0",
        help="version sémantique de la candidate",
    )
    parseur.add_argument("--report-id", help="rapport réussi utilisé à l'activation")
    parseur.add_argument("--approved-by", help="approbateur humain déclaré")
    parseur.add_argument(
        "--online",
        action="store_true",
        help="autorise la recherche Web HTTPS en lecture seule",
    )
    parseur.add_argument(
        "--self-correction",
        choices=("on", "off", "status"),
        help="lance ou inspecte le laboratoire SECAU isolé",
    )
    parseur.add_argument("message", nargs="*")
    return parseur


def main(argv: Sequence[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    if args.self_correction:
        return self_correction(args.self_correction)
    if args.smoke_test:
        return smoke_test()
    if args.causal_run:
        return causal_action("run", args.causal_run)
    if args.causal_replay:
        return causal_action("replay", args.causal_replay)
    if args.causal_status:
        return causal_action("status")
    if args.goal_create:
        return goal_action(
            "create",
            args.goal_create,
            priorite=args.goal_priority,
            max_etapes=args.goal_max_steps,
        )
    if args.goal_run:
        return goal_action(
            "run",
            args.goal_run,
            priorite=args.goal_priority,
            max_etapes=args.goal_max_steps,
        )
    if args.goal_step:
        return goal_action("step", goal_id=args.goal_step)
    if args.goal_status:
        return goal_action("status", goal_id=args.goal_id)
    if args.goal_invalidate:
        return goal_action(
            "invalidate",
            goal_id=args.goal_invalidate,
            raison=args.reason,
        )
    if args.hypothesis_status:
        return hypothesis_status(args.hypothesis_id)
    if args.learning_status:
        return active_learning_status()
    if args.growup_scan:
        return growup_scan()
    if args.route_plan:
        return route_plan(args.route_plan, args.route_target)
    if args.secau_status:
        return secau_status()
    if args.research_status:
        return research_status()
    if args.research_review:
        return research_review(args.research_review)
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

    kernel = Kernel(
        persister_decisions=True,
        allow_network=args.online,
    )
    if args.message:
        message = " ".join(args.message)
        if _demande_hypotheses(message):
            kernel.close()
            return hypothesis_status()
        if _demande_apprentissage(message):
            kernel.close()
            return active_learning_status()
        command = SelfCorrectionLab.parse_command(message)
        if command is not None:
            kernel.close()
            return self_correction(command)
        afficher(kernel.traiter(message))
        kernel.close()
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

        if requete.casefold() in {"quit", "exit"}:
            return 0
        if requete.casefold() == "stop" and not kernel.apprentissage.active:
            return 0
        if not requete:
            continue

        if _demande_hypotheses(requete):
            hypothesis_status()
            continue
        if _demande_apprentissage(requete):
            active_learning_status()
            continue
        command = SelfCorrectionLab.parse_command(requete)
        if command is not None:
            print("Kairos > laboratoire SECAU")
            self_correction(command)
            continue

        if question_en_attente is not None:
            experience = kernel.repondre_a(question_en_attente, requete)
            print(
                "Kairos > Réponse reliée à l'expérience "
                f"{experience.id}. Elle n'est pas encore confirmée."
            )
            hypothese = experience.resolution.get("hypothesis")
            if isinstance(hypothese, dict):
                etat = (
                    "créée"
                    if hypothese.get("creee")
                    else "réutilisée"
                )
                print(
                    f"Kairos > Hypothèse {etat} : {hypothese['id']} "
                    f"({hypothese['statut']})."
                )
                manques = hypothese.get("manques", ())
                if manques:
                    print(
                        "Kairos > Pour la vérifier, il manque : "
                        + ", ".join(str(item) for item in manques)
                        + "."
                    )
                print(
                    "Kairos > Consulte-la avec : "
                    f"kairos --hypothesis-status --hypothesis-id "
                    f"{hypothese['id']}"
                )
                apprentissage_actif = kernel.apprentissage_actif.demarrer(
                    str(hypothese["id"])
                )
                print("Kairos > " + apprentissage_actif.texte)
            else:
                print(
                    "Kairos > Réponse enregistrée comme expérience "
                    f"{experience.id}. Elle ne contient pas encore "
                    "d'explication permettant une hypothèse."
                )
            question_en_attente = None
            continue

        decision = kernel.traiter(requete)
        afficher(decision)
        question_en_attente = decision.question_id


if __name__ == "__main__":
    raise SystemExit(main())
