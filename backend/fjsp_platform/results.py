from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from statistics import mean

METHOD_DIR = {"eoh": "eoh_r", "funsearch": "fun_r", "our": "our_r"}


def method_root(results_root: Path, method: str) -> Path:
    root = results_root / METHOD_DIR[method]
    (root / "history").mkdir(parents=True, exist_ok=True)
    return root


def generated_path(results_root: Path, method: str) -> Path:
    return method_root(results_root, method) / "current_generated.py"


def save_generated_algorithm(results_root: Path, method: str, code: str, metadata: dict | None = None) -> dict:
    root = method_root(results_root, method)
    path = root / "current_generated.py"
    path.write_text(code, encoding="utf-8")
    evolution_id = datetime.now().strftime("evolution_%Y%m%d_%H%M%S_%f")[:-3]
    evolution_dir = root / "history" / evolution_id
    evolution_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, evolution_dir / "generated.py")
    payload = {
        "evolution_id": evolution_id,
        "method": method,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        **(metadata or {}),
    }
    (evolution_dir / "evolution.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def write_run(results_root: Path, method: str, run_id: str, code: str, rows: list[dict]) -> dict:
    root = method_root(results_root, method)
    current_code = root / "current_generated.py"
    current_code.write_text(code, encoding="utf-8")
    run_dir = root / "history" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(current_code, run_dir / "generated.py")

    datasets: list[dict] = []
    for dataset in sorted({row["dataset"] for row in rows}):
        selected = [row for row in rows if row["dataset"] == dataset]
        with (run_dir / f"{dataset}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["instance", "optimal", "makespan", "gap", "runtime_seconds", "error"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(selected)
        valid = [row for row in selected if not row["error"]]
        datasets.append({
            "dataset": dataset,
            "instance_count": len(selected),
            "valid_count": len(valid),
            "avg_gap": mean(row["gap"] for row in valid) if valid else None,
            "avg_runtime_seconds": mean(row["runtime_seconds"] for row in valid) if valid else None,
        })
    valid_rows = [row for row in rows if not row["error"]]
    summary = {
        "run_id": run_id,
        "method": method,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "datasets": datasets,
        "overall_avg_gap": mean(row["gap"] for row in valid_rows) if valid_rows else None,
        "overall_avg_runtime_seconds": mean(row["runtime_seconds"] for row in valid_rows) if valid_rows else None,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "latest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    update_compare_csv(results_root, summary)
    return summary


def _summary_files(results_root: Path) -> list[Path]:
    return sorted(results_root.glob("*_r/history/*/summary.json"))


def load_summaries(results_root: Path) -> list[dict]:
    summaries = []
    for path in _summary_files(results_root):
        try:
            summaries.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return summaries


def update_compare_csv(results_root: Path, _new_summary: dict | None = None) -> None:
    summaries = load_summaries(results_root)
    run_columns = [f'{item["method"]}_{item["run_id"]}' for item in summaries]
    row_keys: list[tuple[str, str, str]] = []
    for summary in summaries:
        for dataset in summary["datasets"]:
            for metric in ("avg_gap", "avg_runtime_seconds"):
                key = (summary["method"], dataset["dataset"], metric)
                if key not in row_keys:
                    row_keys.append(key)
        for metric in ("overall_avg_gap", "overall_avg_runtime_seconds"):
            key = (summary["method"], "ALL_DATASETS", metric)
            if key not in row_keys:
                row_keys.append(key)

    # 数据集明细在前，跨数据集汇总行固定放在文件末尾，便于人工查看。
    row_keys.sort(key=lambda key: (key[1] == "ALL_DATASETS", key[0], key[1], key[2]))

    table: dict[tuple[str, str, str], dict[str, float]] = {key: {} for key in row_keys}
    for summary, column in zip(summaries, run_columns):
        for dataset in summary["datasets"]:
            for metric in ("avg_gap", "avg_runtime_seconds"):
                value = dataset.get(metric)
                if value is not None:
                    table[(summary["method"], dataset["dataset"], metric)][column] = value
        for metric in ("overall_avg_gap", "overall_avg_runtime_seconds"):
            value = summary.get(metric)
            if value is not None:
                table[(summary["method"], "ALL_DATASETS", metric)][column] = value

    results_root.mkdir(parents=True, exist_ok=True)
    with (results_root / "compare.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["method", "dataset", "metric", *run_columns, "average"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in row_keys:
            values = table[key]
            numeric = list(values.values())
            writer.writerow({
                "method": key[0], "dataset": key[1], "metric": key[2],
                **values, "average": mean(numeric) if numeric else "",
            })


def comparison_payload(results_root: Path) -> dict:
    summaries = load_summaries(results_root)
    latest: dict[str, dict] = {}
    for summary in summaries:
        latest[summary["method"]] = summary
    return {"methods": latest, "runs": summaries, "compare_file": "compare.csv"}
