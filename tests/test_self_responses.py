"""Tests des connaissances protégées sur Kairos et du cas historique atoms."""

from __future__ import annotations

import unittest

from kairos import Kernel


class TestReponsesSurSoi(unittest.TestCase):
    def test_identity_is_answered_from_protected_self_memory(self) -> None:
        decision = Kernel().traiter("qui es tu ?")
        self.assertIn("K.A.I.R.O.S.", decision.reponse)
        self.assertIn("0.17.0", decision.reponse)

    def test_current_objective_is_answered_from_protected_self_memory(self) -> None:
        decision = Kernel().traiter("quel est ton objectif ?")
        self.assertIn("comprendre", decision.reponse.casefold())
        self.assertIn("classifier", decision.reponse.casefold())

    def test_atoms_alias_reuses_confirmed_atom_knowledge(self) -> None:
        decision = Kernel().traiter("c'est quoi un atoms ?")
        self.assertIn("atome", decision.reponse.casefold())
        self.assertNotIn(
            "je n'ai pas encore de connaissance confirmée",
            decision.reponse.casefold(),
        )


if __name__ == "__main__":
    unittest.main()
