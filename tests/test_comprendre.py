"""Tests du contrat entre Comprendre et le kernel."""

from __future__ import annotations

import unittest

from kairos import Comprendre


class TestComprendre(unittest.TestCase):
    def setUp(self) -> None:
        self.comprendre = Comprendre()

    def test_install_python_produit_les_scores_de_reference(self) -> None:
        analyse = self.comprendre.analyser("install python")

        self.assertEqual(("ordre", 85), (
            analyse.type_requete.valeur,
            analyse.type_requete.score,
        ))
        self.assertEqual(("execution", 76), (
            analyse.demarche.valeur,
            analyse.demarche.score,
        ))
        self.assertEqual(("installer", 76), (
            analyse.action.valeur,
            analyse.action.score,
        ))
        self.assertEqual(("python", 100), (
            analyse.cible.valeur,
            analyse.cible.score,
        ))

    def test_salut_cv_est_question_et_conversation(self) -> None:
        analyse = self.comprendre.analyser("salut cv?")

        self.assertEqual(("question", 80), (
            analyse.type_requete.valeur,
            analyse.type_requete.score,
        ))
        self.assertEqual(("conversation", 56), (
            analyse.demarche.valeur,
            analyse.demarche.score,
        ))
        self.assertEqual((None, 0), (
            analyse.action.valeur,
            analyse.action.score,
        ))

    def test_requete_vide_demande_une_clarification(self) -> None:
        analyse = self.comprendre.analyser("   ")
        self.assertEqual("inconnu", analyse.type_requete.valeur)
        self.assertEqual("clarification", analyse.demarche.valeur)

    def test_cible_inconnue_ne_recoit_pas_cent_pour_cent(self) -> None:
        analyse = self.comprendre.analyser("install chose-inconnue")
        self.assertEqual("chose-inconnue", analyse.cible.valeur)
        self.assertEqual(55, analyse.cible.score)

    def test_interdiction_est_reconnue(self) -> None:
        analyse = self.comprendre.analyser("n'installe pas python")
        self.assertEqual("interdiction", analyse.type_requete.valeur)
        self.assertEqual("installer", analyse.action.valeur)
        self.assertEqual("python", analyse.cible.valeur)

    def test_lecon_est_reconnue(self) -> None:
        analyse = self.comprendre.analyser("c'est quoi un atome")
        self.assertEqual("lecon", analyse.type_requete.valeur)
        self.assertEqual("apprentissage", analyse.demarche.valeur)

    def test_retour_utilisateur_est_reconnu(self) -> None:
        analyse = self.comprendre.analyser("tu t'es trompé")
        self.assertEqual("retour_utilisateur", analyse.type_requete.valeur)
        self.assertEqual("correction", analyse.demarche.valeur)

    def test_demarrage_de_conversation_est_reconnu(self) -> None:
        analyse = self.comprendre.analyser("bonjour")
        self.assertEqual("demarrage_conversation", analyse.type_requete.valeur)
        self.assertEqual("conversation", analyse.demarche.valeur)


if __name__ == "__main__":
    unittest.main()
