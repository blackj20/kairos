"""Tests V0.10 du français relationnel et de la connaissance de soi."""

from __future__ import annotations

import unittest

from kairos import Kernel


class TestMetaComprehension(unittest.TestCase):
    def test_explain_yourself_points_to_runtime_self(self) -> None:
        decision = Kernel().traiter("explique-toi")
        self.assertEqual("self.explain", decision.route)
        self.assertEqual("expliquer", decision.analyse.action.valeur)
        self.assertEqual("self:kairos", decision.analyse.cible.valeur)
        self.assertIn("version runtime", decision.reponse)
        self.assertIn("0.13.0", decision.reponse)

    def test_simple_explanation_builds_category_and_quality_relations(self) -> None:
        analyse = Kernel().comprendre.analyser(
            "mbote est une salutation amicale"
        )
        relations = {
            (r.source, r.relation, r.target) for r in analyse.relations
        }
        self.assertIn(("mbote", "est_un", "salutation"), relations)
        self.assertIn(("salutation", "qualite", "amical"), relations)

    def test_proper_noun_action_targets_self(self) -> None:
        analyse = Kernel().comprendre.analyser("Jps crée Kairos")
        relations = {
            (r.source, r.relation, r.target) for r in analyse.relations
        }
        self.assertIn(("creator:jps", "creer", "self:kairos"), relations)

    def test_adjective_describes_named_subject(self) -> None:
        analyse = Kernel().comprendre.analyser("Kairos est symbolique")
        relations = {
            (r.source, r.relation, r.target) for r in analyse.relations
        }
        self.assertIn(("self:kairos", "qualite", "symbolique"), relations)

    def test_what_did_you_understand_reuses_previous_analysis(self) -> None:
        kernel = Kernel()
        kernel.traiter("installe python")
        decision = kernel.traiter("qu'as-tu compris ?")
        self.assertEqual("understanding.explain", decision.route)
        self.assertIn("installer", decision.reponse)
        self.assertIn("python", decision.reponse)

    def test_misunderstanding_reports_unknown_word(self) -> None:
        kernel = Kernel()
        kernel.traiter("analyse blorpe")
        decision = kernel.traiter("qu'as-tu mal compris ?")
        self.assertEqual("understanding.explain", decision.route)
        self.assertIn("blorpe", decision.reponse)

    def test_runtime_capabilities_come_from_catalogue(self) -> None:
        decision = Kernel().traiter("que peux-tu faire ?")
        self.assertEqual("self.capabilities", decision.route)
        self.assertIn("memory.search", decision.reponse)
        self.assertIn("absente de ce registre", decision.reponse)

    def test_previous_decision_can_explain_why(self) -> None:
        kernel = Kernel()
        kernel.traiter("installe")
        decision = kernel.traiter("pourquoi ?")
        self.assertEqual("decision.explain", decision.route)
        self.assertIn("route", decision.reponse)
        self.assertIn("%", decision.reponse)


if __name__ == "__main__":
    unittest.main()
