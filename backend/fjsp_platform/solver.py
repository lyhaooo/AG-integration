from __future__ import annotations

from .algorithms import Algorithm
from .datasets import FJSPInstance


def solve(instance: FJSPInstance, algorithm: Algorithm) -> int:
    current = [0] * instance.num_jobs
    machine_available = [0] * instance.num_machines
    job_available = [0] * instance.num_jobs
    completed = 0
    expected = sum(len(job) for job in instance.operations)

    while completed < expected:
        job = algorithm.select_operation(
            instance.num_jobs,
            [len(ops) for ops in instance.operations],
            current,
            instance.operations,
            machine_available,
        )
        if job is None or not 0 <= job < instance.num_jobs or current[job] >= len(instance.operations[job]):
            raise ValueError("工序选择算子返回了无效作业")
        choices = instance.operations[job][current[job]]
        machine = algorithm.select_machine(choices, machine_available)
        duration = next((time for candidate, time in choices if candidate == machine), None)
        if duration is None:
            raise ValueError("机器选择算子返回了不可用机器")
        start = max(machine_available[machine], job_available[job])
        finish = start + duration
        machine_available[machine] = finish
        job_available[job] = finish
        current[job] += 1
        completed += 1
    return max(job_available, default=0)


class GeneratedSolver:
    """加载三种引擎的不同代码接口并统一为 makespan 求解。"""

    def __init__(self, code: str, method: str):
        namespace: dict = {}
        exec(compile(code, f"<{method}_generated>", "exec"), namespace)
        self._fjsp_solver = namespace.get("fjsp_solver")
        if callable(namespace.get("get_operators")):
            select_operation, select_machine = namespace["get_operators"]()
            self._algorithm = Algorithm(select_operation, select_machine, code)
        elif callable(namespace.get("select_operation")) and callable(namespace.get("select_machine")):
            self._algorithm = Algorithm(namespace["select_operation"], namespace["select_machine"], code)
        else:
            self._algorithm = None
        if not callable(self._fjsp_solver) and self._algorithm is None:
            raise ValueError("生成代码必须提供 fjsp_solver、get_operators 或两个 select_* 函数")

    def solve(self, instance: FJSPInstance) -> int:
        if self._algorithm is not None:
            return solve(instance, self._algorithm)
        schedule = self._fjsp_solver(instance.num_jobs, instance.num_machines, instance.operations)
        self._validate_schedule(instance, schedule)
        return max(
            int(start) + int(duration)
            for job in schedule
            for _, start, duration in job
        )

    @staticmethod
    def _validate_schedule(instance: FJSPInstance, schedule) -> None:
        if not isinstance(schedule, list) or len(schedule) != instance.num_jobs:
            raise ValueError("fjsp_solver 返回的作业数量不正确")
        machine_intervals: list[list[tuple[int, int]]] = [[] for _ in range(instance.num_machines)]
        for job_index, job in enumerate(schedule):
            if not isinstance(job, list) or len(job) != len(instance.operations[job_index]):
                raise ValueError("fjsp_solver 返回的工序数量不正确")
            previous_end = 0
            for operation_index, entry in enumerate(job):
                if not isinstance(entry, (tuple, list)) or len(entry) != 3:
                    raise ValueError("调度项必须是 (machine_id, start_time, duration)")
                machine, start, duration = map(int, entry)
                if (machine, duration) not in instance.operations[job_index][operation_index]:
                    raise ValueError("调度使用了不可选机器或错误加工时间")
                if start < previous_end:
                    raise ValueError("作业内工序违反先后约束")
                end = start + duration
                previous_end = end
                machine_intervals[machine].append((start, end))
        for intervals in machine_intervals:
            intervals.sort()
            if any(intervals[index][0] < intervals[index - 1][1] for index in range(1, len(intervals))):
                raise ValueError("机器加工区间发生重叠")
