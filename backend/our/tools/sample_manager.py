import json
import math
import os
import re
import shutil
import time
from typing import Any
from typing import Optional
from typing import Union


_FJSP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_ROOT = os.path.join(_FJSP_DIR, "sample")
ALL_SAMPLE_ROOT = os.path.join(SAMPLE_ROOT, "all")
CURRENT_SAMPLE_ROOT = os.path.join(SAMPLE_ROOT, "current")

SAMPLE_ID_RE = re.compile(r"^sample_\d{8}_\d{6}(?:_\d+)?$")
RETRIEVE_LIBRARY = "current"  # 可选: "all" 或 "current"


def set_retrieve_library(library: str) -> None:
    library = library.strip().lower()
    if library not in ("all", "current"):
        raise ValueError("library 只能是 'all' 或 'current'")
    global RETRIEVE_LIBRARY
    RETRIEVE_LIBRARY = library


def get_library_root() -> str:
    if RETRIEVE_LIBRARY == "all":
        return ALL_SAMPLE_ROOT
    if RETRIEVE_LIBRARY == "current":
        return CURRENT_SAMPLE_ROOT
    raise ValueError("library 只能是 'all' 或 'current'")


def init_sample_dirs(clear_current: bool = True) -> None:
    os.makedirs(ALL_SAMPLE_ROOT, exist_ok=True)
    if clear_current and os.path.isdir(CURRENT_SAMPLE_ROOT):
        shutil.rmtree(CURRENT_SAMPLE_ROOT)
    os.makedirs(CURRENT_SAMPLE_ROOT, exist_ok=True)


def add_sample(
    code: str,
    score: Union[int, float],
    information: Any,
) -> str:
    if not isinstance(code, str):
        raise TypeError("code 必须是 str")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError("score 必须是 int 或 float")

    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    sample_id = f"sample_{stamp}".strip()
    if not SAMPLE_ID_RE.match(sample_id):
        raise ValueError(f"非法 sample_id: {sample_id}")

    while os.path.exists(os.path.join(ALL_SAMPLE_ROOT, sample_id)) or os.path.exists(
        os.path.join(CURRENT_SAMPLE_ROOT, sample_id)
    ):
        if re.match(r".*_\d+$", sample_id):
            base, idx = sample_id.rsplit("_", 1)
            sample_id = f"{base}_{int(idx) + 1}"
        else:
            sample_id = f"{sample_id}_1"

    for root in (ALL_SAMPLE_ROOT, CURRENT_SAMPLE_ROOT):
        sample_dir = os.path.join(root, sample_id)
        os.makedirs(sample_dir, exist_ok=True)
        with open(os.path.join(sample_dir, "code.txt"), "w", encoding="utf-8") as f:
            f.write(code.rstrip() + "\n")
        with open(os.path.join(sample_dir, "score.txt"), "w", encoding="utf-8") as f:
            f.write(str(float(score)))
        with open(os.path.join(sample_dir, "information.json"), "w", encoding="utf-8") as f:
            payload = dict(information or {})
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            payload.setdefault("created_at", created_at)
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return sample_id


def get_sample(sample_id: str) -> dict[str, Any]:
    sample_dir = os.path.join(get_library_root(), sample_id)
    if not os.path.isdir(sample_dir):
        raise FileNotFoundError(f"样本不存在: {sample_id} ({os.path.basename(get_library_root())})")
    with open(os.path.join(sample_dir, "code.txt"), "r", encoding="utf-8") as f:
        code = f.read()
    with open(os.path.join(sample_dir, "score.txt"), "r", encoding="utf-8") as f:
        score = float(f.read())
    with open(os.path.join(sample_dir, "information.json"), "r", encoding="utf-8") as f:
        information = json.load(f)
    return {
        "sample_id": sample_id,
        "sample_dir": sample_dir,
        "score": score,
        "information": information,
        "code": code,
    }


def get_top_samples(
    top_k: Optional[int] = 20,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    only_valid: bool = False,
) -> list[dict[str, Any]]:
    root = get_library_root()
    if not os.path.isdir(root):
        return []
    samples: list[dict[str, Any]] = []
    for sample_id in sorted(os.listdir(root)):
        if not SAMPLE_ID_RE.match(sample_id):
            continue
        sample = get_sample(sample_id)
        score = sample["score"]
        information = sample.get("information", {})
        if only_valid and information.get("is_valid") is not True:
            continue
        if min_score is not None and score < min_score:
            continue
        if max_score is not None and score > max_score:
            continue
        samples.append(sample)

    samples.sort(key=lambda item: (_score_sort_key(item["score"]), item["sample_id"]))
    if top_k is None:
        return samples
    return samples[: max(0, top_k)]


