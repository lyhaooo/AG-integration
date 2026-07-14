"""Best evolved get_operators from FunSearch-FJSP."""
import sys
sys.path.insert(0, '/Users/liyihao/Desktop/常用/项目/AG integration/backend/funsearch')

def get_operators():
  """返回工序选择算子与机器选择算子 (select_operation, select_machine)。"""
  def select_operation(
      num_jobs,
      num_job_operations,
      job_current_operation,
      machine_process_times,
      machine_available_time,
  ):
    best_score = float('-inf')
    chosen = None
    for j in range(num_jobs):
      if job_current_operation[j] >= num_job_operations[j]:
        continue
      op_id = job_current_operation[j]
      eligible = machine_process_times[j][op_id]
      remaining_ops = num_job_operations[j] - job_current_operation[j]
      earliest_machine = min(
          machine_available_time[m] for m, _ in eligible)
      score = remaining_ops * 2 - earliest_machine
      if score > best_score:
        best_score = score
        chosen = j
    return chosen

  def select_machine(machine_process_times, machine_available_time):
    best_finish = float('inf')
    chosen_machine = 0
    for machine, process_time in machine_process_times:
      finish = machine_available_time[machine] + process_time
      if finish < best_finish:
        best_finish = finish
        chosen_machine = machine
    return chosen_machine

  return select_operation, select_machine

