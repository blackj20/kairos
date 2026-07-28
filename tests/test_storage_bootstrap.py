"""Tests de création sûre de la mémoire persistante au premier démarrage."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairos.decision.stockage import StockageJson


class TestInitialisationStockageJson(unittest.TestCase):
    def test_missing_memory_files_are_created_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp) / "memory"
            stockage = StockageJson(dossier)

            self.assertEqual((), stockage.questions_en_attente())
            self.assertEqual((), stockage.experiences())
            self.assertEqual((), stockage.apprentissages())

            for nom in StockageJson.FICHIERS.values():
                chemin = dossier / nom
                self.assertTrue(chemin.is_file())
                self.assertEqual(
                    {"version": 1, "items": []},
                    json.loads(chemin.read_text(encoding="utf-8")),
                )

    def test_existing_invalid_memory_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp) / "memory"
            dossier.mkdir(parents=True)
            invalide = dossier / "pending_questions.json"
            invalide.write_text("pas du json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Mémoire illisible"):
                StockageJson(dossier)

            self.assertEqual("pas du json", invalide.read_text(encoding="utf-8"))

    def test_existing_wrong_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp) / "memory"
            dossier.mkdir(parents=True)
            (dossier / "pending_questions.json").write_text(
                json.dumps({"version": 1, "items": "incorrect"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Format mémoire invalide"):
                StockageJson(dossier)


if __name__ == "__main__":
    unittest.main()
