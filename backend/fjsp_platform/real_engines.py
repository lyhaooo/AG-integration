from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Callable

from .algorithms import EOH_CODE, algorithm_from_code
from .datasets import DATASETS, load_dataset
from .solver import solve

ProgressCallback = Callable[[int, int, float | None, str], None]


def validate_llm_settings(settings: dict) -> None:
    if settings.get("llm_use_local"):
        if not str(settings.get("llm_local_url", "")).strip():
            raise RuntimeError("已选择本地 LLM，但 Local URL 为空")
        return
    if not str(settings.get("llm_api_endpoint", "")).strip():
        raise RuntimeError("LLM API Endpoint 为空，请先在 Our 参数页面配置")
    if not str(settings.get("llm_api_key", "")).strip():
        raise RuntimeError("LLM API Key 为空，请先在 Our 参数页面配置")
    if not str(settings.get("llm_model", "")).strip():
        raise RuntimeError("LLM Model 为空，请先在 Our 参数页面配置")


class _EOHPrompts:
    def get_task(self):
        return "Design a machine-selection heuristic for FJSP that minimizes makespan."

    def get_func_structure(self):
        return "def select_machine(machine_process_times, machine_available_time):\n    # code\n    return machine_id"

    def get_func_outputs(self):
        return ["machine_id"]

    def get_inout_inf(self):
        return "machine_process_times is [(machine_id, process_time), ...]; machine_available_time gives current machine ready times. Return one eligible machine_id."

    def get_other_inf(self):
        return "Return one description in braces followed by exactly one executable Python select_machine function. Use the Python standard library only."


class _EOHProblem:
    def __init__(self, data_root: Path):
        self.prompts = _EOHPrompts()
        spec = next(item for item in DATASETS if item.name == "Dauzere")
        self.instances = load_dataset(data_root, spec)

    def evaluate(self, generated_code: str):
        try:
            algorithm = algorithm_from_code("eoh", EOH_CODE + "\n\n" + generated_code)
            gaps = [
                (solve(instance, algorithm) - instance.optimal) / instance.optimal
                for instance in self.instances
            ]
            if len(gaps) >= 3:
                gaps = sorted(gaps)[1:-1]
            return sum(gaps) / len(gaps)
        except Exception:
            return float("inf")


class _MockEOHInterface:
    counter = 0

    def __init__(self, *args, **kwargs):
        pass

    def get_response(self, prompt_content):
        type(self).counter += 1
        weight = 1 + type(self).counter % 4
        return (
            "{Load-aware earliest completion machine selection}\n"
            "def select_machine(machine_process_times, machine_available_time):\n"
            "    if not machine_process_times:\n"
            "        return 0\n"
            f"    machine_id = min(machine_process_times, key=lambda pair: (machine_available_time[pair[0]] + {weight} * pair[1], pair[0]))[0]\n"
            "    return machine_id"
        )


def run_eoh_engine(
    settings: dict,
    data_root: Path,
    work_root: Path,
    progress: ProgressCallback,
    stop_event,
    mock: bool = False,
) -> tuple[str, dict]:
    if not mock:
        validate_llm_settings(settings)
    backend_root = data_root.parent
    source_root = backend_root / "eoh" / "eoh" / "src"
    sys.path.insert(0, str(source_root)) if str(source_root) not in sys.path else None
    from eoh import eoh as eoh_api
    from eoh.utils.getParas import Paras
    if mock:
        import eoh.methods.eoh.eoh_evolution_fjsp as evolution_module
        evolution_module.InterfaceLLM = _MockEOHInterface

    output = work_root / "eoh_engine"
    problem = _EOHProblem(data_root)
    paras = Paras()
    paras.set_paras(
        method="eoh", problem=problem,
        llm_api_endpoint=settings.get("llm_api_endpoint"),
        llm_api_key=settings.get("llm_api_key"),
        llm_model=settings.get("llm_model"),
        llm_use_local=bool(settings.get("llm_use_local")),
        llm_local_url=settings.get("llm_local_url"),
        ec_pop_size=max(2, int(settings.get("pop_size", 4))),
        ec_n_pop=max(1, int(settings.get("n_iter", 10))),
        exp_n_proc=1, exp_output_path=str(output), eva_numba_decorator=False,
        progress_callback=lambda current, total, score: progress(current, total, _finite(score), "EoH 种群进化"),
        stop_event=stop_event,
    )
    eoh_api.EVOL(paras).run()
    files = sorted(
        (output / "results" / "pops_best").glob("population_generation_*.json"),
        key=lambda path: int(path.stem.rsplit("_", 1)[-1]),
    )
    if not files:
        raise RuntimeError("EoH 未生成有效种群结果")
    best = json.loads(files[-1].read_text(encoding="utf-8"))
    if not best.get("code") or not math.isfinite(float(best.get("objective", float("inf")))):
        raise RuntimeError("EoH 没有得到有效最优算子")
    code = EOH_CODE + "\n\n# EoH evolved machine selector\n" + best["code"]
    return code, {"engine": "EoH", "objective": float(best["objective"]), "generations": len(files)}


