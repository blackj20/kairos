"""Tests des derniers contrats décrits dans architecture.md."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from kairos.kernel_event import Event, EventKernel, EventType
from kairos.learning import Acquire, Extractor
from kairos.memory import MemoryRepository
from kairos.process import FileExecutor, ProcessPlan, ProcessStep, Risk


class _Recorder:
    """Composant factice utilisé pour prouver la délégation événementielle."""

    async def handle(self, event: Event) -> str:
        """Retourne le contenu sans connaître le kernel."""

        return str(event.payload["message"])


class TestEventKernel(unittest.IsolatedAsyncioTestCase):
    """Valide l'attente asynchrone, la délégation et l'arrêt propre."""

    async def test_event_is_dispatched_and_audited(self) -> None:
        """Un message produit exactement une entrée d'audit réussie."""

        kernel = EventKernel()
        kernel.register(EventType.USER_MESSAGE, _Recorder())
        await kernel.emit(
            Event(EventType.USER_MESSAGE, {"message": "bonjour"})
        )
        await kernel.emit(Event(EventType.STOP))
        await asyncio.wait_for(kernel.run(), timeout=1)
        self.assertEqual("bonjour", kernel.audit[0]["result"])
        self.assertEqual("STOP", kernel.audit[1]["event"])


class TestLearning(unittest.TestCase):
    """Valide la provenance et l'extraction non confirmante."""

    def test_document_becomes_evidence_and_candidates(self) -> None:
        """Le document génère une preuve et une définition candidate."""

        repository = MemoryRepository()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                document = Path(tmp) / "cours.md"
                document.write_text(
                    "Classe Python : modèle qui crée des instances\n\n"
                    "```python\nclass Personne:\n    pass\n```\n",
                    encoding="utf-8",
                )
                evidence_id, content = Acquire(repository).from_local_document(
                    document
                )
                candidates = Extractor().extract(content, evidence_id)
                self.assertEqual("Classe Python", candidates[0]["name"])
                self.assertEqual([evidence_id], candidates[0]["evidence_ids"])
                self.assertIn("class Personne", candidates[0]["examples"][0])
                # L'extraction seule ne doit rendre aucune connaissance visible.
                self.assertEqual([], repository.search({"text": "Classe Python"}))
        finally:
            repository.close()


class TestProcess(unittest.TestCase):
    """Valide bornage, confirmation, transaction et rollback."""

    def test_read_and_reversible_write_with_rollback(self) -> None:
        """Une copie peut être annulée sans toucher au fichier source."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.txt").write_text("contenu", encoding="utf-8")
            executor = FileExecutor(root)
            plan = ProcessPlan(
                "copier le fichier",
                (
                    ProcessStep(
                        "fs.copy",
                        {"path": "source.txt", "destination": "copie.txt"},
                        Risk.REVERSIBLE_WRITE,
                    ),
                ),
            )
            transaction = executor.execute(plan)
            self.assertTrue((root / "copie.txt").is_file())
            executor.rollback(transaction.id)
            self.assertFalse((root / "copie.txt").exists())
            self.assertTrue((root / "source.txt").is_file())

    def test_path_traversal_is_rejected(self) -> None:
        """Même une lecture ne peut sortir de la racine autorisée."""

        with tempfile.TemporaryDirectory() as tmp:
            executor = FileExecutor(tmp)
            plan = ProcessPlan(
                "lecture externe interdite",
                (ProcessStep("fs.read", {"path": "../secret"}, Risk.READ),),
            )
            with self.assertRaises(PermissionError):
                executor.execute(plan)

    def test_sensitive_step_requires_confirmation(self) -> None:
        """Une suppression vers corbeille exige un plan approuvé."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.txt").write_text("important", encoding="utf-8")
            executor = FileExecutor(root)
            unapproved = ProcessPlan(
                "supprimer",
                (
                    ProcessStep(
                        "fs.delete_to_trash",
                        {"path": "note.txt"},
                        Risk.DESTRUCTION,
                        requires_confirmation=True,
                    ),
                ),
                approved=False,
            )
            with self.assertRaises(PermissionError):
                executor.execute(unapproved)
            self.assertTrue((root / "note.txt").is_file())

    def test_delete_to_trash_can_be_rolled_back(self) -> None:
        """Une suppression approuvée reste récupérable par transaction."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.txt").write_text("important", encoding="utf-8")
            executor = FileExecutor(root)
            approved = ProcessPlan(
                "mettre à la corbeille",
                (
                    ProcessStep(
                        "fs.delete_to_trash",
                        {"path": "note.txt"},
                        Risk.DESTRUCTION,
                        requires_confirmation=True,
                    ),
                ),
                approved=True,
            )
            transaction = executor.execute(approved)
            self.assertFalse((root / "note.txt").exists())
            executor.rollback(transaction.id)
            self.assertEqual(
                "important", (root / "note.txt").read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
