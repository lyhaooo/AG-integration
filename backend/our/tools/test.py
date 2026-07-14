import csv
import os
import sys


_FJSP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_FJSP_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fjsp.result import generated_code  # noqa: E402
from fjsp.tools.checker import fjsp_correctness_checker  # noqa: E402
from fjsp.tools.getdata import get_data  # noqa: E402

_DATA_DIR = os.path.join(_FJSP_DIR, "data")
_RESULT_DIR = os.path.join(_PROJECT_ROOT, "fjsp", "result")
_SUMMARY_CSV = os.path.join(_RESULT_DIR, "summary.csv")


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


def _rows_with_average(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    ms_vals: list[float] = []
    sc_vals: list[float] = []
    for _, ms_s, sc_s in rows:
        if ms_s:
            try:
                ms_vals.append(float(ms_s))
            except ValueError:
                pass
        if sc_s:
            try:
                sc_vals.append(float(sc_s))
            except ValueError:
                pass
    avg_ms = f"{sum(ms_vals) / len(ms_vals):.2f}" if ms_vals else ""
    avg_sc = f"{sum(sc_vals) / len(sc_vals):.6f}" if sc_vals else ""
    return [*rows, ("平均值", avg_ms, avg_sc)]


def _next_summary_column(headers: list[str]) -> str:
    prefix = "best_solution"
    max_idx = 0
    for header in headers:
        if not header.startswith(prefix):
            continue
        suffix = header[len(prefix) :]
        if suffix.isdigit():
            max_idx = max(max_idx, int(suffix))
    return f"{prefix}{max_idx + 1}"


def _sync_summary(results: dict[str, str]) -> None:
    if not results:
        return

    if os.path.exists(_SUMMARY_CSV):
        with open(_SUMMARY_CSV, newline="", encoding="utf-8") as f:
            summary_rows = list(csv.reader(f))
    else:
        summary_rows = [["data"]]

    if not summary_rows:
        summary_rows = [["data"]]

    headers = summary_rows[0]
    if not headers:
        headers = ["data"]
        summary_rows[0] = headers

    new_col = _next_summary_column(headers)
    headers.append(new_col)

    row_by_data: dict[str, list[str]] = {}
    for row in summary_rows[1:]:
        if not row:
            continue
        while len(row) < len(headers) - 1:
            row.append("")
        row.append(results.get(row[0], ""))
        row_by_data[row[0]] = row

    for entry, avg_score in results.items():
        if entry in row_by_data:
            continue
        summary_rows.append([entry, *[""] * (len(headers) - 2), avg_score])

    with open(_SUMMARY_CSV, "w", newline="", encoding="utf-8") as out:
        csv.writer(out).writerows(summary_rows)
    print(f"已同步 summary.csv 的最后一列: {new_col}")


def run_all(FJSP_Solver) -> None:
    os.makedirs(_RESULT_DIR, exist_ok=True)
    summary_results: dict[str, str] = {}
    for entry in sorted(os.listdir(_DATA_DIR)):
        sub = os.path.join(_DATA_DIR, entry)
        if not os.path.isdir(sub):
            continue
        baseline_csv = _find_baseline_csv(_DATA_DIR, entry)
        if baseline_csv is None:
            print(f"跳过 {entry}: 未找到同名（忽略大小写）的基准 CSV")
            continue
        optimal = _load_optimal_map(baseline_csv)
        rows: list[tuple[str, str, str]] = []
        for fname in sorted(os.listdir(sub)):
            if not fname.lower().endswith(".fjs"):
                continue
            inst = os.path.splitext(fname)[0]
            inst_key = inst.lower()
            fpath = os.path.join(sub, fname)
            try:
                n_jobs, n_machines, durations = get_data(fpath)
                if n_jobs is None or n_machines is None or durations is None:
                    rows.append((inst, "", ""))
                    print(f"加载失败: {fpath}")
                    continue
                result = FJSP_Solver(n_jobs, n_machines, durations)
                if not fjsp_correctness_checker(result, n_jobs, n_machines, durations):
                    print(f"校验未通过: {fpath}")
                ms = _makespan(result)
                opt = optimal.get(inst_key)
                if opt is None:
                    print(f"基准 CSV 中无实例 {inst} ({entry})")
                    rows.append((inst, str(ms), ""))
                elif opt == 0:
                    rows.append((inst, str(ms), ""))
                else:
                    score = (ms - opt) / opt * 100.0
                    rows.append((inst, str(ms), f"{score:.6f}"))
            except Exception as exc:  # noqa: BLE001
                print(f"运行异常 {fpath}: {exc}")
                rows.append((inst, "", ""))

        out_rows = _rows_with_average(rows)
        out_path = os.path.join(_RESULT_DIR, f"{entry}.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as out:
            w = csv.writer(out)
            w.writerow(["instance", "makespan", "score"])
            w.writerows(out_rows)
        summary_results[entry] = out_rows[-1][2]
        print(f"已写入 {out_path}，共 {len(rows)} 个实例")

    _sync_summary(summary_results)


if __name__ == "__main__":
    # FJSP_Solver = sample.fjsp_solver
    FJSP_Solver = generated_code.fjsp_solver
    run_all(FJSP_Solver=FJSP_Solver)
