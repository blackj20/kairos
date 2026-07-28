"""Tests des frontières entre les étapes de Comprendre."""

from __future__ import annotations

import unittest

from kairos import Comprendre, ConnaissanceDeSoi, Kernel


class TestPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.comprendre = Comprendre()

    def test_decouper_conserve_positions_et_ponctuation(self) -> None:
        resultat = self.comprendre.decouper.analyser("Salut, cv ?")
        self.assertEqual(
            ["salut", ",", "cv", "?"],
            [jeton.normalise for jeton in resultat.jetons],
        )
        self.assertTrue(resultat.jetons[-1].ponctuation)

    def test_sens_conserve_les_deux_sens_de_cv(self) -> None:
        decoupage = self.comprendre.decouper.analyser("cv")
        resultats = self.comprendre.sens.analyser(decoupage)
        categories = {candidat.categorie for candidat in resultats[0].candidats}
        self.assertIn("nom_document", categories)
        self.assertIn("question_etat", categories)

    def test_contexte_resout_marche_comme_verbe(self) -> None:
        analyse = self.comprendre.analyser("marche vers la maison")
        marche = next(
            element
            for element in analyse.sens_contextuels
            if element.jeton.normalise == "marche"
        )
        self.assertEqual("verbe_action", marche.choisi.categorie)

    def test_contexte_resout_marche_comme_nom(self) -> None:
        analyse = self.comprendre.analyser("la marche de cet escalier")
        marche = next(
            element
            for element in analyse.sens_contextuels
            if element.jeton.normalise == "marche"
        )
        self.assertEqual("nom", marche.choisi.categorie)

    def test_plusieurs_actions_ne_sont_pas_executees(self) -> None:
        decision = Kernel().traiter("ouvre python et ferme vscode")
        self.assertEqual("ordre", decision.analyse.type_requete.valeur)
        self.assertEqual("clarification", decision.route)
        self.assertFalse(decision.analyse.verification.valide)

    def test_formule_politesse_reste_un_ordre(self) -> None:
        decision = Kernel().traiter("s'il te plaît ouvre le terminal")
        self.assertEqual("ordre", decision.analyse.type_requete.valeur)
        self.assertEqual("competence", decision.route)

    def test_self_connait_identite_maison_objectif_et_createur(self) -> None:
        soi = ConnaissanceDeSoi()
        resume = soi.resume()
        self.assertEqual("K.A.I.R.O.S.", resume["name"])
        self.assertEqual(".", resume["home"])
        self.assertIn("comprendre", resume["objective"])
        self.assertEqual("Jps", resume["creator"])


if __name__ == "__main__":
    unittest.main()
