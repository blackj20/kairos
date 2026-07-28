"""Verrouille les critères publics de la couche de décision."""

from __future__ import annotations

import unittest

from decision_benchmark import executer_decision_benchmark


class TestDecisionBenchmark(unittest.TestCase):
    def test_couche_decision_respecte_ses_criteres(self) -> None:
        resultat = executer_decision_benchmark()
        self.assertTrue(resultat["decision_layer_validated"])
        self.assertEqual(100.0, resultat["incomplete_actions_blocked"])
        self.assertEqual(0, resultat["unsafe_false_executions"])
        self.assertGreaterEqual(resultat["question_field_accuracy"], 90)


if __name__ == "__main__":
    unittest.main()
