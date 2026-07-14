def fjsp_correctness_checker(schedule, n_jobs, n_machines, durations):
    """
    Expected format:
      - schedule: list[list[tuple(machine_id, start_time, duration)]]
      - durations[job_idx][op_idx]: list[tuple(machine_id, duration)]
    """
    debug = False
    if not isinstance(n_jobs, int) or not isinstance(n_machines, int):
        print("n_jobs or n_machines is not an integer")
        return False
    if n_jobs < 0 or n_machines <= 0:
        print("n_jobs or n_machines is not positive")
        return False
    if not isinstance(durations, list) or len(durations) != n_jobs:
        print("durations is not a list or the length of durations is not equal to n_jobs")
        return False
    
    # ===== Check if schedule is correct: all jobs must complete all operations =====
    if not isinstance(schedule, list):
        if debug: print("schedule is not a list")
        return "schedule is not a list"
    if len(schedule) != n_jobs:
        if debug: print("the length of schedule is not equal to n_jobs")
        return "the length of schedule is not equal to n_jobs"

    num_job_operations = []
    for job_idx in range(n_jobs):
        job_ops = durations[job_idx]
        if not isinstance(job_ops, list):
            print("durations[%d] is not a list" % job_idx)
            return False
        num_job_operations.append(len(job_ops))

    expected_total_ops = sum(num_job_operations)
    actual_total_ops = 0
    for job_sched in schedule:
        if not isinstance(job_sched, list):
            if debug: print("schedule[%d] is not a list" % job_idx)
            return "schedule[%d] is not a list" % job_idx
        actual_total_ops += len(job_sched)
    if actual_total_ops != expected_total_ops:
        if debug: print("the number of operations in schedule is not equal to the number of operations in durations")
        return "the number of operations in schedule is not equal to the number of operations in durations"

    # 按作业统计 schedule 中的工序（本项目中工序索引由列表位置隐式定义）
    for job_idx in range(n_jobs):
        expected_ops = num_job_operations[job_idx]
        if len(schedule[job_idx]) != expected_ops:
            if debug: print("the number of operations in schedule[%d] is not equal to the number of operations in durations[%d]" % (job_idx, job_idx))
            return "the number of operations in schedule[%d] is not equal to the number of operations in durations[%d]" % (job_idx, job_idx)

    # 收集机器上的已安排区间，用于检查机器不重叠
    machine_intervals = [[] for _ in range(n_machines)]

    for job_idx in range(n_jobs):
        prev_end = 0
        for op_idx, entry in enumerate(schedule[job_idx]):
            if not isinstance(entry, (tuple, list)) or len(entry) != 3:
                if debug: print("schedule[%d][%d] is not a tuple or list or the length of schedule[%d][%d] is not equal to 3" % (job_idx, op_idx, job_idx, op_idx))
                return "schedule[%d][%d] is not a tuple or list or the length of schedule[%d][%d] is not equal to 3" % (job_idx, op_idx, job_idx, op_idx)
            machine_id, start_time, op_duration = entry

            # 基础字段检查
            if not isinstance(machine_id, int) or not isinstance(start_time, int) or not isinstance(op_duration, int):
                if debug: print("schedule[%d][%d] is not a tuple or list or the length of schedule[%d][%d] is not equal to 3" % (job_idx, op_idx, job_idx, op_idx))
                return "schedule[%d][%d] is not a tuple or list or the length of schedule[%d][%d] is not equal to 3" % (job_idx, op_idx, job_idx, op_idx)
            if machine_id < 0 or machine_id >= n_machines:
                if debug: print("machine_id is not a valid machine id")
                return "machine_id is not a valid machine id"
            if start_time < 0 or op_duration < 0:
                if debug: print("start_time or op_duration is not a valid start time or duration")
                return "start_time or op_duration is not a valid start time or duration"

            # 检查该工序是否允许分配到该机器，且时长是否匹配
            if op_idx >= len(durations[job_idx]):
                if debug: print("op_idx is greater than the number of operations in durations[%d]" % job_idx)
                return "op_idx is greater than the number of operations in durations[%d]" % job_idx
            candidates = durations[job_idx][op_idx]
            if not isinstance(candidates, list) or len(candidates) == 0:
                if debug: print("candidates is not a list or the length of candidates is 0")
                return "candidates is not a list or the length of candidates is 0"

            feasible = False
            for cand in candidates:
                if (
                    isinstance(cand, (tuple, list))
                    and len(cand) == 2
                    and cand[0] == machine_id
                    and cand[1] == op_duration
                ):
                    feasible = True
                    break
            if not feasible:
                if debug: print("the operation is not feasible")
                return "the operation is not feasible"

            # 作业内工序先后约束
            if start_time < prev_end:
                if debug: print("the start time is less than the previous end time")
                return "the start time is less than the previous end time"
            end_time = start_time + op_duration
            prev_end = end_time

            machine_intervals[machine_id].append((start_time, end_time, job_idx, op_idx))

    # 机器容量约束：同一机器上工序不可重叠
    for machine_id in range(n_machines):
        intervals = sorted(machine_intervals[machine_id], key=lambda x: (x[0], x[1]))
        for i in range(1, len(intervals)):
            prev_start, prev_end, _, _ = intervals[i - 1]
            curr_start, _, _, _ = intervals[i]
            if curr_start < prev_end:
                if debug: print("the current start time is less than the previous end time")
                return "the current start time is less than the previous end time"

    return True

