from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fjsp_platform.algorithms import load_algorithm, render_our_code
from fjsp_platform.datasets import DATASETS, load_dataset
from fjsp_platform.results import comparison_payload, write_run
from fjsp_platform.solver import solve


BACKEND = Path(__file__).resolve().parents[1]


class PlatformTests(unittest.TestCase):
    def test_all_six_datasets_load(self):
        counts = [len(load_dataset(BACKEND / "Data", spec)) for spec in DATASETS]
        self.assertEqual(len(counts), 6)
        self.assertTrue(all(count > 0 for count in counts))
        self.assertEqual(sum(counts), 169)

    def test_all_methods_produce_valid_schedule(self):
        instance = load_dataset(BACKEND / "Data", DATASETS[0])[0]
        for method in ("eoh", "funsearch", "our"):
            with self.subTest(method=method):
                self.assertGreater(solve(instance, load_algorithm(method)), 0)

    def test_our_code_weights_are_material(self):
        self.assertNotEqual(render_our_code(0, 0, 0), render_our_code(1, 0.12, 0.08))

    def test_result_history_and_compare_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [{
                "dataset": "Demo", "instance": "a", "optimal": 10,
                "makespan": 12, "gap": 0.2, "runtime_seconds": 0.01, "error": "",
            }]
            write_run(root, "eoh", "test_1", "# code", rows)
            payload = comparison_payload(root)
            self.assertEqual(payload["methods"]["eoh"]["overall_avg_gap"], 0.2)
            self.assertTrue((root / "compare.csv").is_file())


if __name__ == "__main__":
    unittest.main()
