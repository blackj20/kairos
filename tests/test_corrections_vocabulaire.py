"""Tests du vocabulaire quotidien et de la mémoire orthographique."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos import Comprendre, Kernel
from kairos.connaissances import Connaissances
from kairos.corrections import MemoireCorrections


class TestCorrectionsVocabulaire(unittest.TestCase):
    """Valide apprentissage, réutilisation et prudence des corrections."""

    def test_typo_verb_is_confirmed_once_then_reused(self) -> None:
        """Une faute verbale confirmée ne déclenche plus de question."""

        kernel = Kernel()
        first = kernel.traiter("ovre vscode")
        self.assertEqual("confirmer", first.route)
        self.assertIn("ouvre", first.question)
        self.assertIn("ovre", first.question)
        experience = kernel.repondre_a(first.question_id, "oui")
        self.assertIn(
            ("ovre", "ouvre"), experience.resolution["learned_relations"]
        )

        second = kernel.traiter("ovre vscode")
        self.assertEqual("competence", second.route)
        self.assertEqual("ouvrir", second.analyse.action.valeur)
        self.assertIsNone(second.question_id)
        self.assertGreater(
            second.evaluation["score_global"],
            first.evaluation["score_global"],
        )

    def test_typo_entity_is_confirmed_once_then_reused(self) -> None:
        """La même mémoire corrige aussi une cible quotidienne mal écrite."""

        kernel = Kernel()
        first = kernel.traiter("ouvre vsode")
        self.assertEqual("confirmer", first.route)
        self.assertIn("vscode", first.question)
        kernel.repondre_a(first.question_id, "oui")

        second = kernel.traiter("ouvre vsode")
        self.assertEqual("competence", second.route)
        self.assertEqual("vscode", second.analyse.cible.valeur)
        self.assertEqual(100, second.analyse.cible.score)

    def test_unconfirmed_typo_never_becomes_knowledge(self) -> None:
        """Une proposition seule ne modifie pas le lexique adaptatif."""

        kernel = Kernel()
        first = kernel.traiter("renome fichier")
        second = kernel.traiter("renome fichier")
        self.assertEqual("confirmer", first.route)
        self.assertEqual("confirmer", second.route)
        self.assertEqual(
            {}, kernel.comprendre.connaissances.corrections.relations()
        )

    def test_confirmed_relation_can_be_persisted_and_reloaded(self) -> None:
        """Le JSON optionnel conserve la relation entre deux sessions."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrections.json"
            memory = MemoireCorrections(path)
            first = Kernel(
                comprendre=Comprendre(
                    Connaissances(corrections=memory)
                )
            )
            decision = first.traiter("ovre vscode")
            first.repondre_a(decision.question_id, "oui")

            reloaded = Kernel(
                comprendre=Comprendre(
                    Connaissances(corrections=MemoireCorrections(path))
                )
            )
            result = reloaded.traiter("ovre vscode")
            self.assertEqual("competence", result.route)
            self.assertIsNone(result.question_id)

    def test_everyday_verbs_are_understood(self) -> None:
        """Les verbes fréquents produisent une action canonique et une cible."""

        cases = {
            "lis fichier": "lire",
            "écris fichier": "ecrire",
            "cherche dossier": "chercher",
            "copie fichier": "copier",
            "renomme dossier": "renommer",
            "sauvegarde fichier": "sauvegarder",
            "vérifie fichier": "verifier",
            "affiche dossier": "afficher",
        }
        for request, action in cases.items():
            with self.subTest(request=request):
                decision = Kernel().traiter(request)
                self.assertEqual("ordre", decision.analyse.type_requete.valeur)
                self.assertEqual(action, decision.analyse.action.valeur)
                self.assertEqual("competence", decision.route)

    def test_state_verb_is_an_affirmation_not_an_order(self) -> None:
        """« Cela fonctionne » est maintenant reconnu comme constat."""

        decision = Kernel().traiter("cela fonctionne")
        self.assertEqual("affirmation", decision.analyse.type_requete.valeur)
        self.assertEqual("repondre", decision.route)


if __name__ == "__main__":
    unittest.main()
