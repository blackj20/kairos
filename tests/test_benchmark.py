"""Verrouille les critères annoncés pour la fondation candidate."""

from __future__ import annotations

import unittest

from benchmark import executer_benchmark


class TestBenchmark(unittest.TestCase):
    def test_fondation_respecte_ses_criteres(self) -> None:
        resultat = executer_benchmark()
        self.assertTrue(resultat["foundation_validated"])
        self.assertEqual(100.0, resultat["groups"]["core"]["exact_accuracy"])
        self.assertGreaterEqual(
            resultat["groups"]["variant"]["intention_accuracy"],
            90.0,
        )
        self.assertEqual(0, resultat["unsafe_false_executions"])


if __name__ == "__main__":
    unittest.main()
