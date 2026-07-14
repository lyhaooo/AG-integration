"""
使用 results/pops_best 中第十个文件（population_generation_10.json）中的算法，
对 Data 下六个目标文件夹（Barnes、Brandimarte、Dauzere、edata、rdata、vdata）中的测试数据分别进行测试。
Barnes、Brandimarte、Dauzere 为 Data 下直接子文件夹；edata、rdata、vdata 为 Data/Hurink 下的子文件夹。
结果输出六个 CSV 到 results 文件夹，分别命名为 Barnes.csv、Brandimarte.csv、Dauzere.csv、edata.csv、rdata.csv、vdata.csv。
CSV 两列：测试数据名称，makespan。
"""
import os
import sys
import json
import types
import csv

from prob import FJSP
from get_instance import GetData

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(SCRIPT_DIR, "Data")
POPS_BEST_DIR = os.path.join(PROJECT_ROOT,"results", "pops_best")
GENERATION_NUM = 10
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# 六个目标文件夹：(CSV 文件名, 相对 Data 的路径，仅该路径下直接包含 .fjs 文件)
# Barnes、Brandimarte、Dauzere 在 Data 下；edata、rdata、vdata 在 Data/Hurink 下
TARGET_FOLDERS = [
    ("Barnes", "Barnes"),
    ("Brandimarte", "Brandimarte"),
    ("Dauzere", "Dauzere"),
    ("edata", "Hurink/edata"),
    ("rdata", "Hurink/rdata"),
    ("vdata", "Hurink/vdata"),
]


def collect_fjs_in_folder(rel_path_from_data):
    """收集指定文件夹内直接包含的 .fjs 文件（不递归）。
    rel_path_from_data: 相对 DATA_DIR 的路径，如 'Barnes' 或 'Hurink/edata'。
    返回: [ (文件名, 相对Data的路径), ... ]
    """
    folder = os.path.join(DATA_DIR, rel_path_from_data)
    if not os.path.isdir(folder):
        return []
    out = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".fjs"):
            continue
        rel_to_data = os.path.join(rel_path_from_data, f).replace("\\", "/")
        # 第一列输出不包含 .fjs 后缀
        display_name = f[:-4] if f.endswith(".fjs") else f
        out.append((display_name, rel_to_data))
    return out


def load_algorithm_module(json_path):
    """从 pops_best 的 JSON 中加载算法代码，返回可被 fjsp_solver 使用的 module。"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    code_string = data.get("code", "")
    if not code_string:
        raise ValueError("JSON 中无 'code' 字段")
    heuristic_module = types.ModuleType("heuristic_module")
    exec(code_string, heuristic_module.__dict__)
    sys.modules[heuristic_module.__name__] = heuristic_module
    return heuristic_module


def run_batch_and_save_csv():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_file = os.path.join(POPS_BEST_DIR, f"population_generation_{GENERATION_NUM}.json")
    if not os.path.isfile(json_file):
        print(f"错误: 未找到算法文件 -> {json_file}")
        sys.exit(1)

    print(f"加载算法: {json_file}")
    algo_module = load_algorithm_module(json_file)
    fjsp = FJSP()

    for csv_name, rel_path in TARGET_FOLDERS:
        file_list = collect_fjs_in_folder(rel_path)
        rows = []
        for test_name, rel_to_data in file_list:
            getdata = GetData(rel_to_data)
            instance = getdata.get_instance()
            if not instance or instance.get("num_jobs") is None:
                rows.append((test_name, ""))
                continue
            num_jobs = instance["num_jobs"]
            num_job_operations = instance["num_job_operations"]
            machine_process_times = instance["machine_process_times"]
            try:
                makespan, _ = fjsp.fjsp_solver(
                    num_jobs, num_job_operations, machine_process_times, algo_module
                )
                rows.append((test_name, makespan if makespan is not None else ""))
            except Exception:
                rows.append((test_name, ""))

        csv_path = os.path.join(RESULTS_DIR, f"{csv_name}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["测试数据名称", "makespan"])
            w.writerows(rows)
        print(f"已写入: {csv_path} (共 {len(rows)} 条)")


if __name__ == "__main__":
    run_batch_and_save_csv()
