import os
import sys
import json
from pathlib import Path

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    import our.tools.sample_manager as SM
except ImportError:  # 兼容旧 fjsp 包目录名称
    import fjsp.tools.sample_manager as SM


class prompt:
    def __init__(self):
        self._config = self._load_config()
        default_task = (
            "Flexible Job Shop Scheduling Problem (FJSP): choose a feasible machine "
            "and start time for every operation of every job. The objective is to "
            "minimize makespan while preserving job precedence and machine capacity."
        )
        self.task_description = self._value("generator", "task_description", default_task)

    @staticmethod
    def _load_config() -> dict:
        path = Path(__file__).resolve().parents[1] / "config" / "prompts.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _value(self, agent: str, key: str, fallback: str) -> str:
        value = self._config.get(agent, {}).get("instructions", {}).get(key)
        return value.strip() if isinstance(value, str) and value.strip() else fallback

    def get_prompt_gen_G(self, variant_index: int = 1):
        return self._generation_prompt(
            action="Gen(G)",
            strategy_intent=self._value("generator", "global_strategy", (
                "Improve the overall scheduling structure. You may change both "
                "machine assignment and operation sequencing, but keep the public "
                "solver interface and schedule format unchanged."
            )),
            variant_instruction=self._variant_instruction("G", variant_index),
        )

    def get_prompt_gen_E(self, advice: str = "", variant_index: int = 1):
        elite_code = SM.get_elite_code_context()
        return self._generation_prompt(
            action="Gen(E)",
            strategy_intent=self._value("generator", "elite_strategy", (
                "Exploit the current elite solver as a parent. Keep the reliable "
                "fixed-slot scheduling structure, but mutate one or two priority "
                "rules to beat the elite average score. Do not rewrite from scratch."
            )) + f"\nExtra advice:\n{advice or 'No external advice was provided.'}",
            variant_instruction=self._variant_instruction("E", variant_index),
            elite_code=elite_code,
            instance_diagnostics=SM.summarize_best_instance_gaps(top_k=6),
            recent_errors=SM.summarize_recent_errors(top_k=4),
        )

    def get_prompt_gen_L(self, advice: str = "", variant_index: int = 1):
        return self._generation_prompt(
            action="Gen(L)",
            strategy_intent=self._value("generator", "local_strategy", (
                "Apply the following improvement advice as the main design goal. "
                "Make a focused strategy change rather than a cosmetic rewrite."
            )) + f"\nAdvice:\n{advice or 'No external advice was provided.'}",
            variant_instruction=self._variant_instruction("L", variant_index),
            elite_code=SM.get_elite_code_context(max_chars=5500),
            instance_diagnostics=SM.summarize_best_instance_gaps(top_k=5),
            recent_errors=SM.summarize_recent_errors(top_k=4),
        )

    def get_prompt_gen_M(self, variant_index: int = 1):
        return self._generation_prompt(
            action="Gen(M)",
            strategy_intent=self._value("generator", "machine_strategy", (
                "Focus on machine assignment. Try ideas such as earliest available "
                "machine, shortest processing time, workload balancing, and avoiding "
                "future bottleneck machines."
            )),
            variant_instruction=self._variant_instruction("M", variant_index),
        )

    def get_prompt_gen_O(self, variant_index: int = 1):
        return self._generation_prompt(
            action="Gen(O)",
            strategy_intent=self._value("generator", "operation_strategy", (
                "Focus on operation sequencing. Try ideas such as shortest operation "
                "first, largest remaining work first, bottleneck-first dispatching, "
                "and tie-break rules that reduce downstream waiting."
            )),
            variant_instruction=self._variant_instruction("O", variant_index),
        )

    def get_prompt_revise_code_error(self, error_type: str, error_message: str, code: str):
        return self._revise_prompt(
            revise_goal=self._value("reviser", "code_error_goal", (
                "Fix code-level problems only: syntax, missing fjsp_solver, wrong "
                "function signature, imports, runtime exceptions, or invalid return type."
            )),
            error_type=error_type,
            error_message=error_message,
            code=code,
        )

    def get_prompt_revise_schedule_error(self, error_type: str, error_message: str, code: str):
        return self._revise_prompt(
            revise_goal=self._value("reviser", "schedule_error_goal", (
                "Fix schedule feasibility. Preserve the algorithm style if possible, "
                "but correct job precedence, machine overlap, eligible machine choices, "
                "processing durations, and the final nested-list schedule format."
            )),
            error_type=error_type,
            error_message=error_message,
            code=code,
        )

    def get_prompt_revise_performance(self, error_type: str, error_message: str, code: str):
        return self._revise_prompt(
            revise_goal=self._value("reviser", "performance_goal", (
                "Improve performance without sacrificing feasibility. Make a small, "
                "explainable adjustment to machine assignment, operation sequencing, "
                "or tie-break logic."
            )),
            error_type=error_type,
            error_message=error_message,
            code=code,
        )

    def get_prompt_revise(self, error_type: str, error_message: str, code: str):
        if error_type in {"data_shape_error", "index_error", "schedule_index_error", "schedule_invalid"}:
            return self.get_prompt_revise_schedule_error(error_type, error_message, code)
        if error_type in {"evaluation_failed", "performance_regression"}:
            return self.get_prompt_revise_performance(error_type, error_message, code)
        return self.get_prompt_revise_code_error(error_type, error_message, code)

    def get_prompt_question(self, evo_state: str, sample_summary: str):
        role = self._value("questioner", "system_role", "You are helping design the next FJSP heuristic improvement.")
        requirements = self._value("questioner", "output_requirements", "Return only a concise improvement memo with: 1. one likely bottleneck in the current search, 2. one concrete strategy change to try next, 3. one risk to avoid. Do not write code.")
        return f"""
{role}

Task:
{self.task_description}

Current evolution state:
{evo_state}

Historical sample lessons:
{sample_summary}

{requirements}
""".strip()

    def get_prompt_describe(self, code: str, score: float, best_score: float):
        role = self._value("describer", "system_role", "Summarize this FJSP solver candidate for future retrieval.")
        requirements = self._value("describer", "output_requirements", "Return 2-4 short sentences covering the main scheduling idea, what changed, and likely risks.")
        return f"""
{role}

Current score: {score}
Previous best score: {best_score}

Code:
```python
{code}
```

{requirements}
""".strip()

    def _generation_prompt(
        self,
        action: str,
        strategy_intent: str,
        variant_instruction: str,
        elite_code: str = "",
        instance_diagnostics: str = "",
        recent_errors: str = "",
    ) -> str:
        sample_summary = SM.summarize_top_samples(top_k=3)
        elite_section = ""
        if elite_code:
            elite_section = f"""
Current elite parent code:
```python
{elite_code}
```

Elite diagnostics:
{instance_diagnostics or 'No elite diagnostics are available.'}

Recent mistakes to avoid:
{recent_errors or 'No recent errors are recorded.'}

Elite improvement rule:
- Preserve the parent solver's valid schedule representation and helper precomputations unless your change needs them adjusted.
- Make a targeted mutation to priority weights, tie-breakers, or one-step lookahead.
- The result must be different from the elite code in a way that can plausibly improve the worst listed instances.
""".strip()

        system_role = self._value("generator", "system_role", "You are an expert in operations research and Python.")
        configured_constraints = self._value("generator", "output_constraints", "Return only executable Python code.")
        return f"""
{system_role}

Task:
{self.task_description}

Action:
{action}

Strategy intent:
{strategy_intent}

Required strategy variant:
{variant_instruction}

Historical sample lessons:
{sample_summary}

{elite_section}

Required Python interface:
def fjsp_solver(n_jobs, n_machines, durations):
    ...

Input shape:
- durations[job_idx][op_idx] is a list of (machine_id, processing_time).
- machine_id is 0-based.
- Example: durations[0][0] may be [(0, 12), (3, 9)], so you must choose one
  candidate pair before unpacking machine_id and processing_time.

Correct access pattern:
for candidates in durations[job_idx]:
    machine_id, processing_time = min(candidates, key=lambda pair: pair[1])

Forbidden access patterns:
- machine_id, processing_time = durations[job_idx][op_idx]
- for op_idx, (machine_id, processing_time) in enumerate(durations[job_idx])
- durations[job_idx][op_idx][1] as if it were a single processing time
- Expanding every candidate machine into a separate scheduled operation.
- Appending operations with schedule[job_idx].append(...) when op_idx order matters.

Safe scheduling structure:
- Initialize schedule = [[None] * len(durations[j]) for j in range(n_jobs)].
- Maintain job_ready_time[j] as the end time of the last scheduled operation of job j.
- Maintain machine_ready_time[m] as the next available time of machine m.
- At each step, choose one ready operation per unfinished job: op_idx = next_op[j].
- Choose exactly one (machine_id, processing_time) from durations[j][op_idx].
- Write it to schedule[j][op_idx], never append.
- Then increment next_op[j] by 1.

Minimal safe skeleton you may adapt:
def fjsp_solver(n_jobs, n_machines, durations):
    schedule = [[None] * len(durations[j]) for j in range(n_jobs)]
    machine_ready_time = [0] * n_machines
    job_ready_time = [0] * n_jobs
    next_op = [0] * n_jobs
    remaining = sum(len(job) for job in durations)
    while remaining > 0:
        ready_jobs = [j for j in range(n_jobs) if next_op[j] < len(durations[j])]
        job_idx = min(ready_jobs, key=lambda j: job_ready_time[j])
        op_idx = next_op[job_idx]
        candidates = durations[job_idx][op_idx]
        machine_id, processing_time = min(
            candidates,
            key=lambda pair: (max(machine_ready_time[pair[0]], job_ready_time[job_idx]) + pair[1], pair[1], pair[0]),
        )
        start_time = max(machine_ready_time[machine_id], job_ready_time[job_idx])
        schedule[job_idx][op_idx] = (machine_id, start_time, processing_time)
        end_time = start_time + processing_time
        machine_ready_time[machine_id] = end_time
        job_ready_time[job_idx] = end_time
        next_op[job_idx] += 1
        remaining -= 1
    return schedule

Important diversity rule:
- The skeleton above is only a correctness scaffold.
- Do not copy the skeleton unchanged.
- You must change at least one decision rule according to the Required strategy variant.
- Keep the fixed-slot schedule structure, but make the priority functions meaningfully different.

Output shape:
- Return schedule as list[list[tuple[int, int, int]]].
- schedule[job_idx][op_idx] = (machine_id, start_time, duration).

Hard constraints:
- Every operation must be scheduled exactly once.
- Operations of the same job must follow their original order.
- A machine can process at most one operation at a time.
- The chosen machine and duration must match durations[job_idx][op_idx].
- Use only Python standard library.

Configured output constraints:
{configured_constraints}

Return only executable Python code. Do not include markdown fences or explanations.
""".strip()

    def _variant_instruction(self, gen_type: str, variant_index: int) -> str:
        variants = {
            "O": [
                "Change job selection: choose the ready job with the largest total remaining minimum processing time.",
                "Change job selection: choose the ready job whose current operation has the shortest best processing time.",
                "Change job selection: prefer jobs whose current operation has fewer eligible machines, then larger remaining work.",
            ],
            "M": [
                "Change machine selection: minimize earliest completion time plus current machine load.",
                "Change machine selection: prefer the fastest eligible machine, then the least loaded machine.",
                "Change machine selection: penalize machines that are bottlenecks for many future operations.",
            ],
            "G": [
                "Change both priorities: use largest remaining job work for sequencing and load-aware earliest completion for machines.",
                "Add one-step lookahead: when choosing a machine, also consider the next operation's best possible completion.",
                "Use bottleneck awareness: prioritize constrained operations and avoid overloading high-demand machines.",
            ],
            "L": [
                "Follow the advice, but make a concrete change to the job priority function.",
                "Follow the advice, but make a concrete change to the machine scoring function.",
                "Follow the advice, and combine one job-priority change with one machine-scoring change.",
            ],
            "E": [
                "Mutate the elite job priority weights to target the worst instance gaps; keep machine scoring mostly stable.",
                "Mutate the elite machine scoring weights or tie-breakers to reduce bottleneck machine congestion.",
                "Add or adjust a one-step lookahead term in the elite while preserving feasibility and fixed-slot output.",
                "Hybridize the elite with one top historical lesson, changing only the priority functions.",
            ],
        }
        options = variants.get(gen_type, variants["G"])
        selected = options[(max(variant_index, 1) - 1) % len(options)]
        return (
            f"Variant {variant_index}: {selected} "
            "Implement this variant explicitly in code; do not return the default earliest-ready skeleton."
        )

    def _revise_prompt(self, revise_goal: str, error_type: str, error_message: str, code: str) -> str:
        role = self._value("reviser", "system_role", "You are revising a generated FJSP solver.")
        configured_constraints = self._value("reviser", "output_constraints", "Return only executable Python code.")
        return f"""
{role}

Revision goal:
{revise_goal}

Error type:
{error_type}

Error message:
{error_message}

Required interface and output:
- Keep exactly this public function: fjsp_solver(n_jobs, n_machines, durations)
- Return schedule as list[list[tuple[int, int, int]]]
- Use only Python standard library
- Return only executable Python code, no markdown fences, no explanation

Configured output constraints:
{configured_constraints}

Important data shape:
- durations[job_idx][op_idx] is a candidate list: [(machine_id, processing_time), ...]
- Always choose one candidate pair before unpacking it.
- Never unpack durations[job_idx] or durations[job_idx][op_idx] directly as if each operation had only one machine.
- Initialize schedule with fixed operation slots and assign by op_idx:
  schedule = [[None] * len(durations[j]) for j in range(n_jobs)]
  schedule[job_idx][op_idx] = (machine_id, start_time, processing_time)
- Do not use schedule[job_idx].append(...) for operation results.
- Do not schedule one row for each candidate machine; schedule exactly one row for each operation.

Original code:
```python
{code}
```
""".strip()
