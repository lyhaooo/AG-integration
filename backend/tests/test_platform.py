from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fjsp_platform.algorithms import load_algorithm, render_our_code
from fjsp_platform.datasets import DATASETS, load_dataset
from fjsp_platform.results import comparison_payload, write_run
from fjsp_platform.runner import ExperimentManager
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

    def test_evolution_status_collects_chart_history(self):
        def fake_engine(settings, data_root, work_root, progress, stop_event, mock=False):
            progress(1, 2, 0.42, "first")
            progress(1, 2, 0.38, "first improved")
            progress(2, 2, 0.31, "second")
            return "def fjsp_solver(instance):\n    return []\n", {"engine": "fake"}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = ExperimentManager(root / "Data", root / "results")
            with patch("fjsp_platform.runner.run_eoh_engine", fake_engine):
                manager.start_evolution("eoh")
                manager._threads["eoh"].join(timeout=2)

            status = manager.statuses()["eoh"]
            self.assertEqual(status["status"], "completed")
            self.assertEqual([point["iteration"] for point in status["evolution_history"]], [1, 2])
            self.assertEqual(status["evolution_history"][0]["best_fitness"], 0.38)
            self.assertEqual(status["best_fitness"], 0.31)

    def test_evolution_status_exposes_active_agent_stage(self):
        reported = threading.Event()
        release = threading.Event()

        def fake_engine(settings, data_root, work_root, progress, stop_event, mock=False):
            progress(1, 1, 0.25, "Generator Agent 正在执行", "generator", "Generator", "generation")
            reported.set()
            release.wait(timeout=2)
            return "def fjsp_solver(instance):\n    return []\n", {"engine": "fake"}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = ExperimentManager(root / "Data", root / "results")
            with patch("fjsp_platform.runner.run_our_engine", fake_engine):
                manager.start_evolution("our")
                self.assertTrue(reported.wait(timeout=2))
                status = manager.statuses()["our"]
                self.assertEqual(status["activity_stage"], "generator")
                self.assertEqual(status["active_agent"], "Generator")
                self.assertEqual(status["activity_detail"], "generation")
                self.assertEqual(status["activity_events"][0]["stage"], "generator")
                release.set()
                manager._threads["our"].join(timeout=2)


if __name__ == "__main__":
    unittest.main()
