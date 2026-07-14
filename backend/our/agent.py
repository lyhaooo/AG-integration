import math
import os
import re
import sys
import time
import traceback
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from our.prompt import prompt
from our.tools.checker import fjsp_correctness_checker
from our.tools.evaluate import evaluate_with_report
from our.tools.getdata import get_data
import our.tools.sample_manager as SM
from llm.api_general import InterfaceAPI
from llm.api_local_llm import InterfaceLocalLLM


@dataclass
class CheckReport:
    ok: bool
    error_type: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationReport:
    score: float
    dataset: str
    valid_instances: int = 0
    failed_instances: list[dict[str, Any]] = field(default_factory=list)
    instances: list[dict[str, Any]] = field(default_factory=list)
    error_type: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.valid_instances > 0 and math.isfinite(self.score)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvolutionInfo:
    action: str
    code: str = ""
    prompt: str = ""
    score: float = float("inf")
    description: str = ""
    check_report: CheckReport | None = None
    evaluation_report: EvaluationReport | None = None
    error_type: str = ""
    error: str = ""
    question: str = ""
    sample_id: str = ""

    @property
    def is_success(self) -> bool:
        return (
            self.check_report is not None
            and self.check_report.ok
            and self.evaluation_report is not None
            and self.evaluation_report.ok
        )

    def to_sample_information(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "score": self.score,
            "is_valid": self.is_success,
            "error_type": self.error_type,
            "error": self.error,
            "description": self.description,
            "prompt": self.prompt,
            "evaluation": self.evaluation_report.to_dict() if self.evaluation_report else None,
            "check": self.check_report.to_dict() if self.check_report else None,
            "question": self.question,
        }


@dataclass
class LLMConfig:
    api_endpoint: str
    api_key: str
    model: str
    use_local: bool
    local_url: str
    debug_mode: bool


_LLM_INTERFACE = None


class LLMGenerationError(RuntimeError):
    """Raised when the LLM backend cannot produce usable code or advice."""


