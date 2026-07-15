from __future__ import annotations

import json
import threading
import time
import tempfile
from datetime import datetime
from pathlib import Path

from .datasets import DATASETS, load_dataset
from .results import (
    METHOD_DIR,
    generated_path,
    save_generated_algorithm,
    write_run,
)
from .real_engines import run_eoh_engine, run_funsearch_engine, run_our_engine
from .solver import GeneratedSolver


def empty_status(method: str) -> dict:
    return {
        "method": method, "status": "idle", "action": None, "message": "尚未运行", "error": None,
        "progress_percent": 0.0, "current_dataset": "", "current_instance": 0,
        "total_instances": 0, "completed_instances": 0,
        "evolution_iteration": 0, "total_evolution_iterations": 0,
        "best_fitness": None, "evolution_history": [],
        "generated_ready": False, "started_at": None, "finished_at": None, "summary": None,
    }


class ExperimentManager:
    def __init__(self, data_root: Path, results_root: Path):
        self.data_root = data_root
        self.results_root = results_root
        self._lock = threading.RLock()
        self._statuses = {method: empty_status(method) for method in ("eoh", "funsearch", "our")}
        self._threads: dict[str, threading.Thread] = {}
        self._stops = {method: threading.Event() for method in self._statuses}
        self._restore_latest()

    def _restore_latest(self) -> None:
        for method, directory in METHOD_DIR.items():
            status = self._statuses[method]
            status["generated_ready"] = generated_path(self.results_root, method).is_file()
            path = self.results_root / directory / "latest.json"
            if not path.exists():
                continue
            try:
                summary = json.loads(path.read_text(encoding="utf-8"))
                total = sum(item.get("instance_count", 0) for item in summary.get("datasets", []))
                status.update({
                    "status": "completed", "action": "test", "message": "已载入最近一次测试",
                    "progress_percent": 100.0, "total_instances": total, "completed_instances": total,
                    "finished_at": summary.get("created_at"), "summary": summary,
                })
            except (OSError, ValueError):
                continue

    def statuses(self) -> dict[str, dict]:
        with self._lock:
            for method, status in self._statuses.items():
                status["generated_ready"] = generated_path(self.results_root, method).is_file()
            return {method: dict(status) for method, status in self._statuses.items()}

    def start_evolution(self, method: str) -> dict:
        return self._start(method, "evolution", self._run_evolution)

    def start_test(self, method: str) -> dict:
        if method not in self._statuses:
            raise KeyError(method)
        if not generated_path(self.results_root, method).is_file():
            return {"ok": False, "message": "请先运行迭代实验，生成 current_generated.py"}
        return self._start(method, "test", self._run_test)

    def start(self, method: str) -> dict:
        """向后兼容：旧 run 接口等价于统一测试。"""
        return self.start_test(method)

    def _start(self, method: str, action: str, target) -> dict:
        with self._lock:
            if method not in self._statuses:
                raise KeyError(method)
            if any(status["status"] == "running" for status in self._statuses.values()):
                return {"ok": False, "message": "已有任务在运行，请稍后再试"}
            self._stops[method].clear()
            previous_summary = self._statuses[method].get("summary")
            self._statuses[method] = empty_status(method) | {
                "status": "running", "action": action,
                "message": "正在准备迭代实验" if action == "evolution" else "正在加载生成算子",
                "generated_ready": generated_path(self.results_root, method).is_file(),
                "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "summary": previous_summary,
            }
            thread = threading.Thread(target=target, args=(method,), daemon=True, name=f"{action}-{method}")
            self._threads[method] = thread
            thread.start()
        label = "迭代实验" if action == "evolution" else "统一测试"
        return {"ok": True, "message": f"{method} {label}已启动"}

    def stop(self, method: str) -> dict:
        if method not in self._statuses:
            raise KeyError(method)
        self._stops[method].set()
        return {"ok": True, "message": "已发送停止请求"}

    def _update(self, method: str, **changes) -> None:
        with self._lock:
            self._statuses[method].update(changes)

    def _finish_stopped(self, method: str) -> None:
        self._update(method, status="stopped", message="任务已停止", finished_at=self._now())

    def _run_evolution(self, method: str) -> None:
        try:
            settings = self._read_json(self.data_root.parent / "config" / "settings.json", {})
            engines = {"eoh": run_eoh_engine, "funsearch": run_funsearch_engine, "our": run_our_engine}

            def report(current: int, total: int, best: float | None, message: str) -> None:
                point = {
                    "iteration": current,
                    "best_fitness": best,
                    "timestamp": self._now(),
                }
                with self._lock:
                    history = list(self._statuses[method]["evolution_history"])
                    if history and history[-1]["iteration"] == current:
                        history[-1] = point
                    else:
                        history.append(point)
                    self._statuses[method].update(
                        evolution_iteration=current, total_evolution_iterations=total,
                        best_fitness=best, evolution_history=history,
                        progress_percent=round(current / max(total, 1) * 100, 2),
                        message=message,
                    )

            with tempfile.TemporaryDirectory(prefix=f"fjsp-{method}-") as temp_dir:
                code, metadata = engines[method](
                    settings, self.data_root, Path(temp_dir), report, self._stops[method], mock=False
                )
            if self._stops[method].is_set():
                self._finish_stopped(method)
                return
            save_generated_algorithm(self.results_root, method, code, metadata)
            self._update(
                method, status="completed", action="evolution", message="迭代实验完成，已生成算子",
                progress_percent=100.0, generated_ready=True, finished_at=self._now(),
                evolution_iteration=self._statuses[method]["total_evolution_iterations"],
            )
        except Exception as exc:
            self._fail(method, exc)

    def _run_test(self, method: str) -> None:
        try:
            code = generated_path(self.results_root, method).read_text(encoding="utf-8")
            generated_solver = GeneratedSolver(code, method)
            loaded = [(spec, load_dataset(self.data_root, spec)) for spec in DATASETS]
            total = sum(len(instances) for _, instances in loaded)
            self._update(method, total_instances=total, message=f"统一测试共 {total} 个实例")
            rows: list[dict] = []
            completed = 0
            for spec, instances in loaded:
                for index, instance in enumerate(instances, start=1):
                    if self._stops[method].is_set():
                        self._finish_stopped(method)
                        return
                    error = ""
                    started = time.perf_counter()
                    try:
                        makespan = generated_solver.solve(instance)
                        gap = (makespan - instance.optimal) / instance.optimal
                    except Exception as exc:
                        makespan, gap, error = "", "", f"{type(exc).__name__}: {exc}"
                    elapsed = time.perf_counter() - started
                    rows.append({
                        "dataset": spec.name, "instance": instance.name, "optimal": instance.optimal,
                        "makespan": makespan, "gap": gap, "runtime_seconds": elapsed, "error": error,
                    })
                    completed += 1
                    self._update(
                        method, current_dataset=spec.name, current_instance=index,
                        completed_instances=completed, progress_percent=round(completed / total * 100, 2),
                        message=f"{spec.name}: {index}/{len(instances)}",
                    )
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            summary = write_run(self.results_root, method, run_id, code, rows)
            self._update(
                method, status="completed", action="test", message="统一基准测试完成",
                progress_percent=100.0, finished_at=self._now(), summary=summary,
            )
        except Exception as exc:
            self._fail(method, exc)

    def _fail(self, method: str, exc: Exception) -> None:
        self._update(method, status="error", message="运行失败", error=f"{type(exc).__name__}: {exc}", finished_at=self._now())

    @staticmethod
    def _read_json(path: Path, default: dict) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
