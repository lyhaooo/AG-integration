"""Run one unified experiment from the command line."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from fjsp_platform.runner import ExperimentManager


def run(method: str, action: str = "test") -> int:
    root = Path(__file__).resolve().parent
    manager = ExperimentManager(root / "Data", root / "results")
    result = manager.start_evolution(method) if action == "evolve" else manager.start_test(method)
    print(result["message"])
    while True:
        status = manager.statuses()[method]
        print(f'\r{status["progress_percent"]:6.2f}% {status["message"]:<40}', end="", flush=True)
        if status["status"] != "running":
            print()
            if status["error"]:
                print(status["error"])
            return 0 if status["status"] == "completed" else 1
        time.sleep(0.1)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行统一 FJSP 基准实验")
    parser.add_argument("method", choices=("eoh", "funsearch", "our"))
    parser.add_argument("action", choices=("evolve", "test"), help="迭代生成算子或运行统一测试")
    args = parser.parse_args()
    return run(args.method, args.action)


if __name__ == "__main__":
    raise SystemExit(main())
