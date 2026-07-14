import csv
import os

from our.tools.checker import fjsp_correctness_checker
from our.tools.getdata import get_data

Dataset = "Dauzere"


def _load_optimal_map(csv_path: str) -> dict[str, int]:
    optimal: dict[str, int] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            name, val_s = row[0].strip(), row[1].strip()
            if not name:
                continue
            try:
                optimal[name.lower()] = int(val_s)
            except ValueError:
                continue
    return optimal


def _find_baseline_csv(data_dir: str, folder_name: str) -> str | None:
    fl = folder_name.lower()
    for fname in os.listdir(data_dir):
        if not fname.lower().endswith(".csv"):
            continue
        stem, _ = os.path.splitext(fname)
        if stem.lower() == fl:
            return os.path.join(data_dir, fname)
    return None


def _makespan(schedule: list) -> int:
    return max(max(op[1] + op[2] for op in job) for job in schedule)


def evaluate_with_report(FJSP_Solver, dataset: str = Dataset, validate: bool = True) -> dict:
    """
    在 data/<Dataset>/ 下跑遍所有 .fjs，用 FJSP_Solver 求调度，按基准 CSV 计算各实例
    score = (makespan - 最优值) / 最优值 * 100，并返回逐实例诊断。
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_root = os.getenv("FJSP_DATA_DIR", os.path.join(backend_dir, "Data"))
    sub = os.path.join(data_root, dataset)
    if not os.path.isdir(sub):
        raise FileNotFoundError(f"数据集目录不存在: {sub}")
    baseline_csv = _find_baseline_csv(data_root, dataset)
    if baseline_csv is None:
        raise FileNotFoundError(f"未找到与 {dataset} 同名（忽略大小写）的基准 CSV")
    optimal = _load_optimal_map(baseline_csv)

    scores: list[float] = []
    instances: list[dict] = []
    failed_instances: list[dict] = []

    for fname in sorted(os.listdir(sub)):
        if not fname.lower().endswith(".fjs"):
            continue
        inst_name = os.path.splitext(fname)[0]
        inst_key = os.path.splitext(fname)[0].lower()
        fpath = os.path.join(sub, fname)
        n_jobs, n_machines, durations = get_data(fpath)
        if n_jobs is None or n_machines is None or durations is None:
            failed_instances.append({"instance": inst_name, "error": "load_failed"})
            continue
        try:
            result = FJSP_Solver(n_jobs, n_machines, durations)
            if validate:
                check_result = fjsp_correctness_checker(result, n_jobs, n_machines, durations)
                if check_result is not True:
                    failed_instances.append({
                        "instance": inst_name,
                        "error": "schedule_invalid",
                        "message": str(check_result),
                    })
                    continue
            ms = _makespan(result)
        except Exception as exc:  # noqa: BLE001 - generated solvers may fail in many ways
            failed_instances.append({
                "instance": inst_name,
                "error": type(exc).__name__,
                "message": str(exc),
            })
            continue
        opt = optimal.get(inst_key)
        if opt is None or opt == 0:
            failed_instances.append({"instance": inst_name, "error": "missing_baseline"})
            continue
        score = (ms - opt) / opt * 100.0
        scores.append(score)
        instances.append({
            "instance": inst_name,
            "makespan": ms,
            "optimal": opt,
            "score": score,
        })

    avg_score = float("nan") if not scores else sum(scores) / len(scores)
    return {
        "score": avg_score,
        "dataset": dataset,
        "valid_instances": len(instances),
        "failed_instances": failed_instances,
        "instances": instances,
    }


def evaluate(FJSP_Solver):
    """Backward-compatible score-only API."""
    return evaluate_with_report(FJSP_Solver)["score"]
