# FJSP FunSearch

基于 FunSearch 框架、评测方案对齐 [MA4PGO](file:///Users/liyihao/Desktop/常用/项目/MA4PGO)：
在 **Dauzere** 实例集上进化合并算子 `get_operators()`（内含 `select_operation` 与 `select_machine`），
fitness 为各实例相对 gap `(makespan-最优)/最优` 的去极值平均（越小越好）；FunSearch 内部使用 **负 fitness** 作为 score。

## 数据

`data/` 已从 MA4PGO 复制，包含 Barnes、Brandimarte、Dauzere、Hurink/edata/rdata/vdata 及最优值 CSV。

## 配置

LLM 与 MA4PGO 相同，编辑 `fjsp/config/settings.json`：

| 字段 | 说明 |
|------|------|
| `llm_api_endpoint` | API 地址（如 `one.ocoolai.com`） |
| `llm_api_key` | API Key |
| `llm_model` | 模型名（如 `gpt-3.5-turbo`） |
| `llm_use_local` | 是否使用本地 OpenAI 兼容服务 |
| `llm_local_url` | 本地服务地址 |
| `llm_debug_mode` | 调试输出 |
| `llm_max_workers` | 并行请求线程数 |
| `max_samples` | FunSearch 采样轮次 |
| `num_islands` | 岛数量 |
| `samples_per_prompt` | 每轮 prompt 采样数 |

CLI 可临时覆盖 LLM 参数（与 MA4PGO 字段名一致），例如：

```bash
python -m fjsp.run --llm-api-endpoint one.ocoolai.com --llm-model gpt-3.5-turbo
```

## 运行

```bash
cd /path/to/funsearch-main
pip install -r requirements.txt

# 冒烟测试（无需 API）
python -m fjsp.run --mock --max-samples 2

# 正式进化（读取 fjsp/config/settings.json）
python -m fjsp.run --max-samples 100

# 六个 benchmark 批量评测并导出 MA4PGO 风格 CSV
python -m fjsp.experiment
```

## 输出

- `results/best_get_operators.py`：最优 `get_operators` 函数
- `results/best_operation_operator.py` / `best_machine_operator.py`：拆分后的双算子（experiment 生成）
- `results/*.csv`：与 MA4PGO experiment 相同格式的评测表
- `results/best_meta.json`：最优 score 元数据

## 目录说明

| 文件 | 说明 |
|------|------|
| `specification.txt` | FunSearch 问题规格（`@funsearch.run` / `@funsearch.evolve`） |
| `fjsp_eval.py` | FJSP 求解器与 MA4PGO 一致评测逻辑 |
| `get_instance.py` | `.fjs` 实例解析 |
| `sandbox.py` | 子进程沙箱执行生成代码 |
| `llm_client.py` | OpenAI 兼容 API / Mock LLM |
| `run.py` | FunSearch 进化主入口 |
| `experiment.py` | 六组 benchmark 批量测试 |
