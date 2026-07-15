def fjsp_solver(n_jobs, n_machines, durations):
    # ---------- helper data ----------
    n_ops = [len(job) for job in durations]
    total_ops = sum(n_ops)
    # Precompute remaining minimum work for each job from each operation
    remaining_min_work = [[0] * (n_ops[j] + 1) for j in range(n_jobs)]
    for j in range(n_jobs):
        for op in range(n_ops[j] - 1, -1, -1):
            best = min(durations[j][op], key=lambda x: x[1])[1]
            remaining_min_work[j][op] = best + remaining_min_work[j][op + 1]

    # ---------- new priority weights (mutated from elite) ----------
    ALPHA = 0.80  # slightly lower blend from earlier elite (0.85)

    # ---------- priority functions (modified to improve worst instances) ----------
    def job_priority(job_idx, next_op, machine_ready_time, job_ready_time):
        op_idx = next_op[job_idx]
        candidates = durations[job_idx][op_idx]
        min_start = min(
            max(machine_ready_time[m], job_ready_time[job_idx])
            for m, _ in candidates
        )
        # New elite part with adjusted weights
        # Remaining work coefficient increased, machine load coefficient reduced
        optimistic_completion = min_start + remaining_min_work[job_idx][op_idx]
        avg_machine_load = sum(machine_ready_time[m] for m, _ in candidates) / len(candidates)
        elite_val = (min_start
                     - 0.35 * remaining_min_work[job_idx][op_idx]
                     + 0.15 * avg_machine_load
                     + 0.30 * optimistic_completion)
        # Base part is just min_start
        hybrid = ALPHA * elite_val + (1 - ALPHA) * min_start
        return (hybrid, job_idx)

    def machine_priority(job_idx, machine_id, processing_time,
                         next_op, machine_ready_time, job_ready_time):
        op_idx = next_op[job_idx]
        start_time = max(machine_ready_time[machine_id], job_ready_time[job_idx])
        completion = start_time + processing_time
        # New machine priority: stronger penalty on machine load,
        # smaller bonus for job remaining work, negative weight on processing time removed
        machine_load = machine_ready_time[machine_id] + processing_time
        job_rem = remaining_min_work[job_idx][op_idx]
        new_val = completion + 0.5 * machine_load + 0.25 * job_rem - 0.1 * processing_time
        base_val = start_time + processing_time
        hybrid = ALPHA * new_val + (1 - ALPHA) * base_val
        return (hybrid, machine_ready_time[machine_id], processing_time, machine_id)

    # ---------- constructive scheduler ----------
    schedule = [[None] * len(durations[j]) for j in range(n_jobs)]
    machine_ready_time = [0] * n_machines
    job_ready_time = [0] * n_jobs
    next_op = [0] * n_jobs
    remaining = total_ops

    while remaining > 0:
        ready_jobs = [j for j in range(n_jobs) if next_op[j] < n_ops[j]]

        # Select job using the new job_priority
        job_idx = min(ready_jobs,
                      key=lambda j: job_priority(j, next_op, machine_ready_time, job_ready_time))

        op_idx = next_op[job_idx]
        candidates = durations[job_idx][op_idx]

        # Select machine using the new machine_priority
        machine_id, processing_time = min(
            candidates,
            key=lambda pair: machine_priority(job_idx, pair[0], pair[1],
                                              next_op, machine_ready_time, job_ready_time)
        )

        start_time = max(machine_ready_time[machine_id], job_ready_time[job_idx])
        schedule[job_idx][op_idx] = (machine_id, start_time, processing_time)
        end_time = start_time + processing_time
        machine_ready_time[machine_id] = end_time
        job_ready_time[job_idx] = end_time
        next_op[job_idx] += 1
        remaining -= 1

    return schedule