# MA4PGO Unified Backend

三种方法统一读取 `Data/` 下的六组 FJSP 数据，结果统一写入 `results/`。

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 app.py
```

前端构建完成后可直接访问 `http://127.0.0.1:8000`；前端开发模式仍可使用 `npm run dev`。

- `results/compare.csv`：所有历史实验的 gap 与单实例平均耗时对比。
- `results/eoh_r|fun_r|our_r/current_generated.py`：该方法当前算子。
- `results/*_r/history/<run_id>/`：每次运行的算子、六份逐实例 CSV 和汇总 JSON。

也可不启动网页，按阶段运行：`python3 run_method.py eoh|funsearch|our evolve|test`。先执行 `evolve` 调用对应的真实迭代引擎并生成算子，再执行 `test` 统一测试。Our 会运行 `our/agent.py` 中的多智能体流程，并依据保存的种群、候选数、迭代参数和提示词进行搜索；EoH/FunSearch 分别运行其原始种群进化、采样评估与岛屿更新流程。迭代前须在 `config/settings.json` 中填写真实 LLM 配置；配置缺失时会直接报告错误，不会生成模拟结果。
