"""Tests de routage du chef d'orchestre."""

from __future__ import annotations

import unittest

from kairos import Analyse, Kernel


class TestKernel(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = Kernel()

    def test_conversation_est_envoyee_a_repondre(self) -> None:
        decision = self.kernel.traiter("salut cv?")
        self.assertEqual("repondre", decision.route)
        self.assertEqual("Salut ! Ça va bien. Et toi ?", decision.reponse)

    def test_ordre_est_envoye_a_une_competence(self) -> None:
        decision = self.kernel.traiter("install python")
        self.assertEqual("competence", decision.route)
        self.assertIn("aucune compétence", decision.reponse)

    def test_competence_enregistree_recoit_analyse(self) -> None:
        def installer(analyse: Analyse) -> str:
            return f"Simulation d'installation : {analyse.cible.valeur}"

        self.kernel.enregistrer_competence("installer", installer)
        decision = self.kernel.traiter("install python")

        self.assertEqual("competence", decision.route)
        self.assertEqual("Simulation d'installation : python", decision.reponse)

    def test_interdiction_est_envoyee_au_controle(self) -> None:
        decision = self.kernel.traiter("n'installe pas python")
        self.assertEqual("controle", decision.route)
        self.assertIn("Interdiction comprise", decision.reponse)


if __name__ == "__main__":
    unittest.main()
