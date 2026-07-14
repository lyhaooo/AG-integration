import type { EvolutionStatus } from "../types";
import FitnessChart from "./FitnessChart";
import { PHASE_LABEL, ProgressBar, StatusHeader, TaskControls } from "./TaskCommon";

interface Props {
  status: EvolutionStatus;
  loading: boolean;
  actionMsg: string;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onRestart: () => void;
}

export default function EvolutionPanel({
  status,
  loading,
  actionMsg,
  onStart,
  onStop,
  onReset,
  onRestart,
}: Props) {
  const isRunning = status.status === "running";
  const phaseLabel = PHASE_LABEL[status.phase] ?? status.phase;

  return (
    <div className="card task-card">
      <div className="task-card-top">
        <StatusHeader
          title="算子进化"
          subtitle="对应 src/run.py · 多智能体协同生成最优工序/机器选择算子"
          status={status.status}
          message={status.message}
        />
        <TaskControls
          isRunning={isRunning}
          loading={loading}
          onStart={onStart}
          onStop={onStop}
          onReset={onReset}
          onRestart={onRestart}
          startLabel="启动进化"
        />
      </div>

      {actionMsg && <p className="action-msg">{actionMsg}</p>}

      <ProgressBar
        percent={status.progress_percent}
        label={`迭代 ${status.current_iter} / ${status.total_iter}${phaseLabel ? ` · ${phaseLabel}` : ""}`}
      />

      {status.best_fitness != null && (
        <p className="metric-line">
          全局最优 Objective：<strong>{status.best_fitness.toFixed(6)}</strong>
        </p>
      )}

      {status.error && <p className="error-line">{status.error}</p>}

      <div className="chart-wrap">
        <h4 className="section-label">收敛曲线</h4>
        <FitnessChart history={status.history} />
      </div>
    </div>
  );
}
