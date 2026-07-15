import { useCallback, useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { downloadUrl, fetchComparison } from "../api";
import type { ComparisonData, MethodName } from "../types";

const LABELS: Record<MethodName, string> = { eoh: "EoH", funsearch: "FunSearch", our: "Our" };
const COLORS: Record<MethodName, string> = { eoh: "#3b82f6", funsearch: "#a855f7", our: "#22c55e" };
const METHODS: MethodName[] = ["eoh", "funsearch", "our"];
const CAPABILITIES = [
  {
    title: "调度算子自动生成",
    description: "主要由 Generator Agent 负责，以现有模板为基础，引导 LLM 自动生成高性能算子。",
  },
  {
    title: "调度算子自动调试",
    description: "主要由 Checker 和 Evaluator Agent 负责，对由 LLM 生成的算子进行检查、评估并修正。",
  },
  {
    title: "调度算子自动优化",
    description: "由 Reviser Agent 负责对无法正确运行或调度结果不合理的代码进行修正，同时迭代生成更高质量的代码。",
  },
  {
    title: "调度算子动态组合",
    description: "Generator Agent 会调用不同工具，对算子的不同部分进行扰动和组合；例如 gen_M 仅修改机器选择算子，gen_O 仅修改工序选择算子。",
  },
];

export default function ComparisonPanel() {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const refresh = useCallback(() => fetchComparison().then(setData).catch(() => setData(null)), []);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const datasets = useMemo(() => {
    const names = new Set<string>();
    Object.values(data?.methods ?? {}).forEach((summary) => summary?.datasets.forEach((item) => names.add(item.dataset)));
    return [...names];
  }, [data]);
  const activeDataset = selectedDataset && datasets.includes(selectedDataset)
    ? selectedDataset
    : datasets[0] ?? null;
  const chart = datasets.map((dataset) => {
    const row: Record<string, string | number> = { dataset };
    METHODS.forEach((method) => {
      const item = data?.methods[method]?.datasets.find((value) => value.dataset === dataset);
      if (item?.avg_gap != null) row[LABELS[method]] = item.avg_gap * 100;
    });
    return row;
  });

  return (
    <div className="run-center">
      <div className="card">
        <h3 className="card-title">多智能体调度算子生成算法功能性评价</h3>
        <p className="task-subtitle">通过不同 Agent 分工协作，覆盖算子自动生成、自动调试、自动优化与动态组合的完整流程。</p>
        <div className="capability-grid">
          {CAPABILITIES.map((capability, index) => (
            <div className="capability-item" key={capability.title}>
              <span className="capability-index">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h4>{capability.title}</h4>
                <p>{capability.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="comparison-title">
          <div>
            <h3 className="card-title">多智能体调度算子生成算法性能性评价</h3>
            <p className="task-subtitle">选择一个数据集，比较三种方法最新一次评测的平均 gap 和单实例平均耗时。</p>
          </div>
        </div>

        <div className="dataset-checkboxes" role="radiogroup" aria-label="选择要比较的数据集">
          {datasets.map((dataset) => (
            <label className={`dataset-checkbox ${activeDataset === dataset ? "selected" : ""}`} key={dataset}>
              <input
                type="radio"
                name="comparison-dataset"
                checked={activeDataset === dataset}
                onChange={() => setSelectedDataset(dataset)}
              />
              <span>{dataset}</span>
            </label>
          ))}
        </div>

        {datasets.length === 0 ? (
          <p className="empty-note">暂无实验结果，请先在运行中心至少完成一种方法的评测。</p>
        ) : activeDataset && (
          <div className="table-wrap comparison-matrix">
            <table>
              <thead>
                <tr>
                  <th rowSpan={2}>方法</th>
                  <th colSpan={2}>{activeDataset}</th>
                </tr>
                <tr>
                  <th>平均 gap</th>
                  <th>单实例平均耗时</th>
                </tr>
              </thead>
              <tbody>
                {METHODS.map((method) => (
                  <tr key={method}>
                    <td><span className="method-color" style={{ background: COLORS[method] }} />{LABELS[method]}</td>
                    {(() => {
                      const result = data?.methods[method]?.datasets.find((item) => item.dataset === activeDataset);
                      return <>
                        <td>{result?.avg_gap == null ? "—" : `${(result.avg_gap * 100).toFixed(4)}%`}</td>
                        <td>{result?.avg_runtime_seconds == null ? "—" : `${(result.avg_runtime_seconds * 1000).toFixed(3)} ms`}</td>
                      </>;
                    })()}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="table-note">页面每 5 秒刷新一次；“—”表示该方法尚未完成对应数据集的评测。</p>
      </div>

      <div className="card">
        <div className="comparison-title"><div><h3 className="card-title">各数据集平均 gap</h3><p className="task-subtitle">数值越低越好，三种方法均使用 backend/Data 中相同实例。</p></div><a className="btn btn-ghost" href={downloadUrl("compare.csv")} download style={{ textDecoration: "none" }}>下载 compare.csv</a></div>
        {chart.length === 0 ? <p className="empty-note">暂无可展示的评测数据。</p> : <ResponsiveContainer width="100%" height={340}>
          <BarChart data={chart} margin={{ top: 12, right: 12, left: 4, bottom: 26 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
            <XAxis dataKey="dataset" stroke="#8b949e" angle={-15} textAnchor="end" interval={0} height={60} />
            <YAxis stroke="#8b949e" unit="%" />
            <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} formatter={(value: number) => `${value.toFixed(3)}%`} />
            <Legend />
            {METHODS.map((method) => <Bar key={method} dataKey={LABELS[method]} fill={COLORS[method]} />)}
          </BarChart>
        </ResponsiveContainer>}
      </div>

      <div className="card">
        <h3 className="card-title">最新实验指标</h3>
        <div className="table-wrap">
          <table><thead><tr><th>方法</th><th>数据集</th><th>有效实例</th><th>平均 gap</th><th>单实例平均耗时</th></tr></thead>
            <tbody>{METHODS.flatMap((method) => data?.methods[method]?.datasets.map((item) => (
              <tr key={`${method}-${item.dataset}`}><td>{LABELS[method]}</td><td>{item.dataset}</td><td>{item.valid_count}/{item.instance_count}</td><td>{item.avg_gap == null ? "—" : `${(item.avg_gap * 100).toFixed(4)}%`}</td><td>{item.avg_runtime_seconds == null ? "—" : `${(item.avg_runtime_seconds * 1000).toFixed(3)} ms`}</td></tr>
            )) ?? [])}</tbody>
          </table>
        </div>
        <p className="table-note">共保存 {data?.runs.length ?? 0} 次历史测试；compare.csv 的每个测试列对应一次完整实验，average 列为同方法同数据集的历史平均。</p>
      </div>
    </div>
  );
}
