"""Tests du graphe sens.json et de l'auto-amélioration verbale."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.connaissances import Connaissances
from kairos.relations_verbes import MemoireRelationsVerbes


class TestRelationsSemantiques(unittest.TestCase):
    """Prouve les relations statiques, contextuelles et apprises."""

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

    def test_creator_answer_teaches_unknown_verb(self) -> None:
        """Question → enseignement → réutilisation prouve l'auto-amélioration."""

        kernel = Kernel()
        before = kernel.traiter("deploie python")
        self.assertEqual("clarification", before.route)
        self.assertIn("deploie", before.question)

        experience = kernel.repondre_a(
            before.question_id,
            "installer",
            acteur="creator",
        )
        learned = experience.resolution["learned_semantic_relation"]
        self.assertEqual("deploie", learned["source"])
        self.assertEqual("installer", learned["target"])

        after = kernel.traiter("deploie python")
        self.assertEqual("installer", after.analyse.action.valeur)
        self.assertEqual("competence", after.route)
        self.assertIsNone(after.question_id)
        self.assertGreater(
            after.evaluation["score_global"],
            before.evaluation["score_global"],
        )

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
            "learned_semantic_relation",
            experience.resolution,
        )
        self.assertIsNone(
            kernel.comprendre.connaissances.relations_verbes.obtenir("deploie")
        )

    def test_learned_relation_persists_across_sessions(self) -> None:
        """Une mémoire fichier rend la croissance durable et vérifiable."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "relations.json"
            first = Kernel(
                comprendre=Comprendre(
                    Connaissances(
                        relations_verbes=MemoireRelationsVerbes(path)
                    )
                )
            )
            question = first.traiter("deploie python")
            first.repondre_a(question.question_id, "installer")

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

    def test_internet_teaching_requires_two_sources(self) -> None:
        """Une page Internet isolée ne suffit pas à enrichir le cerveau."""

        kernel = Kernel()
        with self.assertRaises(ValueError):
            kernel.enseigner_relation_verbe(
                "provisionne",
                "installer",
                sources=("https://example.test/source-1",),
            )
        kernel.enseigner_relation_verbe(
            "provisionne",
            "installer",
            sources=(
                "https://example.test/source-1",
                "https://example.test/source-2",
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
