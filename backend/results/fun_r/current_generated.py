"""FunSearch generated FJSP heuristic."""
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
