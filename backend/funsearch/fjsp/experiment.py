# -*- coding: utf-8 -*-
"""
批量测试：将进化得到的最优 get_operators 导出为 MA4PGO 风格的双算子文件，
并对六个 benchmark 文件夹生成 CSV（与 MA4PGO experiment.py 一致）。
"""

import csv
import os
import sys
import types

from fjsp.fjsp_eval import FJSPEvaluator
from fjsp.get_instance import GetData

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
RESULTS_DIR = os.path.join(SCRIPT_DIR, 'results')

TARGET_FOLDERS = [
    ('Barnes', 'Barnes', 'Barnes.csv'),
    ('Brandimarte', 'Brandimarte', 'Brandimarte.csv'),
    ('Dauzere', 'Dauzere', 'Dauzere.csv'),
    ('edata', 'Hurink/edata', 'hurink_edata.csv'),
    ('rdata', 'Hurink/rdata', 'Hurink_rdata.csv'),
    ('vdata', 'Hurink/vdata', 'hurink_vdata.csv'),
]

BEST_OPERATORS_PATH = os.path.join(RESULTS_DIR, 'best_get_operators.py')
BEST_OPERATION_PATH = os.path.join(RESULTS_DIR, 'best_operation_operator.py')
BEST_MACHINE_PATH = os.path.join(RESULTS_DIR, 'best_machine_operator.py')


def load_optimal_dict(optimal_csv_name: str) -> dict[str, float]:
  csv_path = os.path.join(DATA_DIR, optimal_csv_name)
  d: dict[str, float] = {}
  if not os.path.isfile(csv_path):
    return d
  with open(csv_path, 'r', encoding='utf-8') as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      parts = line.split(',')
      if len(parts) < 2:
        continue
      name = parts[0].strip()
      try:
        d[name.lower()] = float(parts[1].strip())
      except ValueError:
        pass
  return d


def lookup_optimal(test_name: str, optimal_dict: dict[str, float]) -> float | None:
  if not test_name:
    return None
  return optimal_dict.get(test_name.lower())


def calc_relative_gap(makespan, optimal) -> str | float:
  if makespan == '' or makespan is None or optimal is None or optimal <= 0:
    return ''
  try:
    return (float(makespan) - optimal) / optimal
  except (TypeError, ValueError):
    return ''


def collect_fjs_in_folder(rel_path_from_data: str) -> list[tuple[str, str]]:
  folder = os.path.join(DATA_DIR, rel_path_from_data)
  if not os.path.isdir(folder):
    return []
  out = []
  for f in sorted(os.listdir(folder)):
    if not f.endswith('.fjs'):
      continue
    rel_to_data = os.path.join(rel_path_from_data, f).replace('\\', '/')
    display_name = f[:-4]
    out.append((display_name, rel_to_data))
  return out


def load_algorithm_module(path: str | None = None):
  path = path or BEST_OPERATORS_PATH
  if not os.path.isfile(path):
    raise FileNotFoundError(f'未找到算子文件: {path}')
  with open(path, 'r', encoding='utf-8') as f:
    code = (f.read() or '').strip()
  mod = types.ModuleType('heuristic_module')
  exec(code, mod.__dict__)  # pylint: disable=exec-used
  sys.modules[mod.__name__] = mod
  if not hasattr(mod, 'get_operators'):
    raise ValueError('算子文件缺少 get_operators')
  select_op, select_mach = mod.get_operators()
  algo = types.SimpleNamespace(
      select_operation=select_op,
      select_machine=select_mach,
  )
  return algo


def export_split_operators(get_operators_path: str) -> None:
  """将 get_operators 展开为 MA4PGO 风格的两个独立算子文件。"""
  with open(get_operators_path, 'r', encoding='utf-8') as f:
    src = f.read()
  mod = types.ModuleType('export_mod')
  exec(src, mod.__dict__)  # pylint: disable=exec-used
  select_op, select_mach = mod.get_operators()
  op_lines = _function_source(select_op, 'select_operation')
  mach_lines = _function_source(select_mach, 'select_machine')
  os.makedirs(RESULTS_DIR, exist_ok=True)
  with open(BEST_OPERATION_PATH, 'w', encoding='utf-8') as f:
    f.write(op_lines)
  with open(BEST_MACHINE_PATH, 'w', encoding='utf-8') as f:
    f.write(mach_lines)


def _function_source(fn, name: str) -> str:
  import inspect
  try:
    return inspect.getsource(fn)
  except OSError:
    return f'def {name}(*args, **kwargs):\n  raise NotImplementedError()\n'


def run_batch_and_save_csv(operators_path: str | None = None) -> None:
  os.makedirs(RESULTS_DIR, exist_ok=True)
  algo_module = load_algorithm_module(operators_path)
  evaluator = FJSPEvaluator(DATA_DIR)
  print('加载算法: get_operators()')

  for csv_name, rel_path, optimal_csv_name in TARGET_FOLDERS:
    optimal_dict = load_optimal_dict(optimal_csv_name)
    file_list = collect_fjs_in_folder(rel_path)
    rows = []
    for test_name, rel_to_data in file_list:
      optimal = lookup_optimal(test_name, optimal_dict)
      instance = GetData(rel_to_data, DATA_DIR).get_instance()
      if not instance or instance.get('num_jobs') is None:
        rows.append((test_name, '', calc_relative_gap('', optimal)))
        continue
      try:
        makespan, _ = evaluator.fjsp_solver(
            instance['num_jobs'],
            instance['num_job_operations'],
            instance['machine_process_times'],
            algo_module,
        )
        ms = makespan if makespan is not None else ''
        rows.append((test_name, ms, calc_relative_gap(ms, optimal)))
      except Exception:
        rows.append((test_name, '', calc_relative_gap('', optimal)))

    csv_path = os.path.join(RESULTS_DIR, f'{csv_name}.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
      w = csv.writer(f)
      w.writerow(['测试数据名称', 'makespan', '(makespan-最优)/最优'])
      w.writerows(rows)
    print(f'已写入: {csv_path} (共 {len(rows)} 条)')


if __name__ == '__main__':
  path = sys.argv[1] if len(sys.argv) > 1 else BEST_OPERATORS_PATH
  if os.path.isfile(path):
    export_split_operators(path)
  run_batch_and_save_csv(path)