def run_funsearch_engine(
    settings: dict,
    data_root: Path,
    work_root: Path,
    progress: ProgressCallback,
    stop_event,
    mock: bool = False,
) -> tuple[str, dict]:
    if not mock:
        validate_llm_settings(settings)
    backend_root = data_root.parent
    funsearch_root = backend_root / "funsearch"
    if str(funsearch_root) not in sys.path:
        sys.path.insert(0, str(funsearch_root))
    os.environ["FJSP_DATA_DIR"] = str(data_root)
    from fjsp.run import run_evolution

    engine_settings = {
        **settings,
        "max_samples": max(1, int(settings.get("n_iter", 10))),
        "num_islands": max(2, int(settings.get("pop_size", 4))),
        "samples_per_prompt": max(1, int(settings.get("n_per_method", 2))),
    }
    score, code = run_evolution(
        engine_settings,
        mock=mock,
        progress_callback=lambda current, total, best: progress(current, total, _finite(best), "FunSearch 程序采样"),
        stop_event=stop_event,
    )
    if not code.strip():
        raise RuntimeError("FunSearch 未生成有效程序")
    return code, {"engine": "FunSearch", "score": _finite(score), "samples": engine_settings["max_samples"]}


class _MockOurLLM:
    def __init__(self):
        self.index = 0

    def get_response(self, prompt_text: str):
        from our.tools.heuristic_templates import get_builtin_heuristic_codes
        if "improvement memo" in prompt_text.lower():
            return "Bottleneck: machine congestion. Change: add load-aware completion. Risk: preserve feasibility."
        codes = get_builtin_heuristic_codes()
        code = codes[self.index % len(codes)]["code"]
        self.index += 1
        return code


def run_our_engine(
    settings: dict,
    data_root: Path,
    work_root: Path,
    progress: ProgressCallback,
    stop_event,
    mock: bool = False,
) -> tuple[str, dict]:
    if not mock:
        validate_llm_settings(settings)
    os.environ["FJSP_DATA_DIR"] = str(data_root)
    from our import agent as agent_module
    import our.tools.sample_manager as sample_manager
    if mock:
        agent_module._LLM_INTERFACE = _MockOurLLM()
    else:
        agent_module._LLM_INTERFACE = None
        agent_module.validate_llm_config()

    sample_manager.init_sample_dirs(clear_current=True)
    sample_manager.set_retrieve_library("all")
    controller = agent_module.EvoCtrlAgent()
    iterations = max(1, int(settings.get("n_iter", 10)))
    controller.global_budget = iterations + 1
    generator = agent_module.agent_Generator()
    checker = agent_module.agent_Checker()
    evaluator = agent_module.agent_Evaluator()
    reviser = agent_module.agent_Reviser()
    describer = agent_module.agent_Describer()
    questioner = agent_module.agent_Questioner()
    info = None
    best_code, best_score = "", float("inf")
    completed_steps = 0
    candidates_per_action = max(1, int(settings.get("n_per_method", 2)))

    for step in range(1, iterations + 1):
        if stop_event.is_set():
            break
        action = controller.next(info)
        if action == "Finish":
            break
        completed_steps = step
        try:
            if action.startswith("Gen("):
                gen_type = action.split("(", 1)[1].split(")", 1)[0]
                candidates = []
                for _ in range(candidates_per_action):
                    if stop_event.is_set():
                        break
                    code, prompt_text = generator.generate_code(gen_type, controller.last_question_advice)
                    candidate = _evaluate_our_candidate(
                        agent_module, action, code, prompt_text, checker, evaluator, describer
                    )
                    candidates.append(candidate)
                    sample_manager.add_sample(
                        candidate.code,
                        candidate.score if math.isfinite(candidate.score) else float("inf"),
                        candidate.to_sample_information(),
                    )
                if not candidates:
                    break
                info = min(candidates, key=lambda item: (not item.is_success, item.score))
            elif action == "Revise":
                code, prompt_text = reviser.revise_code(info)
                info = _evaluate_our_candidate(agent_module, action, code, prompt_text, checker, evaluator, describer)
            else:
                advice, prompt_text = questioner.question_code(info, sample_manager.summarize_top_samples(3))
                info = agent_module.EvolutionInfo(action=action, prompt=prompt_text, question=advice)
        except Exception as exc:
            info = agent_module.EvolutionInfo(action=action, error_type=type(exc).__name__, error=str(exc))

        if info and not info.question:
            if not action.startswith("Gen("):
                sample_manager.add_sample(
                    info.code, info.score if math.isfinite(info.score) else float("inf"), info.to_sample_information()
                )
            if info.is_success and info.score < best_score:
                best_code, best_score = info.code, info.score
        progress(step, iterations, _finite(best_score), f"Our 多智能体迭代：{action}")

    if not best_code:
        sample_manager.set_retrieve_library("current")
        sample = sample_manager.get_best_valid_sample()
        best_code = sample["code"] if sample else ""
        best_score = sample["score"] if sample else float("inf")
    if not best_code:
        raise RuntimeError("Our 多智能体迭代未生成有效求解器")
    return best_code, {
        "engine": "Our multi-agent",
        "score": _finite(best_score),
        "iterations": completed_steps,
        "candidates_per_action": candidates_per_action,
    }


def _evaluate_our_candidate(agent_module, action, code, prompt_text, checker, evaluator, describer):
    check_report = checker.check_code(code)
    if not check_report.ok:
        return agent_module.EvolutionInfo(
            action=action, code=code, prompt=prompt_text, check_report=check_report,
            error_type=check_report.error_type, error=check_report.message,
        )
    evaluation_report = evaluator.evaluate_code(code)
    if not evaluation_report.ok:
        return agent_module.EvolutionInfo(
            action=action, code=code, prompt=prompt_text, check_report=check_report,
            evaluation_report=evaluation_report, error_type=evaluation_report.error_type or "evaluation_failed",
            error=evaluation_report.message,
        )
    description = describer.describe_code(
        code, prompt_text, evaluation_report.score, float("inf"), action, evaluation_report
    )
    return agent_module.EvolutionInfo(
        action=action, code=code, prompt=prompt_text, score=evaluation_report.score,
        description=description, check_report=check_report, evaluation_report=evaluation_report,
    )


def _finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None
