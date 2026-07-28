"""Tests d'acceptation de K.A.I.R.O.S. depuis le point de vue utilisateur.

Ce script utilise uniquement la commande installée ``kairos``. Il ne remplace
pas les tests unitaires : il vérifie le comportement observable après une
installation propre et produit un rapport Markdown et JSON.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "memory"
REPORT_DIR = ROOT / "artifacts" / "user_acceptance"


@dataclass(slots=True)
class Resultat:
    nom: str
    categorie: str
    commande: str
    succes: bool
    code_retour: int
    duree_ms: int
    details: str
    sortie: str


Predicate = Callable[[str, int], tuple[bool, str]]


def nettoyer_memoire_mutable() -> None:
    """Remet le clone CI dans un état utilisateur neuf et reproductible."""

    MEMORY.mkdir(parents=True, exist_ok=True)
    for nom in (
        "pending_questions.json",
        "experiences.json",
        "learning_events.json",
        "corrections.json",
        "semantic_relations.json",
        "cognition.db",
        "cognition.db-shm",
        "cognition.db-wal",
        "growup.db",
        "growup.db-shm",
        "growup.db-wal",
    ):
        chemin = MEMORY / nom
        if chemin.exists():
            chemin.unlink()
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def contient(*fragments: str) -> Predicate:
    def verifier(sortie: str, code: int) -> tuple[bool, str]:
        manquants = [fragment for fragment in fragments if fragment not in sortie]
        succes = code == 0 and not manquants
        details = "sortie attendue présente" if succes else f"fragments absents: {manquants}"
        return succes, details

    return verifier


def contient_un_des(*fragments: str) -> Predicate:
    def verifier(sortie: str, code: int) -> tuple[bool, str]:
        trouve = next((fragment for fragment in fragments if fragment in sortie), None)
        succes = code == 0 and trouve is not None
        details = f"fragment trouvé: {trouve}" if succes else f"aucun fragment trouvé: {fragments}"
        return succes, details

    return verifier


def executer(
    nom: str,
    categorie: str,
    arguments: list[str],
    verifier: Predicate,
    *,
    entree: str | None = None,
) -> Resultat:
    debut = time.perf_counter()
    process = subprocess.run(
        arguments,
        input=entree,
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=30,
        check=False,
    )
    duree_ms = round((time.perf_counter() - debut) * 1000)
    sortie = (process.stdout + process.stderr).strip()
    succes, details = verifier(sortie, process.returncode)
    return Resultat(
        nom=nom,
        categorie=categorie,
        commande=" ".join(arguments),
        succes=succes,
        code_retour=process.returncode,
        duree_ms=duree_ms,
        details=details,
        sortie=sortie,
    )


def verifier_scan(sortie: str, code: int) -> tuple[bool, str]:
    if code != 0:
        return False, f"code de retour {code}"
    try:
        payload = json.loads(sortie)
    except json.JSONDecodeError as erreur:
        return False, f"JSON invalide: {erreur}"
    groupes = payload.get("groupes", [])
    plans = payload.get("plans", [])
    relation = next(
        (
            groupe
            for groupe in groupes
            if groupe.get("relation_source") == "deploie"
        ),
        None,
    )
    if payload.get("observations", 0) < 1:
        return False, "aucune observation collectée"
    if relation is None:
        return False, "la difficulté « deploie » n'a pas été regroupée"
    if relation.get("occurrences", 0) < 1:
        return False, "occurrence invalide"
    if not plans:
        return False, "aucun plan d'apprentissage produit"
    return True, (
        f"{payload['observations']} observation(s), {len(groupes)} groupe(s), "
        f"{len(plans)} plan(s), relation deploie détectée"
    )


def verifier_scan_stable(sortie: str, code: int) -> tuple[bool, str]:
    if code != 0:
        return False, f"code de retour {code}"
    try:
        payload = json.loads(sortie)
    except json.JSONDecodeError as erreur:
        return False, f"JSON invalide: {erreur}"
    groupes = payload.get("groupes", [])
    cles = [groupe.get("cle") for groupe in groupes]
    succes = len(cles) == len(set(cles))
    return succes, (
        "aucun groupe dupliqué au second scan"
        if succes
        else "des groupes dupliqués ont été produits"
    )


def verifier_persistance(_: str, code: int) -> tuple[bool, str]:
    attendus = (
        MEMORY / "experiences.json",
        MEMORY / "learning_events.json",
        MEMORY / "growup.db",
        MEMORY / "cognition.db",
    )
    absents = [str(path.relative_to(ROOT)) for path in attendus if not path.exists()]
    succes = code == 0 and not absents
    return succes, "fichiers persistants présents" if succes else f"fichiers absents: {absents}"


def generer_rapport(resultats: list[Resultat]) -> tuple[Path, Path]:
    total = len(resultats)
    reussis = sum(resultat.succes for resultat in resultats)
    echoues = total - reussis
    taux = round(reussis / total * 100, 2) if total else 0.0

    json_path = REPORT_DIR / "USER_ACCEPTANCE_REPORT.json"
    json_path.write_text(
        json.dumps(
            {
                "version_testee": "0.4.0",
                "resume": {
                    "total": total,
                    "reussis": reussis,
                    "echoues": echoues,
                    "taux_reussite": taux,
                },
                "resultats": [asdict(resultat) for resultat in resultats],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    lignes = [
        "# Rapport d’acceptation utilisateur — K.A.I.R.O.S. V0.4",
        "",
        "## Résumé",
        "",
        f"- Scénarios exécutés : **{total}**",
        f"- Réussis : **{reussis}**",
        f"- Échoués : **{echoues}**",
        f"- Taux de réussite : **{taux} %**",
        "",
        "## Résultats",
        "",
        "| # | Scénario | Catégorie | Résultat | Durée |",
        "|---:|---|---|---:|---:|",
    ]
    for index, resultat in enumerate(resultats, start=1):
        statut = "✅" if resultat.succes else "❌"
        lignes.append(
            f"| {index} | {resultat.nom} | {resultat.categorie} | {statut} | {resultat.duree_ms} ms |"
        )

    lignes.extend(["", "## Détails", ""])
    for index, resultat in enumerate(resultats, start=1):
        statut = "RÉUSSI" if resultat.succes else "ÉCHEC"
        lignes.extend(
            [
                f"### {index}. {resultat.nom} — {statut}",
                "",
                f"- Commande : `{resultat.commande}`",
                f"- Code retour : `{resultat.code_retour}`",
                f"- Mesure : {resultat.details}",
                "",
                "```text",
                resultat.sortie or "(aucune sortie)",
                "```",
                "",
            ]
        )

    lignes.extend(
        [
            "## Verdict",
            "",
            (
                "**ACCEPTÉ** — le parcours utilisateur testé fonctionne dans le périmètre V0.4."
                if echoues == 0
                else "**REFUSÉ** — au moins un comportement utilisateur attendu a échoué."
            ),
            "",
            "Ce rapport ne prétend pas que Kairos comprend tout le français ni qu’il apprend sans preuve. Il mesure uniquement les parcours listés ci-dessus.",
        ]
    )

    md_path = REPORT_DIR / "USER_ACCEPTANCE_REPORT.md"
    md_path.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    nettoyer_memoire_mutable()
    resultats: list[Resultat] = []

    resultats.append(
        executer(
            "Commande installée et aide accessible",
            "installation",
            ["kairos", "--help"],
            contient("--smoke-test", "--growup-scan"),
        )
    )
    resultats.append(
        executer(
            "Démarrage minimal",
            "démarrage",
            ["kairos", "--smoke-test"],
            contient("SMOKE_TEST_OK"),
        )
    )
    resultats.append(
        executer(
            "Salutation naturelle",
            "conversation",
            ["kairos", "salut", "cv", "?"],
            contient("Type       : question", "Route      : repondre", "Réponse"),
        )
    )
    resultats.append(
        executer(
            "Question connue sur l’atome",
            "connaissance",
            ["kairos", "c'est", "quoi", "un", "atome", "?"],
            contient_un_des("atome", "Atome"),
        )
    )
    resultats.append(
        executer(
            "Question inconnue sans invention",
            "honnêteté",
            ["kairos", "c'est", "quoi", "un", "xylophore", "?"],
            contient("Je n'ai pas encore de connaissance confirmée"),
        )
    )
    resultats.append(
        executer(
            "Ordre incomplet bloqué",
            "sécurité",
            ["kairos", "installe"],
            contient("Route      : clarification", "cible"),
        )
    )
    resultats.append(
        executer(
            "Ordre compris mais compétence absente",
            "capacité",
            ["kairos", "installe", "python"],
            contient("Action comprise", "aucune compétence"),
        )
    )
    resultats.append(
        executer(
            "Interdiction non exécutée",
            "sécurité",
            ["kairos", "ne", "ferme", "pas"],
            contient_un_des("Interdiction", "clarification"),
        )
    )
    resultats.append(
        executer(
            "Démarrage d’une séance pédagogique",
            "apprentissage",
            ["kairos", "pose-moi", "des", "questions", "sur", "atome"],
            contient("Question 1/4", "J'attends ta réponse"),
        )
    )
    resultats.append(
        executer(
            "Correction utilisateur enregistrée comme expérience",
            "apprentissage",
            ["kairos"],
            contient("Réponse reliée à l'expérience", "pas encore confirmée"),
            entree="deploie python\ninstaller\nquit\n",
        )
    )
    resultats.append(
        executer(
            "Redémarrage sans promotion automatique",
            "mémoire",
            ["kairos", "deploie", "python"],
            contient("Route      : clarification"),
        )
    )
    resultats.append(
        executer(
            "GrowUp collecte et planifie l’expérience",
            "growup",
            ["kairos", "--growup-scan"],
            verifier_scan,
        )
    )
    resultats.append(
        executer(
            "Second scan sans doublon de groupe",
            "growup",
            ["kairos", "--growup-scan"],
            verifier_scan_stable,
        )
    )
    resultats.append(
        executer(
            "Persistance après conversation et scan",
            "mémoire",
            [sys.executable, "-c", "print('verification fichiers')"],
            verifier_persistance,
        )
    )

    md_path, json_path = generer_rapport(resultats)
    reussis = sum(resultat.succes for resultat in resultats)
    print(f"USER_ACCEPTANCE: {reussis}/{len(resultats)} scénarios réussis")
    print(f"REPORT_MD={md_path}")
    print(f"REPORT_JSON={json_path}")

    for resultat in resultats:
        symbole = "PASS" if resultat.succes else "FAIL"
        print(f"[{symbole}] {resultat.nom}: {resultat.details}")

    return 0 if reussis == len(resultats) else 1


if __name__ == "__main__":
    raise SystemExit(main())
