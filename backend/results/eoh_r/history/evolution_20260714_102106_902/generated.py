"""EoH generated FJSP heuristic."""
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
