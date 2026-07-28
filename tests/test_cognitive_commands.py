"""Tests des ordres cognitifs et des résultats pédagogiques concrets."""

from __future__ import annotations

import unittest

from kairos import Kernel
from kairos.knowledge_base import KnowledgeBase


class TestCognitiveCommands(unittest.TestCase):
    """Vérifie questions, réponses sourcées et branches de connaissance."""

    def test_ask_me_questions_uses_reflechir(self) -> None:
        decision = Kernel().traiter("pose-moi des questions")
        self.assertEqual("competence", decision.route)
        self.assertEqual("poser", decision.analyse.action.valeur)
        self.assertIn("Question 1/4", decision.reponse)
        self.assertIn("Comment définir", decision.reponse)
        self.assertIn("J'attends ta réponse", decision.reponse)
        self.assertNotIn("Question 2/4", decision.reponse)

    def test_atom_question_returns_sourced_clear_answer(self) -> None:
        decision = Kernel().traiter("c'est quoi un atome ?")
        self.assertEqual("repondre", decision.route)
        self.assertIn("noyau", decision.reponse)
        self.assertIn("électrons", decision.reponse)
        self.assertIn("goldbook.iupac.org", decision.reponse)

        item = KnowledgeBase().find("c'est quoi un atome ?")
        self.assertGreaterEqual(len(item["relations"]), 4)
        self.assertGreaterEqual(len(item["examples"]), 3)
        self.assertGreaterEqual(len(item["counterexamples"]), 2)

    def test_python_print_question_returns_executable_example(self) -> None:
        decision = Kernel().traiter(
            "comment faire un print avec python ?"
        )
        self.assertEqual("repondre", decision.route)
        self.assertIn('print("Bonjour")', decision.reponse)
        self.assertIn("sep", decision.reponse)
        self.assertIn("docs.python.org", decision.reponse)

    def test_learn_python_returns_curriculum_and_exercise(self) -> None:
        decision = Kernel().traiter("apprends python")
        self.assertEqual("repondre", decision.route)
        self.assertEqual("apprendre", decision.analyse.action.valeur)
        self.assertIn("Premier exercice", decision.reponse)
        self.assertIn("print(nom)", decision.reponse)

    def test_natural_learning_variants_return_concrete_results(self) -> None:
        """Les formulations découvertes pendant la session client restent réparées."""

        cases = (
            (
                "explique-moi la différence entre un atome et une molécule",
                ("molécule", "deux atomes"),
            ),
            (
                "comment afficher une variable en python ?",
                ('print("Bonjour")', "sep"),
            ),
            (
                "apprends-moi python",
                ("Premier exercice", "print(nom)"),
            ),
            (
                "donne-moi un exercice python",
                ("input()", "Résultat attendu"),
            ),
            (
                "pourquoi le ciel est bleu ?",
                ("diffusion de Rayleigh", "nesdis.noaa.gov"),
            ),
            (
                "qu'est-ce qu'une boucle python ?",
                ("for nombre", "while"),
            ),
            (
                "comment créer une fonction python ?",
                ("def saluer", "return"),
            ),
        )
        for request, expected_fragments in cases:
            with self.subTest(request=request):
                decision = Kernel().traiter(request)
                self.assertIn(decision.route, {"repondre", "competence"})
                for fragment in expected_fragments:
                    self.assertIn(fragment, decision.reponse)

    def test_questions_explicit_topic_overrides_old_unknown(self) -> None:
        """« sur python » doit primer sur un ancien événement d'apprentissage."""

        kernel = Kernel()
        kernel.traiter("blorpe")
        decision = kernel.traiter("pose-moi des questions sur python")
        self.assertIn("« python »", decision.reponse)
        self.assertNotIn("blorpe", decision.reponse)

    def test_question_session_waits_corrects_and_advances_one_by_one(self) -> None:
        """Chaque réponse est évaluée avant que la question suivante apparaisse."""

        kernel = Kernel()
        kernel.traiter("bonjjour")
        first = kernel.traiter("pose-moi des questions")
        self.assertIn("corrigé le sujet en « bonjour »", first.reponse)
        self.assertIn("Question 1/4", first.reponse)
        self.assertIn("Type de réponse attendu : définition", first.reponse)
        self.assertEqual(
            "définition : une phrase d'au moins 5 mots",
            kernel.attente_pedagogique,
        )

        too_short = kernel.traiter("une salutation")
        self.assertIn("Réponse à améliorer", too_short.reponse)
        self.assertIn("même question", too_short.reponse)
        self.assertNotIn("Question 2/4", too_short.reponse)

        accepted = kernel.traiter(
            "bonjour est une formule utilisée pour saluer une personne"
        )
        self.assertIn("Proposition corrigée", accepted.reponse)
        self.assertIn("Question 2/4", accepted.reponse)
        self.assertIn("trois exemples", accepted.reponse)
        self.assertEqual(
            "3 exemples distincts, séparés par des virgules",
            kernel.attente_pedagogique,
        )

        examples_short = kernel.traiter("le matin et le soir")
        self.assertIn("trois exemples distincts", examples_short.reponse)
        self.assertNotIn("Question 3/4", examples_short.reponse)

        examples = kernel.traiter(
            "bonjour le matin, bonjour à un voisin, bonjour à un collègue"
        )
        self.assertIn("Question 3/4", examples.reponse)
        self.assertIn("ne s'applique", examples.reponse)

    def test_put_file_in_folder_resolves_to_move(self) -> None:
        """La préposition « dans » spécialise mettre en déplacer."""

        decision = Kernel().traiter("mets le fichier dans le dossier")
        self.assertEqual("deplacer", decision.analyse.action.valeur)
        self.assertEqual("fichier", decision.analyse.cible.valeur)

    def test_unknown_question_returns_a_search_method_not_an_empty_answer(self) -> None:
        """Une question inconnue indique comment trouver et vérifier la réponse."""

        decision = Kernel().traiter("comment marche console.log en js")
        self.assertEqual("repondre", decision.route)
        self.assertIn("MDN console.log en JavaScript", decision.reponse)
        self.assertIn("spécification ECMAScript", decision.reponse)
        self.assertIn("console du navigateur", decision.reponse)
        self.assertIn("cherche en ligne | sujet=console.log en JavaScript", decision.reponse)
        self.assertNotIn(
            "Je n'ai pas encore assez d'indices",
            decision.reponse,
        )


if __name__ == "__main__":
    unittest.main()
