"""Tests du graphe sens.json et de l'auto-amélioration verbale."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.connaissances import Connaissances
from kairos.learning import CreatorLearningPipeline
from kairos.memory import MemoryRepository
from kairos.relations_verbes import MemoireRelationsVerbes


class TestRelationsSemantiques(unittest.TestCase):
    """Prouve les relations statiques, contextuelles et apprises."""

    @staticmethod
    def _resolver_deploie(texte: str) -> str | None:
        return "installer" if texte.casefold().startswith("deploie ") else None

    def test_put_and_add_software_mean_install(self) -> None:
        """Les formulations quotidiennes convergent vers l'action canonique."""

        for request in (
            "mets python",
            "met docker",
            "ajoute python",
            "rajoute vscode",
        ):
            with self.subTest(request=request):
                decision = Kernel().traiter(request)
                self.assertEqual("ordre", decision.analyse.type_requete.valeur)
                self.assertEqual("installer", decision.analyse.action.valeur)
                self.assertEqual("competence", decision.route)
                self.assertIsNone(decision.question_id)

    def test_context_prevents_wrong_installation_meaning(self) -> None:
        """« mettre » et « ajouter » restent génériques hors logiciel."""

        mettre = Kernel().traiter("mets fichier")
        ajouter = Kernel().traiter("ajoute fichier")
        self.assertEqual("mettre", mettre.analyse.action.valeur)
        self.assertEqual("ajouter", ajouter.analyse.action.valeur)
        self.assertNotEqual("installer", mettre.analyse.action.valeur)
        self.assertNotEqual("installer", ajouter.analyse.action.valeur)

    def test_fuzzy_similarity_outside_directive_is_not_an_action(self) -> None:
        """Un adjectif proche d'un verbe ne doit pas créer un faux ordre."""

        decision = Kernel().traiter("cette marche est cassée")
        self.assertEqual("affirmation", decision.analyse.type_requete.valeur)
        self.assertIsNone(decision.analyse.action.valeur)
        self.assertEqual("repondre", decision.route)

    def test_remove_software_maps_to_delete(self) -> None:
        """La relation contextuelle peut aussi relier retirer à supprimer."""

        decision = Kernel().traiter("retire docker")
        self.assertEqual("supprimer", decision.analyse.action.valeur)

    def test_extended_everyday_relational_verbs_are_understood(self) -> None:
        """Les familles état, liaison, maintenance et archive sont couvertes."""

        cases = {
            "active terminal": "activer",
            "désactive terminal": "desactiver",
            "connecte terminal": "connecter",
            "répare fichier": "reparer",
            "trie dossier": "trier",
            "compresse dossier": "compresser",
            "extrais fichier": "extraire",
            "imprime fichier": "imprimer",
        }
        for request, expected in cases.items():
            with self.subTest(request=request):
                decision = Kernel().traiter(request)
                self.assertEqual(expected, decision.analyse.action.valeur)
                self.assertEqual("competence", decision.route)

    def test_creator_answer_becomes_candidate_then_confirmed(self) -> None:
        """Question → candidate → tests → SECAU → réutilisation."""

        kernel = Kernel()
        before = kernel.traiter("deploie python")
        self.assertEqual("clarification", before.route)
        self.assertIn("deploie", before.question)

        experience = kernel.repondre_a(
            before.question_id,
            "installer",
            acteur="creator",
        )
        candidate = experience.resolution["candidate_semantic_relation"]
        self.assertEqual("deploie", candidate["source"])
        self.assertEqual("installer", candidate["target"])
        self.assertEqual("candidate", candidate["status"])
        self.assertIsNone(
            kernel.comprendre.connaissances.relations_verbes.obtenir("deploie")
        )
        still_unknown = kernel.traiter("deploie python")
        self.assertEqual("clarification", still_unknown.route)

        repository = MemoryRepository()
        result = CreatorLearningPipeline(
            repository,
            kernel.comprendre.connaissances.relations_verbes,
        ).consolidate_relation(
            experience,
            examples=("deploie python", "deploie docker", "deploie vscode"),
            counterexamples=("supprime python", "ouvre terminal"),
            resolver=self._resolver_deploie,
            regressions=(
                lambda: Kernel().traiter("installe python").analyse.action.valeur
                == "installer",
            ),
        )
        self.assertEqual("promote", result.secau.verdict.value)

        after = kernel.traiter("deploie python")
        self.assertEqual("installer", after.analyse.action.valeur)
        self.assertEqual("competence", after.route)
        self.assertIsNone(after.question_id)
        repository.close()

    def test_ordinary_user_cannot_teach_kernel(self) -> None:
        """Une réponse utilisateur reste une expérience, pas une relation."""

        kernel = Kernel()
        decision = kernel.traiter("deploie python")
        experience = kernel.repondre_a(
            decision.question_id,
            "installer",
            acteur="user",
        )
        self.assertNotIn(
            "candidate_semantic_relation",
            experience.resolution,
        )
        self.assertIsNone(
            kernel.comprendre.connaissances.relations_verbes.obtenir("deploie")
        )

    def test_confirmed_relation_persists_across_sessions(self) -> None:
        """Seule une relation consolidée devient durable entre deux sessions."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "relations.json"
            relations = MemoireRelationsVerbes(path)
            first = Kernel(
                comprendre=Comprendre(
                    Connaissances(relations_verbes=relations)
                )
            )
            question = first.traiter("deploie python")
            experience = first.repondre_a(question.question_id, "installer")

            repository = MemoryRepository()
            result = CreatorLearningPipeline(
                repository,
                relations,
            ).consolidate_relation(
                experience,
                examples=("deploie python", "deploie docker", "deploie vscode"),
                counterexamples=("supprime python", "ouvre terminal"),
                resolver=self._resolver_deploie,
            )
            self.assertEqual("promote", result.secau.verdict.value)
            repository.close()

            second = Kernel(
                comprendre=Comprendre(
                    Connaissances(
                        relations_verbes=MemoireRelationsVerbes(path)
                    )
                )
            )
            decision = second.traiter("deploie python")
            self.assertEqual("installer", decision.analyse.action.valeur)
            self.assertIsNone(decision.question_id)

    def test_internet_teaching_requires_two_distinct_https_domains(self) -> None:
        """Une page ou un seul domaine Internet ne suffit jamais."""

        kernel = Kernel()
        with self.assertRaises(ValueError):
            kernel.enseigner_relation_verbe(
                "provisionne",
                "installer",
                sources=("https://example.test/source-1",),
            )
        with self.assertRaises(ValueError):
            kernel.enseigner_relation_verbe(
                "provisionne",
                "installer",
                sources=(
                    "https://example.test/source-1",
                    "https://example.test/source-2",
                ),
            )
        with self.assertRaises(ValueError):
            kernel.enseigner_relation_verbe(
                "provisionne",
                "installer",
                sources=(
                    "http://example-a.test/source-1",
                    "https://example-b.test/source-2",
                ),
            )
        kernel.enseigner_relation_verbe(
            "provisionne",
            "installer",
            sources=(
                "https://example-a.test/source-1",
                "https://example-b.test/source-2",
            ),
        )
        decision = kernel.traiter("provisionne python")
        self.assertEqual("installer", decision.analyse.action.valeur)
        self.assertIsNone(decision.question_id)

    def test_sens_graph_contains_typed_auditable_relations(self) -> None:
        """Chaque arête essentielle possède type, cible, score et preuve."""

        relations = Connaissances().relations_semantiques
        identifiers = {relation["id"] for relation in relations}
        self.assertIn("mettre_logiciel_installer", identifiers)
        self.assertIn("ajouter_logiciel_installer", identifiers)
        for relation in relations:
            self.assertIn("source", relation)
            self.assertIn("relation", relation)
            self.assertIn("target", relation)
            self.assertTrue(0 <= int(relation["score"]) <= 100)
            if relation["relation"] == "action_equivalente":
                self.assertTrue(relation.get("source_refs"))


if __name__ == "__main__":
    unittest.main()
