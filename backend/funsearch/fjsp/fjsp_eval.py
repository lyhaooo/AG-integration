# -*- coding: utf-8 -*-
"""
FJSP 评测（对齐 MA4PGO）：
将工序选择算子与机器选择算子组合，在指定实例集上求解，
每个实例得 (makespan-最优)/最优，去掉最大最小后取平均作为 fitness（越小越好）。
"""

import os
import types
import warnings
from collections import defaultdict

from fjsp.get_instance import GetData


def _trimmed_mean(scores: list[float]) -> float:
  if not scores:
    return float('inf')
  if len(scores) >= 3:
    trimmed = sorted(scores)[1:-1]
  else:
    trimmed = scores
  return float(sum(trimmed) / len(trimmed))


class FJSPEvaluator:
  """组合 select_operation 与 select_machine，在 benchmark 实例上评测。"""

  def __init__(self, data_dir: str | None = None):
    self._data_dir = data_dir or os.getenv('FJSP_DATA_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data')

  def _load_optimal_dict(self, optimal_csv_name: str) -> dict[str, float]:
    csv_path = os.path.join(self._data_dir, optimal_csv_name)
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

  def fjsp_solver(
      self,
      num_jobs: int,
      num_job_operations: list[int],
      machine_process_times: list,
      alg,
  ):
    schedule = []
    job_current_operation = [0] * num_jobs
    machine_available_time: defaultdict[int, int] = defaultdict(int)
    job_available_time = [0] * num_jobs
    makespan = 0
    while True:
      job_idx = alg.select_operation(
          num_jobs,
          num_job_operations,
          job_current_operation,
          machine_process_times,
          machine_available_time,
      )
      if job_idx is None:
        break
      if not (0 <= job_idx < num_jobs
              and job_current_operation[job_idx] < num_job_operations[job_idx]):
        makespan = None
        break

      op_idx = job_current_operation[job_idx]
      machine_id = alg.select_machine(
          machine_process_times[job_idx][op_idx],
          machine_available_time,
      )
      processing_time = None
      for mid, p_time in machine_process_times[job_idx][op_idx]:
        if mid == machine_id:
          processing_time = int(p_time)
          break
      if processing_time is None:
        raise ValueError(
            f'未在 machine_process_times 中找到 machine_id={machine_id}')

      start_time = int(max(
          int(machine_available_time[machine_id]),
          int(job_available_time[job_idx]),
      ))
      end_time = int(start_time + processing_time)
      schedule.append((int(job_idx), int(op_idx), int(machine_id),
                       int(start_time), int(end_time)))
      machine_available_time[machine_id] = int(end_time)
      job_available_time[job_idx] = int(end_time)
      job_current_operation[job_idx] += 1
      makespan = int(max(int(entry[4]) for entry in schedule)) if schedule else 0

    expected_total_ops = sum(num_job_operations)
    if len(schedule) != expected_total_ops:
      makespan = None
    job_op_count: defaultdict[int, list[int]] = defaultdict(list)
    for job_idx, op_idx, _, _, _ in schedule:
      job_op_count[job_idx].append(op_idx)
    for job_idx in range(num_jobs):
      expected_ops = num_job_operations[job_idx]
      actual_ops = sorted(job_op_count[job_idx])
      expected_op_indices = list(range(expected_ops))
      if len(actual_ops) != expected_ops or actual_ops != expected_op_indices:
        makespan = None
    return makespan, schedule

  def evaluate_folder(
      self,
      rel_folder: str,
      optimal_csv_name: str,
      alg,
  ) -> float | None:
    """在 data 下 rel_folder 文件夹内所有 .fjs 上评测，返回 trimmed mean gap。"""
    folder_path = os.path.join(self._data_dir, rel_folder)
    if not os.path.isdir(folder_path):
      return None
    optimal_dict = self._load_optimal_dict(optimal_csv_name)
    fjs_list = sorted([f for f in os.listdir(folder_path) if f.endswith('.fjs')])
    if not fjs_list:
      return None

    scores: list[float] = []
    for fname in fjs_list:
      name_no_ext = os.path.splitext(fname)[0]
      optimal = optimal_dict.get(name_no_ext.lower())
      if optimal is None or optimal <= 0:
        continue
      rel_to_data = os.path.join(rel_folder, fname).replace('\\', '/')
      instance = GetData(rel_to_data, self._data_dir).get_instance()
      if not instance or instance.get('num_jobs') is None:
        continue
      try:
        makespan, _ = self.fjsp_solver(
            instance['num_jobs'],
            instance['num_job_operations'],
            instance['machine_process_times'],
            alg,
        )
      except Exception:
        return None
      if makespan is None:
        return None
      scores.append((float(int(makespan)) - optimal) / optimal)

    if not scores:
      return None
    return _trimmed_mean(scores)

  def evaluate_combination(self, code_operation: str, code_machine: str) -> float | None:
    """合并两段算子代码字符串并评测（MA4PGO 原始接口）。"""
    self._last_error = None
    try:
      with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        mod = types.ModuleType('combined_heuristic')
        combined_code = (code_operation or '').strip() + '\n\n' + (
            code_machine or '').strip()
        if not combined_code.strip():
          return None
        try:
          exec(combined_code, mod.__dict__)  # pylint: disable=exec-used
        except SyntaxError as e:
          self._last_error = {'type': 'SyntaxError', 'message': str(e)}
          return None
        except Exception as e:
          self._last_error = {'type': type(e).__name__, 'message': str(e)}
          return None
        if not hasattr(mod, 'select_operation') or not hasattr(mod, 'select_machine'):
          return None
      return self.evaluate_folder('Dauzere', 'Dauzere.csv', mod)
    except Exception:
      return None

  def evaluate_get_operators(self, get_operators_fn) -> float | None:
    """从 get_operators() 取得两个算子函数并评测（FunSearch 合并进化接口）。"""
    self._last_error = None
    try:
      select_operation, select_machine = get_operators_fn()
      alg = types.SimpleNamespace(
          select_operation=select_operation,
          select_machine=select_machine,
      )
      return self.evaluate_folder('Dauzere', 'Dauzere.csv', alg)
    except SyntaxError as e:
      self._last_error = {'type': 'SyntaxError', 'message': str(e)}
      return None
    except Exception as e:
      self._last_error = {'type': type(e).__name__, 'message': str(e)}
      return None

  def get_last_error(self):
    return self._last_error
