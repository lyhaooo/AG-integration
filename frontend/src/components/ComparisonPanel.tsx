import { useCallback, useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { downloadUrl, fetchComparison } from "../api";
import type { ComparisonData, MethodName } from "../types";

const LABELS: Record<MethodName, string> = { eoh: "EoH", funsearch: "FunSearch", our: "Our" };
const COLORS: Record<MethodName, string> = { eoh: "#3b82f6", funsearch: "#a855f7", our: "#22c55e" };

export default function ComparisonPanel() {
  const [data, setData] = useState<ComparisonData | null>(null);
  const refresh = useCallback(() => fetchComparison().then(setData).catch(() => setData(null)), []);
  useEffect(() => { void refresh(); }, [refresh]);

  const datasets = useMemo(() => {
    const names = new Set<string>();
    Object.values(data?.methods ?? {}).forEach((summary) => summary?.datasets.forEach((item) => names.add(item.dataset)));
    return [...names];
  }, [data]);
  const chart = datasets.map((dataset) => {
    const row: Record<string, string | number> = { dataset };
    (["eoh", "funsearch", "our"] as MethodName[]).forEach((method) => {
      const item = data?.methods[method]?.datasets.find((value) => value.dataset === dataset);
      if (item?.avg_gap != null) row[LABELS[method]] = item.avg_gap * 100;
    });
    return row;
  });

  if (!data || Object.keys(data.methods).length === 0) {
    return <div className="card"><h3 className="card-title">方法结果比较</h3><p className="empty-note">暂无实验结果，请先在运行中心至少运行一种方法。</p></div>;
  }

  return (
    <div className="run-center">
      <div className="card">
        <div className="comparison-title"><div><h3 className="card-title">各数据集平均 gap</h3><p className="task-subtitle">数值越低越好，三种方法均使用 backend/Data 中相同实例。</p></div><a className="btn btn-ghost" href={downloadUrl("compare.csv")} download style={{ textDecoration: "none" }}>下载 compare.csv</a></div>
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={chart} margin={{ top: 12, right: 12, left: 4, bottom: 26 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
            <XAxis dataKey="dataset" stroke="#8b949e" angle={-15} textAnchor="end" interval={0} height={60} />
            <YAxis stroke="#8b949e" unit="%" />
            <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} formatter={(value: number) => `${value.toFixed(3)}%`} />
            <Legend />
            {(["eoh", "funsearch", "our"] as MethodName[]).map((method) => <Bar key={method} dataKey={LABELS[method]} fill={COLORS[method]} />)}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="card-title">最新实验指标</h3>
        <div className="table-wrap">
          <table><thead><tr><th>方法</th><th>数据集</th><th>有效实例</th><th>平均 gap</th><th>单实例平均耗时</th></tr></thead>
            <tbody>{(["eoh", "funsearch", "our"] as MethodName[]).flatMap((method) => data.methods[method]?.datasets.map((item) => (
              <tr key={`${method}-${item.dataset}`}><td>{LABELS[method]}</td><td>{item.dataset}</td><td>{item.valid_count}/{item.instance_count}</td><td>{item.avg_gap == null ? "—" : `${(item.avg_gap * 100).toFixed(4)}%`}</td><td>{item.avg_runtime_seconds == null ? "—" : `${(item.avg_runtime_seconds * 1000).toFixed(3)} ms`}</td></tr>
            )) ?? [])}</tbody>
          </table>
        </div>
        <p className="table-note">共保存 {data.runs.length} 次历史测试；compare.csv 的每个测试列对应一次完整实验，average 列为同方法同数据集的历史平均。</p>
      </div>
    </div>
  );
}

