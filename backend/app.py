from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fjsp_platform.datasets import dataset_catalog
from fjsp_platform.results import METHOD_DIR, comparison_payload
from fjsp_platform.runner import ExperimentManager

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Data"
RESULTS_DIR = BASE_DIR / "results"
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
PROMPTS_FILE = CONFIG_DIR / "prompts.json"

DEFAULT_SETTINGS = {
    "pop_size": 4, "n_per_method": 2, "n_iter": 10,
    "llm_api_endpoint": "", "llm_api_key": "", "llm_model": "gpt-4.1-mini",
    "llm_use_local": False, "llm_local_url": "http://127.0.0.1:8080/v1",
    "llm_debug_mode": False, "llm_max_workers": 4,
}
DEFAULT_PROMPTS = {
    "generator": {
        "title": "Generator 代码生成智能体",
        "description": "对应 agent_Generator 与 prompt.get_prompt_gen_G/M/O/L/E。",
        "instructions": {
            "system_role": "You are an expert in operations research and Python.",
            "task_description": "Flexible Job Shop Scheduling Problem (FJSP): choose a feasible machine and start time for every operation of every job. The objective is to minimize makespan while preserving job precedence and machine capacity.",
            "global_strategy": "Improve the overall scheduling structure. You may change both machine assignment and operation sequencing, but keep the public solver interface and schedule format unchanged.",
            "machine_strategy": "Focus on machine assignment. Try ideas such as earliest available machine, shortest processing time, workload balancing, and avoiding future bottleneck machines.",
            "operation_strategy": "Focus on operation sequencing. Try ideas such as shortest operation first, largest remaining work first, bottleneck-first dispatching, and tie-break rules that reduce downstream waiting.",
            "local_strategy": "Apply the improvement advice as the main design goal. Make a focused strategy change rather than a cosmetic rewrite.",
            "elite_strategy": "Exploit the current elite solver as a parent. Keep the reliable fixed-slot scheduling structure, but mutate one or two priority rules to beat the elite average score. Do not rewrite from scratch.",
            "output_constraints": "Return only executable Python code implementing fjsp_solver(n_jobs, n_machines, durations). Use only the Python standard library and return a feasible fixed-slot schedule as list[list[tuple[int, int, int]]].",
        },
    },
    "reviser": {
        "title": "Reviser 代码修订智能体",
        "description": "对应 agent_Reviser 与 prompt.get_prompt_revise。",
        "instructions": {
            "system_role": "You are revising a generated FJSP solver.",
            "code_error_goal": "Fix code-level problems only: syntax, missing fjsp_solver, wrong function signature, imports, runtime exceptions, or invalid return type.",
            "schedule_error_goal": "Fix schedule feasibility while preserving the algorithm style: job precedence, machine overlap, eligible machines, durations, and nested-list schedule format.",
            "performance_goal": "Improve performance without sacrificing feasibility. Make a small, explainable adjustment to machine assignment, operation sequencing, or tie-break logic.",
            "output_constraints": "Keep exactly fjsp_solver(n_jobs, n_machines, durations), use only the Python standard library, and return executable Python code without markdown fences.",
        },
    },
    "questioner": {
        "title": "Questioner 策略提问智能体",
        "description": "对应 agent_Questioner 与 prompt.get_prompt_question。",
        "instructions": {
            "system_role": "You are helping design the next FJSP heuristic improvement.",
            "output_requirements": "Return only a concise improvement memo with: 1. one likely bottleneck in the current search, 2. one concrete strategy change to try next, 3. one risk to avoid. Do not write code.",
        },
    },
    "describer": {
        "title": "Describer 样本描述智能体",
        "description": "对应 agent_Describer 与 prompt.get_prompt_describe。",
        "instructions": {
            "system_role": "Summarize this FJSP solver candidate for future retrieval.",
            "output_requirements": "Return 2-4 short sentences covering the main scheduling idea, what changed, and likely risks.",
        },
    },
}


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return json.loads(json.dumps(default))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(json.dumps(default))


