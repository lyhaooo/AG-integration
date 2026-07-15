import { useCallback, useEffect, useState } from "react";
import type { MethodName, MethodsOverview } from "../types";
import {
  downloadUrl,
  extractErrorMessage,
  fetchGeneratedCode,
  fetchMethodsStatus,
  evolveMethod,
  testMethod,
  stopMethod,
} from "../api";
import { ProgressBar, StatusHeader } from "./TaskCommon";
import MethodFitnessChart from "./MethodFitnessChart";
import AgentActivity from "./AgentActivity";

const METHODS: { id: MethodName; title: string }[] = [
  { id: "eoh", title: "EoH" },
  { id: "funsearch", title: "FunSearch" },
  { id: "our", title: "基于多智能体协同演化的调度算子自动生成算法" },
];

const RESULT_FILES = ["compare.csv", "eoh_r.zip", "fun_r.zip", "our_r.zip"];

export default function RunCenter() {
  const [overview, setOverview] = useState<MethodsOverview | null>(null);
  const [ourCode, setOurCode] = useState("");
  const [messages, setMessages] = useState<Partial<Record<MethodName, string>>>({});
  const [loading, setLoading] = useState<MethodName | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [status, code] = await Promise.all([
        fetchMethodsStatus(), fetchGeneratedCode("our"),
      ]);
      setOverview(status);
      setOurCode(code);
    } catch {
      setMessages({ our: "无法连接后端，请确认 8000 端口服务已启动" });
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const action = async (method: MethodName, kind: "evolution" | "test" | "stop") => {
    setLoading(method);
    try {
      const result = kind === "evolution"
        ? await evolveMethod(method)
        : kind === "test" ? await testMethod(method) : await stopMethod(method);
      setMessages((value) => ({ ...value, [method]: result.message }));
      await refresh();
    } catch (error) {
      setMessages((value) => ({ ...value, [method]: extractErrorMessage(error) }));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="run-center">
      <div className="pipeline-hint">
        <span className="pipeline-step">① 运行迭代实验生成算子</span><span className="pipeline-arrow">→</span>
        <span className="pipeline-step">② 用生成算子测试全部 {overview?.datasets.reduce((n, d) => n + d.instance_count, 0) ?? 169} 个实例</span>
        <span className="pipeline-arrow">→</span><span className="pipeline-step">③ compare.csv 自动追加测试列</span>
      </div>

      <div className="method-grid">
        {METHODS.map(({ id, title }) => {
          const status = overview?.methods[id];
          const running = status?.status === "running";
          const history = status?.evolution_history ?? [];
          return (
            <div className="card method-card" key={id}>
              <div className="task-card-top">
                <StatusHeader title={title} status={status?.status ?? "idle"} message={status?.message} />
                <div className="task-controls">
                  <button className="btn btn-primary" disabled={loading !== null || running} onClick={() => void action(id, "evolution")}>运行迭代实验</button>
                  <button className="btn btn-ghost" disabled={loading !== null || running || !status?.generated_ready} onClick={() => void action(id, "test")}>运行完整测试</button>
                  <button className="btn btn-danger" disabled={loading !== null || !running} onClick={() => void action(id, "stop")}>停止</button>
                </div>
              </div>
              <ProgressBar
                percent={status?.progress_percent ?? 0}
                label={status?.action === "evolution"
                  ? `迭代 ${status.evolution_iteration} / ${status.total_evolution_iterations}`
                  : `测试 ${status?.completed_instances ?? 0} / ${status?.total_instances ?? 0} 实例`}
                sublabel={status?.action === "test" ? status.current_dataset || undefined : undefined}
              />
              <p className={`generated-state ${status?.generated_ready ? "ready" : ""}`}>
                {status?.generated_ready ? "✓ 已生成 current_generated.py，可运行完整测试" : "尚无生成算子，请先运行迭代实验"}
              </p>
              {id === "our" && running && status?.action === "evolution" && (
                <AgentActivity
                  stage={status.activity_stage}
                  detail={status.activity_detail}
                  agent={status.active_agent}
                  events={status.activity_events ?? []}
                />
              )}
              {status?.action === "evolution" && status.best_fitness != null && (
                <p className="metric-line">当前最优 Fitness：<strong>{status.best_fitness.toFixed(6)}</strong></p>
              )}
              {(status?.action === "evolution" || history.length > 0) && (
                <div className="method-chart-wrap">
                  <div className="method-chart-title">
                    <h4 className="section-label">迭代收敛曲线</h4>
                    <span>{history.length} 个数据点</span>
                  </div>
                  <MethodFitnessChart history={history} />
                </div>
              )}
              {messages[id] && <p className="action-msg">{messages[id]}</p>}
              {status?.error && <p className="error-line">{status.error}</p>}
              {status?.summary && (
                <div className="summary-grid compact-summary">
                  <div className="summary-chip"><span className="chip-name">总体平均性能差距比(PGR)</span><span className="chip-meta">{((status.summary.overall_avg_gap ?? 0) * 100).toFixed(3)}%</span></div>
                  <div className="summary-chip"><span className="chip-name">单实例平均耗时</span><span className="chip-meta">{((status.summary.overall_avg_runtime_seconds ?? 0) * 1000).toFixed(3)} ms</span></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card">
        <h3 className="card-title">当前生成代码</h3>
        <p className="task-subtitle"></p>
        <pre className="code-block">{ourCode || "运行后将在此展示本次生成的最终算子"}</pre>
      </div>

      <div className="card">
        <h3 className="card-title">统一结果文件</h3>
        <ul className="file-list">
            {RESULT_FILES.map((filename) => (
              <li key={filename}>
                <div>{filename}</div>
                <a className="btn btn-ghost" href={downloadUrl(filename)} download style={{ textDecoration: "none" }}>下载</a>
              </li>
            ))}
          </ul>
      </div>
    </div>
  );
}
