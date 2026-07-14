# -*- coding: utf-8 -*-
"""从 .fjs 文件加载 FJSP 实例。rel_path 为相对 data 目录的路径，如 'Dauzere/01a.fjs'。"""

import os


class GetData:
  def __init__(self, rel_path: str, data_dir: str | None = None):
    self.rel_path = rel_path.replace('\\', '/')
    if data_dir is None:
      data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    self._data_dir = data_dir
    self._file_path = os.path.join(self._data_dir, self.rel_path)

  def get_instance(self):
    if not os.path.isfile(self._file_path):
      return None
    try:
      with open(self._file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    except OSError:
      return None
    if not lines:
      return None
    all_tokens = []
    for line in lines:
      all_tokens.extend(line.split())
    if len(all_tokens) < 2:
      return None
    try:
      num_jobs = int(all_tokens[0])
      num_machines = int(all_tokens[1])
    except ValueError:
      return None
    pos = 3 if len(all_tokens) > 2 else 2
    num_job_operations = []
    machine_process_times = []
    for _ in range(num_jobs):
      if pos >= len(all_tokens):
        return None
      try:
        n_ops = int(all_tokens[pos])
      except ValueError:
        return None
      pos += 1
      num_job_operations.append(n_ops)
      job_ops = []
      for _ in range(n_ops):
        if pos >= len(all_tokens):
          return None
        try:
          n_mach = int(all_tokens[pos])
        except ValueError:
          return None
        pos += 1
        if pos + 2 * n_mach > len(all_tokens):
          return None
        op_list = []
        for _ in range(n_mach):
          mid = int(all_tokens[pos])
          pt = int(all_tokens[pos + 1])
          pos += 2
          op_list.append((max(0, mid - 1), pt))
        job_ops.append(op_list)
      machine_process_times.append(job_ops)
    return {
        'num_jobs': num_jobs,
        'num_machines': num_machines,
        'num_job_operations': num_job_operations,
        'machine_process_times': machine_process_times,
    }
