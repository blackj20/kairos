"""La porte V0.18 doit rester exécutable depuis la suite principale."""

from __future__ import annotations

import unittest

import internal_engine_benchmark


class InternalEngineBenchmarkTests(unittest.TestCase):
    def test_internal_engine_benchmark(self) -> None:
        self.assertEqual(0, internal_engine_benchmark.main())


if __name__ == "__main__":
    unittest.main()
