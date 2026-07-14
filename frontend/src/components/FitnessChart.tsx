import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryPoint } from "../types";

interface Props {
  history: HistoryPoint[];
}

export default function FitnessChart({ history }: Props) {
  const data = history.map((h) => ({
    iteration: h.iteration,
    全局最优: h.best_fitness,
    工序最优: h.best_o,
    机器最优: h.best_m,
  }));

  if (data.length === 0) {
    return (
      <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 40 }}>
        暂无迭代数据，启动实验后将在此展示收敛曲线
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
        <XAxis
          dataKey="iteration"
          stroke="#8b949e"
          label={{ value: "迭代轮次", position: "insideBottom", offset: -2, fill: "#8b949e" }}
        />
        <YAxis stroke="#8b949e" label={{ value: "Objective", angle: -90, position: "insideLeft", fill: "#8b949e" }} />
        <Tooltip
          contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f", borderRadius: 6 }}
          labelStyle={{ color: "#e6edf3" }}
        />
        <Legend />
        <Line type="monotone" dataKey="全局最优" stroke="#22c55e" dot={false} strokeWidth={2} connectNulls />
        <Line type="monotone" dataKey="工序最优" stroke="#3b82f6" dot={false} strokeWidth={1.5} connectNulls />
        <Line type="monotone" dataKey="机器最优" stroke="#a855f7" dot={false} strokeWidth={1.5} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
