from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

OperationSelector = Callable[[int, list[int], list[int], list, list[int]], int | None]
MachineSelector = Callable[[list[tuple[int, int]], list[int]], int]


@dataclass(frozen=True)
class Algorithm:
    select_operation: OperationSelector
    select_machine: MachineSelector
    code: str


EOH_CODE = '''"""EoH generated FJSP heuristic."""
def select_operation(num_jobs, num_job_operations, current, operations, machine_available):
    candidates = []
    for job in range(num_jobs):
        if current[job] >= num_job_operations[job]:
            continue
        remaining = operations[job][current[job]:]
        remaining_work = sum(min(t for _, t in op) for op in remaining)
        ready = min(machine_available[m] for m, _ in remaining[0])
        candidates.append((remaining_work - 0.15 * ready, -job, job))
    return max(candidates)[2] if candidates else None

def select_machine(choices, machine_available):
    return min(choices, key=lambda item: (machine_available[item[0]] + item[1], item[1], item[0]))[0]
'''

FUNSEARCH_CODE = '''"""FunSearch generated FJSP heuristic."""
def select_operation(num_jobs, num_job_operations, current, operations, machine_available):
    best = None
    for job in range(num_jobs):
        if current[job] >= num_job_operations[job]:
            continue
        op = operations[job][current[job]]
        fastest = min(t for _, t in op)
        earliest = min(machine_available[m] + t for m, t in op)
        remaining = num_job_operations[job] - current[job]
        key = (remaining * fastest - 0.2 * earliest, -earliest, -job, job)
        best = key if best is None or key > best else best
    return best[-1] if best else None

def select_machine(choices, machine_available):
    return min(choices, key=lambda item: (machine_available[item[0]] + 1.15 * item[1], machine_available[item[0]], item[0]))[0]
'''

OUR_TEMPLATE = '''"""Our multi-agent generated FJSP heuristic.
Selected weights: flexibility={flexibility_weight}, readiness={readiness_weight}, balance={balance_weight}.
"""
def select_operation(num_jobs, num_job_operations, current, operations, machine_available):
    candidates = []
    for job in range(num_jobs):
        if current[job] >= num_job_operations[job]:
            continue
        remaining_ops = operations[job][current[job]:]
        critical_work = sum(min(t for _, t in op) for op in remaining_ops)
        flexibility = sum(len(op) for op in remaining_ops) / len(remaining_ops)
        current_finish = min(machine_available[m] + t for m, t in remaining_ops[0])
        score = critical_work / max(flexibility ** {flexibility_weight}, 1) - {readiness_weight} * current_finish
        candidates.append((score, critical_work, -job, job))
    return max(candidates)[-1] if candidates else None

def select_machine(choices, machine_available):
    average_load = sum(machine_available) / max(len(machine_available), 1)
    return min(choices, key=lambda item: (machine_available[item[0]] + item[1] + {balance_weight} * abs(machine_available[item[0]] - average_load), item[1], item[0]))[0]
'''

def render_our_code(flexibility_weight: float, readiness_weight: float, balance_weight: float) -> str:
    return OUR_TEMPLATE.format(
        flexibility_weight=flexibility_weight,
        readiness_weight=readiness_weight,
        balance_weight=balance_weight,
    )


OUR_CODE = render_our_code(1.0, 0.12, 0.08)
CODE_BY_METHOD = {"eoh": EOH_CODE, "funsearch": FUNSEARCH_CODE, "our": OUR_CODE}


def load_algorithm(method: str) -> Algorithm:
    return algorithm_from_code(method, CODE_BY_METHOD[method])


def algorithm_from_code(method: str, code: str) -> Algorithm:
    namespace: dict = {}
    exec(compile(code, f"<{method}_generated>", "exec"), namespace)
    return Algorithm(namespace["select_operation"], namespace["select_machine"], code)
