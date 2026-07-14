# MA4PGO FJSP 统一实验平台

项目已将 EoH、FunSearch、Our 三种方法统一到同一套 FJSP 数据、求解器、结果协议和网页运行入口。

## 启动

```bash
cd frontend
npm install
npm run build

cd ../backend
python3 -m pip install -r requirements.txt
python3 app.py
```

打开 <http://127.0.0.1:8000>。开发前端时也可在 `frontend` 目录运行 `npm run dev`，访问 5173 端口。

## 目录约定

- `backend/Data/`：六组方法共用的 169 个 FJSP 实例及最优值 CSV。
- `backend/results/compare.csv`：每次完整实验为一个测试列，记录各方法/数据集的平均 gap、单实例平均耗时；`average` 为历史测试平均，文件末尾为跨数据集汇总。
- `backend/results/eoh_r/`、`fun_r/`、`our_r/`：当前生成算子和历史运行。
- 每个 `history/<run_id>/`：本次最终算子、六份逐实例 CSV、`summary.json`。

## 不使用网页运行

```bash
cd backend
python3 run_method.py eoh evolve
python3 run_method.py eoh test
python3 run_method.py funsearch evolve
python3 run_method.py funsearch test
python3 run_method.py our evolve
python3 run_method.py our test
```

每种方法都先用 `evolve` 调用真实迭代引擎并生成 `current_generated.py`，再用 `test` 完成六组统一基准测试。EoH 调用原始种群进化流程，FunSearch 调用采样、沙箱评估和岛屿更新流程，Our 调用 `our/agent.py` 中的多智能体控制器、生成器、检查器、评估器、修订器与提问器。Our 会使用网页保存的种群、候选数、迭代次数和 `our/prompt.py` 对应的提示词；EoH 与 FunSearch 的参数和生成代码不在网页展示。运行迭代前须在 `backend/config/settings.json` 填写真实 LLM 配置，未配置时任务会明确报错，不会退回伪造结果。

## 验证

```bash
cd backend
python3 -m unittest discover -s tests -v

cd ../frontend
npm run build
```