def _save_json(path: Path, value: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return value


class Settings(BaseModel):
    pop_size: int = 4
    n_per_method: int = 2
    n_iter: int = 10
    llm_api_endpoint: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_use_local: bool = False
    llm_local_url: str = "http://127.0.0.1:8080/v1"
    llm_debug_mode: bool = False
    llm_max_workers: int = 4


app = FastAPI(title="MA4PGO Unified API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
manager = ExperimentManager(DATA_DIR, RESULTS_DIR)


@app.get("/api/health")
def health():
    return {"ok": True, "datasets": dataset_catalog(DATA_DIR)}


@app.get("/api/config/settings")
def get_settings():
    return _load_json(SETTINGS_FILE, DEFAULT_SETTINGS)


@app.put("/api/config/settings")
def put_settings(settings: Settings):
    return _save_json(SETTINGS_FILE, settings.model_dump())


@app.get("/api/config/prompts")
def get_prompts():
    return _load_json(PROMPTS_FILE, DEFAULT_PROMPTS)


@app.put("/api/config/prompts")
def put_prompts(prompts: dict):
    required = ("generator", "reviser", "questioner", "describer")
    if not all(key in prompts and isinstance(prompts[key].get("instructions"), dict) for key in required):
        raise HTTPException(422, "提示词必须包含 Generator、Reviser、Questioner、Describer")
    return _save_json(PROMPTS_FILE, prompts)


@app.get("/api/methods/status")
def methods_status():
    return {"methods": manager.statuses(), "datasets": dataset_catalog(DATA_DIR)}


@app.post("/api/methods/{method}/run")
def run_method(method: str):
    try:
        return manager.start(method)
    except KeyError:
        raise HTTPException(404, "未知方法") from None


@app.post("/api/methods/{method}/evolve")
def evolve_method(method: str):
    try:
        return manager.start_evolution(method)
    except KeyError:
        raise HTTPException(404, "未知方法") from None


@app.post("/api/methods/{method}/test")
def test_method(method: str):
    try:
        return manager.start_test(method)
    except KeyError:
        raise HTTPException(404, "未知方法") from None


@app.post("/api/methods/{method}/stop")
def stop_method(method: str):
    try:
        return manager.stop(method)
    except KeyError:
        raise HTTPException(404, "未知方法") from None


@app.get("/api/results/comparison")
def comparison():
    return comparison_payload(RESULTS_DIR)


@app.get("/api/results/generated/{method}")
def generated_code(method: str):
    if method not in METHOD_DIR:
        raise HTTPException(404, "未知方法")
    path = RESULTS_DIR / METHOD_DIR[method] / "current_generated.py"
    return {"method": method, "code": path.read_text(encoding="utf-8") if path.exists() else ""}


@app.get("/api/results/files")
def result_files():
    files = []
    for path in sorted(RESULTS_DIR.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            stat = path.stat()
            files.append({"name": path.relative_to(RESULTS_DIR).as_posix(), "size": stat.st_size, "modified": int(stat.st_mtime)})
    return {"files": files}


@app.get("/api/results/download/{filename:path}")
def download(filename: str):
    zip_directories = {"eoh_r.zip": "eoh_r", "fun_r.zip": "fun_r", "our_r.zip": "our_r"}
    if filename in zip_directories:
        source = RESULTS_DIR / zip_directories[filename]
        if not source.is_dir():
            raise HTTPException(404, "结果目录不存在")
        temp = tempfile.NamedTemporaryFile(prefix=f"{source.name}-", suffix=".zip", delete=False)
        temp_path = Path(temp.name)
        temp.close()
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(source.rglob("*")):
                if item.is_file() and item.name != ".DS_Store":
                    archive.write(item, Path(source.name) / item.relative_to(source))
        return FileResponse(
            temp_path,
            filename=filename,
            media_type="application/zip",
            background=BackgroundTask(temp_path.unlink, missing_ok=True),
        )
    path = (RESULTS_DIR / filename).resolve()
    if RESULTS_DIR.resolve() not in path.parents and path != RESULTS_DIR.resolve():
        raise HTTPException(400, "无效路径")
    if not path.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(path, filename=path.name)


# 生产构建存在时由同一个服务提供页面；开发时仍可使用 Vite 的 5173 端口。
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
