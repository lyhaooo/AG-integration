import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MethodHistoryPoint } from "../types";

interface Props {
  history: MethodHistoryPoint[];
}

export default function MethodFitnessChart({ history }: Props) {
  const data = history.filter((point) => point.best_fitness != null);

  if (data.length === 0) {
    return <div className="method-chart-empty">等待首轮迭代结果…</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 8, right: 18, left: 4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" vertical={false} />
        <XAxis
          dataKey="iteration"
          stroke="#8b949e"
          tickLine={false}
          allowDecimals={false}
          label={{ value: "迭代轮次", position: "insideBottom", offset: -3, fill: "#8b949e" }}
        />
        <YAxis
          stroke="#8b949e"
          tickLine={false}
          width={68}
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => Number(value).toPrecision(4)}
        />
        <Tooltip
          formatter={(value: number) => [Number(value).toFixed(6), "当前最优 Fitness"]}
          labelFormatter={(iteration) => `第 ${iteration} 轮`}
          contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f", borderRadius: 6 }}
          labelStyle={{ color: "#e6edf3" }}
        />
        <Line
          type="monotone"
          dataKey="best_fitness"
          name="当前最优 Fitness"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={{ r: 2.5, fill: "#60a5fa", strokeWidth: 0 }}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
