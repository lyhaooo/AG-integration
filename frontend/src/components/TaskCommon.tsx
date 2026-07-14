import type { JobStatus } from "../types";

export const STATUS_LABEL: Record<JobStatus, string> = {
  idle: "空闲",
  running: "运行中",
  completed: "已完成",
  error: "出错",
  stopped: "已停止",
};

export const PHASE_LABEL: Record<string, string> = {
  init: "初始化",
  initial_population: "初始种群",
  initial_eval: "初始评测",
  evolution: "进化迭代",
  loading: "加载算子",
  testing: "实例测试",
};

interface TaskControlsProps {
  isRunning: boolean;
  loading: boolean;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onRestart: () => void;
  startLabel?: string;
  disabledStart?: boolean;
}

export function TaskControls({
  isRunning,
  loading,
  onStart,
  onStop,
  onReset,
  onRestart,
  startLabel = "启动",
  disabledStart = false,
}: TaskControlsProps) {
  return (
    <div className="task-controls">
      <button className="btn btn-primary" onClick={onStart} disabled={loading || isRunning || disabledStart}>
        {startLabel}
      </button>
      <button className="btn btn-danger" onClick={onStop} disabled={loading || !isRunning}>
        停止
      </button>
      <button className="btn btn-ghost" onClick={onReset} disabled={loading || isRunning}>
        重置
      </button>
      <button className="btn btn-ghost" onClick={onRestart} disabled={loading || isRunning}>
        重新开始
      </button>
    </div>
  );
}

interface ProgressBarProps {
  percent: number;
  label: string;
  sublabel?: string;
}

export function ProgressBar({ percent, label, sublabel }: ProgressBarProps) {
  return (
    <div className="progress-section">
      <div className="progress-header">
        <span>{label}</span>
        <span>{sublabel ?? `${percent}%`}</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
    </div>
  );
}

interface StatusHeaderProps {
  title: string;
  subtitle?: string;
  status: JobStatus;
  message?: string;
}

export function StatusHeader({ title, subtitle, status, message }: StatusHeaderProps) {
  return (
    <div className="task-header">
      <div>
        <h3 className="card-title">{title}</h3>
        {subtitle && <p className="task-subtitle">{subtitle}</p>}
        <div className="task-status-row">
          <span className={`status-badge status-${status}`}>{STATUS_LABEL[status]}</span>
          {message && <span className="task-message">{message}</span>}
        </div>
      </div>
    </div>
  );
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
