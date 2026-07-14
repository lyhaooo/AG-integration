"""Our multi-agent generated FJSP heuristic.
Selected weights: flexibility=1.0, readiness=0.2, balance=0.0.
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
        score = critical_work / max(flexibility ** 1.0, 1) - 0.2 * current_finish
        candidates.append((score, critical_work, -job, job))
    return max(candidates)[-1] if candidates else None

def select_machine(choices, machine_available):
    average_load = sum(machine_available) / max(len(machine_available), 1)
    return min(choices, key=lambda item: (machine_available[item[0]] + item[1] + 0.0 * abs(machine_available[item[0]] - average_load), item[1], item[0]))[0]