def _load_project_env() -> None:
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    if not os.path.isfile(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def print2file(b_code: str) -> None:
    output_path = os.getenv(
        "FJSP_GENERATED_OUTPUT",
        os.path.join(_PROJECT_ROOT, "results", "our_r", "current_generated.py"),
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write((b_code or "").rstrip() + "\n")


def clean_llm_text(raw_text: Any) -> str:
    if raw_text is None:
        return ""
    text = str(raw_text).strip()
    if not text:
        return ""
    text = re.sub(r"^\s*```(?:python)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


def _read_llm_config() -> LLMConfig:
    _load_project_env()
    settings = {}
    settings_path = os.path.join(_PROJECT_ROOT, "config", "settings.json")
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            import json
            settings = json.load(f)
    except (OSError, ValueError):
        pass
    return LLMConfig(
        api_endpoint=os.getenv("FJSP_LLM_API_ENDPOINT", str(settings.get("llm_api_endpoint", ""))).strip(),
        api_key=os.getenv("FJSP_LLM_API_KEY", str(settings.get("llm_api_key", ""))).strip(),
        model=os.getenv("FJSP_LLM_MODEL", str(settings.get("llm_model", "gpt-4.1-mini"))).strip(),
        use_local=_env_truthy("FJSP_LLM_USE_LOCAL", "1" if settings.get("llm_use_local") else "0"),
        local_url=os.getenv("FJSP_LLM_LOCAL_URL", str(settings.get("llm_local_url", ""))).strip(),
        debug_mode=_env_truthy("FJSP_LLM_DEBUG", "1" if settings.get("llm_debug_mode") else "0"),
    )


def validate_llm_config() -> None:
    cfg = _read_llm_config()
    if cfg.use_local:
        if not cfg.local_url:
            raise RuntimeError("LLM local mode is enabled, but FJSP_LLM_LOCAL_URL is empty.")
        return

    if not cfg.api_endpoint or not cfg.api_key:
        raise RuntimeError(
            "Missing LLM config. Set FJSP_LLM_API_ENDPOINT and FJSP_LLM_API_KEY, "
            "or set FJSP_LLM_USE_LOCAL=1 with FJSP_LLM_LOCAL_URL."
        )


def _get_llm_interface():
    global _LLM_INTERFACE
    if _LLM_INTERFACE is not None:
        return _LLM_INTERFACE

    cfg = _read_llm_config()
    validate_llm_config()
    if cfg.use_local:
        _LLM_INTERFACE = InterfaceLocalLLM(cfg.local_url)
        return _LLM_INTERFACE

    _LLM_INTERFACE = InterfaceAPI(cfg.api_endpoint, cfg.api_key, cfg.model, cfg.debug_mode)
    return _LLM_INTERFACE


def _get_llm_response(prompt_text: str) -> str:
    max_attempts = max(1, int(os.getenv("FJSP_LLM_MAX_RETRIES", "3")))
    sleep_seconds = max(0.0, float(os.getenv("FJSP_LLM_RETRY_SLEEP", "1.0")))
    last_error = "LLM returned an empty response."
    for attempt in range(1, max_attempts + 1):
        response = _get_llm_interface().get_response(prompt_text)
        if response is not None and str(response).strip():
            return clean_llm_text(response)
        last_error = f"LLM returned an empty response on attempt {attempt}/{max_attempts}."
        if attempt < max_attempts and sleep_seconds > 0:
            time.sleep(sleep_seconds)
    raise LLMGenerationError(last_error)


def _classify_solver_exception(exc: Exception, tb: str = "") -> str:
    message = str(exc).lower()
    data_shape_markers = (
        "not enough values to unpack",
        "too many values to unpack",
        "object is not subscriptable",
    )
    if any(marker in message for marker in data_shape_markers):
        return "data_shape_error"
    if "index out of range" in message and "schedule" in tb.lower():
        return "schedule_index_error"
    if "index out of range" in message:
        return "index_error"
    if isinstance(exc, TypeError) and "positional argument" in message:
        return "signature_error"
    return "runtime_error"


class EvoCtrlAgent:
    def __init__(self):
        self.iteration = 0
        self.global_budget = 60
        self.revise_budget = 5
        self.question_budget = 3
        self.question_cooldown = 0
        self.question_cooldown_steps = 3
        self.no_improve_streak = 0
        self.error_streak = 0
        self.last_k_scores: list[float] = []
        self.last_k_size = 6
        self.action_streak_by_type = {"M": 0, "O": 0, "G": 0}
        self.focus_order = ["O", "M", "G"]
        self.current_focus = "O"
        self.no_gain_rotate_threshold = 2
        self.stagnation_trigger = 4
        self.finish_stagnation = 20
        self.exploit_trigger = 2
        self.exploit_cooldown = 0
        self.exploit_cooldown_steps = 1
        self.last_action = None
        self.last_action_kind = None
        self.best_score = float("inf")
        self.last_question_advice = ""

    def _ingest_feedback(self, evo_info: EvolutionInfo | None) -> None:
        if self.question_cooldown > 0:
            self.question_cooldown -= 1
        if self.exploit_cooldown > 0:
            self.exploit_cooldown -= 1
        if evo_info is None:
            return

        if evo_info.error_type == "llm_generation_failed":
            return

        if self.last_action_kind in self.action_streak_by_type:
            self.action_streak_by_type[self.last_action_kind] += 1

        if evo_info.question:
            self.last_question_advice = evo_info.question
            return

        if evo_info.is_success:
            self.error_streak = 0
            score = evo_info.score
            self.last_k_scores.append(score)
            self.last_k_scores = self.last_k_scores[-self.last_k_size :]
            if score < self.best_score - 1e-9:
                self.best_score = score
                self.no_improve_streak = 0
                return
            self.no_improve_streak += 1
        else:
            self.error_streak += 1
            self.no_improve_streak += 1

        if self.no_improve_streak > 0 and self.no_improve_streak % self.no_gain_rotate_threshold == 0:
            self._rotate_focus()

    def _rotate_focus(self) -> None:
        idx = self.focus_order.index(self.current_focus)
        self.current_focus = self.focus_order[(idx + 1) % len(self.focus_order)]

    def _should_finish(self) -> bool:
        if self.iteration >= self.global_budget:
            return True
        if self.no_improve_streak >= self.finish_stagnation and self.question_budget <= 0:
            return True
        return False

    def _should_question(self) -> bool:
        if self.question_budget <= 0:
            return False
        if self.question_cooldown > 0:
            return False
        if self.no_improve_streak < self.stagnation_trigger:
            return False
        return all(v >= 1 for v in self.action_streak_by_type.values())

    def _should_exploit(self) -> bool:
        if self.exploit_cooldown > 0:
            return False
        if self.no_improve_streak < self.exploit_trigger:
            return False
        return math.isfinite(SM.get_best_score())

    def _should_revise(self, evo_info: EvolutionInfo | None) -> bool:
        if evo_info is None or evo_info.is_success or evo_info.question:
            return False
        if evo_info.error_type == "llm_generation_failed":
            return False
        if not evo_info.error_type:
            return False
        if self.revise_budget <= 0:
            return False
        if self.error_streak >= 3:
            return False
        return True

    def next(self, evo_info: EvolutionInfo | None) -> str:
        self._ingest_feedback(evo_info)
        self.iteration += 1

        if isinstance(evo_info, EvolutionInfo) and evo_info.question:
            action = "Gen(L)"
            self.last_action = action
            self.last_action_kind = "L"
            return action

        if self._should_finish():
            self.last_action = "Finish"
            self.last_action_kind = None
            return "Finish"

        if self._should_revise(evo_info):
            self.revise_budget -= 1
            self.last_action = "Revise"
            self.last_action_kind = None
            return "Revise"

        if self._should_question():
            self.question_budget -= 1
            self.question_cooldown = self.question_cooldown_steps
            self.last_action = "Questn"
            self.last_action_kind = None
            return "Questn"

        if self._should_exploit():
            self.exploit_cooldown = self.exploit_cooldown_steps
            action = "Gen(E)"
            self.last_action = action
            self.last_action_kind = "E"
            return action

        action = f"Gen({self.current_focus})"
        self.last_action = action
        self.last_action_kind = self.current_focus
        return action


class agent_Generator:
    def __init__(self):
        self.Prompt = prompt()
        self.generation_counts = {"M": 0, "O": 0, "G": 0, "L": 0}

    def generate_code(self, gen_type: str, advice: str = "") -> tuple[str, str]:
        self.generation_counts[gen_type] = self.generation_counts.get(gen_type, 0) + 1
        variant_index = self.generation_counts[gen_type]
        if gen_type == "M":
            prompt_text = self.Prompt.get_prompt_gen_M(variant_index)
        elif gen_type == "O":
            prompt_text = self.Prompt.get_prompt_gen_O(variant_index)
        elif gen_type == "G":
            prompt_text = self.Prompt.get_prompt_gen_G(variant_index)
        elif gen_type == "L":
            prompt_text = self.Prompt.get_prompt_gen_L(advice, variant_index)
        elif gen_type == "E":
            prompt_text = self.Prompt.get_prompt_gen_E(advice, variant_index)
        else:
            raise ValueError(f"Unknown generation type: {gen_type}")

        return _get_llm_response(prompt_text), prompt_text


class agent_Checker:
    def __init__(self):
        check_data_path = os.path.join(_PROJECT_ROOT, "Data", "Dauzere", "01a.fjs")
        self.n_jobs, self.n_machines, self.durations = get_data(check_data_path)

    def check_code(self, code: str) -> CheckReport:
        if not isinstance(code, str) or not code.strip():
            return CheckReport(False, "empty_code", "LLM returned empty code.")

        namespace: dict[str, Any] = {}
        try:
            exec(code, namespace)
        except SyntaxError as exc:
            return CheckReport(False, "syntax_error", str(exc), {"traceback": traceback.format_exc()})
        except Exception as exc:  # noqa: BLE001 - generated code may fail at import time
            return CheckReport(False, "runtime_error", str(exc), {"traceback": traceback.format_exc()})

        fjsp_solver = namespace.get("fjsp_solver")
        if not callable(fjsp_solver):
            return CheckReport(False, "missing_solver", "代码中无法找到可调用的 fjsp_solver() 函数。")

        try:
            schedule = fjsp_solver(self.n_jobs, self.n_machines, self.durations)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            return CheckReport(
                False,
                _classify_solver_exception(exc, tb),
                str(exc),
                {"traceback": tb},
            )

        check_result = fjsp_correctness_checker(schedule, self.n_jobs, self.n_machines, self.durations)
        if check_result is True:
            return CheckReport(True, details={"check_instance": "Dauzere/01a.fjs"})
        return CheckReport(False, "schedule_invalid", str(check_result), {"check_instance": "Dauzere/01a.fjs"})


class agent_Evaluator:
    def __init__(self, dataset: str = "Dauzere"):
        self.dataset = dataset

    def evaluate_code(self, code: str) -> EvaluationReport:
        namespace: dict[str, Any] = {}
        try:
            exec(code, namespace)
            fjsp_solver = namespace.get("fjsp_solver")
            if not callable(fjsp_solver):
                return EvaluationReport(
                    score=float("inf"),
                    dataset=self.dataset,
                    error_type="missing_solver",
                    message="代码中无法找到可调用的 fjsp_solver() 函数。",
                )
            raw_report = evaluate_with_report(fjsp_solver, dataset=self.dataset)
        except Exception as exc:  # noqa: BLE001
            return EvaluationReport(
                score=float("inf"),
                dataset=self.dataset,
                error_type="evaluation_failed",
                message=str(exc),
                failed_instances=[{"error": type(exc).__name__, "message": str(exc)}],
            )

        return EvaluationReport(
            score=float(raw_report["score"]),
            dataset=raw_report["dataset"],
            valid_instances=int(raw_report["valid_instances"]),
            failed_instances=list(raw_report["failed_instances"]),
            instances=list(raw_report["instances"]),
        )


class agent_Reviser:
    def __init__(self):
        self.Prompt = prompt()

    def revise_code(self, evo_info: EvolutionInfo) -> tuple[str, str]:
        error_type = evo_info.error_type or "runtime_error"
        error_message = evo_info.error or "unknown error"
        prompt_text = self.Prompt.get_prompt_revise(error_type, error_message, evo_info.code)
        return _get_llm_response(prompt_text), prompt_text


class agent_Describer:
    def describe_code(
        self,
        code: str,
        prompt_text: str,
        score: float,
        best_score: float,
        action: str = "",
        evaluation_report: EvaluationReport | None = None,
    ) -> str:
        if math.isfinite(best_score):
            delta = score - best_score
            trend = "improved" if delta < 0 else "did not improve"
            score_note = f"score={score:.6f}, previous_best={best_score:.6f}, trend={trend}"
        else:
            score_note = f"score={score:.6f}, first valid candidate"

        valid = evaluation_report.valid_instances if evaluation_report else 0
        failed = len(evaluation_report.failed_instances) if evaluation_report else 0
        return (
            f"{action or 'candidate'} produced a feasible solver; {score_note}. "
            f"Evaluation covered {valid} valid instances with {failed} failed instances. "
            "Store this candidate as a reusable heuristic reference."
        )


class agent_Questioner:
    def __init__(self):
        self.Prompt = prompt()

    def question_code(self, evo_info: EvolutionInfo | None, sample_summary: str) -> tuple[str, str]:
        evo_state = self._format_evo_state(evo_info)
        prompt_text = self.Prompt.get_prompt_question(evo_state, sample_summary)
        return _get_llm_response(prompt_text), prompt_text

    def _format_evo_state(self, evo_info: EvolutionInfo | None) -> str:
        if evo_info is None:
            return "No previous candidate has been evaluated."
        if evo_info.is_success:
            return (
                f"Last action={evo_info.action}, score={evo_info.score:.6f}, "
                f"description={evo_info.description}"
            )
        return (
            f"Last action={evo_info.action}, error_type={evo_info.error_type}, "
            f"error={evo_info.error}"
        )
