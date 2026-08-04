"""Porte mesurable du moteur interne V0.18."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kairos.interne import MoteurInterne
from kairos.memory import MemoryRepository


class FakeLab:
    def __init__(self) -> None:
        self.called = 0

    def run(self, source_path: Path) -> dict[str, object]:
        self.called += 1
        return {
            "state": "completed",
            "secau_calls": 1,
            "production_unchanged": True,
            "source": str(source_path),
        }


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "memory").mkdir(parents=True)
        repository = MemoryRepository(root / "memory" / "cognition.db")
        try:
            repository.add_hypothesis(
                {
                    "name": "xylophore",
                    "definition": "un instrument musical",
                    "created_from_experience_id": "bench_exp",
                    "score": 40,
                }
            )
            config = {
                "mode": "offline_first",
                "max_candidates": 10,
                "max_seconds": 5,
                "run_lab": True,
                "ask_one_question": True,
                "network": False,
                "production_promotion": False,
            }
            engine = MoteurInterne(root, repository=repository, config=config)
            result = engine.run()
            assertions = (
                result.etat == "waiting_human",
                result.candidats_vus == 1,
                result.taches_executees == 1,
                result.question is not None,
                result.question is not None and result.question.champ == "relation",
                result.question is not None and result.question.gain_attendu == 40,
                result.reseau_utilise is False,
                result.ratio_hors_ligne == 1.0,
                result.connaissances_production_modifiees is False,
                Path(result.report_path).exists(),
                engine.status()["run_id"] == result.run_id,
                MoteurInterne.parse_command("internal-engine=on") == "on",
            )
            checks = sum(bool(item) for item in assertions)
            if checks != len(assertions):
                print(f"INTERNAL_ENGINE_BENCHMARK_FAILED: {checks}/{len(assertions)}")
                return 1
            print(f"INTERNAL_ENGINE_BENCHMARK_OK: {checks}/{len(assertions)}")
            return 0
        finally:
            repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