def get_best_sample() -> Optional[dict[str, Any]]:
    top = get_top_samples(top_k=1)
    if not top:
        return None
    return top[0]


def get_best_valid_sample() -> Optional[dict[str, Any]]:
    top = get_top_samples(top_k=1, only_valid=True)
    if not top:
        return None
    return top[0]


def get_best_score() -> float:
    best_sample = get_best_valid_sample()
    if best_sample is None:
        return float("inf")
    return best_sample["score"]


def summarize_top_samples(top_k: int = 3) -> str:
    """Return compact lessons from the best valid samples for prompt reuse."""
    samples = get_top_samples(top_k=top_k, only_valid=True)
    if not samples:
        return "No valid historical samples are available yet."

    lines = []
    for idx, sample in enumerate(samples, start=1):
        info = sample.get("information", {})
        score = sample.get("score", float("inf"))
        action = info.get("action", "unknown")
        description = info.get("description") or "No description recorded."
        if len(description) > 240:
            description = description[:237].rstrip() + "..."
        lines.append(f"{idx}. score={score:.6f}, action={action}, lesson={description}")
    return "\n".join(lines)


def get_elite_code_context(max_chars: int = 7000) -> str:
    """Return the current best valid code as a compact parent for mutation prompts."""
    sample = get_best_valid_sample()
    if sample is None:
        return ""
    code = str(sample.get("code", "")).strip()
    if len(code) <= max_chars:
        return code
    return code[:max_chars].rstrip() + "\n# ... truncated elite code ..."


def summarize_best_instance_gaps(top_k: int = 5) -> str:
    """Summarize worst per-instance gaps for the current best valid sample."""
    sample = get_best_valid_sample()
    if sample is None:
        return "No valid elite sample is available yet."

    info = sample.get("information", {})
    evaluation = info.get("evaluation") if isinstance(info, dict) else None
    instances = evaluation.get("instances", []) if isinstance(evaluation, dict) else []
    if not instances:
        return "The elite sample has no per-instance diagnostics recorded."

    worst = sorted(
        instances,
        key=lambda item: float(item.get("score", float("-inf"))),
        reverse=True,
    )[: max(0, top_k)]
    lines = [
        f"Elite score={sample.get('score', float('inf')):.6f}; worst instance gaps:"
    ]
    for item in worst:
        lines.append(
            " - "
            f"{item.get('instance', 'unknown')}: "
            f"score={float(item.get('score', float('inf'))):.2f}%, "
            f"makespan={item.get('makespan', '?')}, "
            f"optimal={item.get('optimal', '?')}"
        )
    return "\n".join(lines)


def summarize_recent_errors(top_k: int = 5) -> str:
    """Return compact recent non-valid failures so prompts avoid repeated mistakes."""
    root = get_library_root()
    if not os.path.isdir(root):
        return "No recent errors are recorded."

    samples: list[dict[str, Any]] = []
    for sample_id in sorted(os.listdir(root), reverse=True):
        if not SAMPLE_ID_RE.match(sample_id):
            continue
        sample = get_sample(sample_id)
        info = sample.get("information", {})
        if info.get("is_valid") is True:
            continue
        error_type = info.get("error_type")
        if not error_type:
            continue
        if error_type == "llm_generation_failed" or _looks_like_transport_error(str(info.get("error", ""))):
            continue
        samples.append(sample)
        if len(samples) >= top_k:
            break

    if not samples:
        return "No recent errors are recorded."

    lines = []
    for sample in samples:
        info = sample.get("information", {})
        message = " ".join(str(info.get("error", "")).split())
        if len(message) > 160:
            message = message[:157].rstrip() + "..."
        lines.append(f"- {info.get('action', 'unknown')}: {info.get('error_type', 'error')} - {message}")
    return "\n".join(lines)


def _score_sort_key(score: float) -> float:
    if isinstance(score, (int, float)) and math.isfinite(float(score)):
        return float(score)
    return float("inf")


def _looks_like_transport_error(message: str) -> bool:
    lower = message.lower()
    markers = (
        "httpsconnectionpool",
        "sslerror",
        "proxyerror",
        "remote end closed connection",
        "max retries exceeded",
        "unable to connect to proxy",
    )
    return any(marker in lower for marker in markers)
