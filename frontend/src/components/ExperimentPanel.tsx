import { useEffect, useState } from "react";
import type { ExperimentCsvRow, ExperimentStatus } from "../types";
import { fetchExperimentCsv } from "../api";
import { ProgressBar, StatusHeader, TaskControls } from "./TaskCommon";

interface Props {
  status: ExperimentStatus;
  ready: boolean;
  readyMessage: string;
  loading: boolean;
  actionMsg: string;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onRestart: () => void;
}

export default function ExperimentPanel({
  status,
  ready,
  readyMessage,
  loading,
  actionMsg,
  onStart,
  onStop,
  onReset,
  onRestart,
}: Props) {
  const isRunning = status.status === "running";
  const [selectedDataset, setSelectedDataset] = useState("Barnes");
  const [csvPreview, setCsvPreview] = useState<{ rows: ExperimentCsvRow[] } | null>(null);

  const datasets = status.target_folders?.length
    ? status.target_folders
    : ["Barnes", "Brandimarte", "Dauzere", "edata", "rdata", "vdata"];

  useEffect(() => {
    fetchExperimentCsv(selectedDataset)
      .then((d) => setCsvPreview({ rows: d.rows.slice(0, 8) }))
      .catch(() => setCsvPreview(null));
  }, [selectedDataset, status.folder_summaries, status.status]);

  return (
    <div className="card task-card">
      <div className="task-card-top">
        <StatusHeader
          title="批量测试"
          subtitle="对应 src/experiment.py · 用最优算子测试 Barnes / Brandimarte / Dauzere / edata / rdata / vdata"
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
          startLabel="启动测试"
          disabledStart={!ready && !isRunning}
        />
      </div>

      {!ready && status.status === "idle" && (
        <div className="warn-banner">{readyMessage || "请先完成算子进化，生成最优算子文件"}</div>
      )}

      {actionMsg && <p className="action-msg">{actionMsg}</p>}

      <ProgressBar
        percent={status.progress_percent}
        label={`数据集 ${status.completed_folders.length} / ${status.total_folders} 已完成`}
        sublabel={
          status.current_folder_name
            ? `${status.current_folder_name}: ${status.current_instance}/${status.total_instances} · ${status.progress_percent}%`
            : `${status.progress_percent}%`
        }
      />

      {status.folder_summaries.length > 0 && (
        <div className="summary-grid">
          {status.folder_summaries.map((s) => (
            <div key={s.name} className="summary-chip">
              <span className="chip-name">{s.name}</span>
              <span className="chip-meta">
                {s.valid_count}/{s.instance_count} 有效
                {s.avg_gap != null && ` · 平均 gap ${s.avg_gap.toFixed(4)}`}
              </span>
            </div>
          ))}
        </div>
      )}

      {status.error && <p className="error-line">{status.error}</p>}

      <div className="dataset-preview">
        <div className="preview-toolbar">
          <h4 className="section-label">测试结果预览</h4>
          <select value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
            {datasets.map((d) => (
              <option key={d} value={d}>
                {d}.csv
              </option>
            ))}
          </select>
        </div>
        {csvPreview && csvPreview.rows.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>实例</th>
                  <th>makespan</th>
                  <th>相对 gap</th>
                </tr>
              </thead>
              <tbody>
                {csvPreview.rows.map((row, i) => (
                  <tr key={i}>
                    <td>{row["测试数据名称"]}</td>
                    <td>{row.makespan}</td>
                    <td>{row["(makespan-最优)/最优"]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {csvPreview.rows.length >= 8 && (
              <p className="table-note">仅显示前 8 行，完整数据请下载 CSV</p>
            )}
          </div>
        ) : (
          <p className="empty-note">暂无 {selectedDataset}.csv，请先运行批量测试</p>
        )}
      </div>
    </div>
  );
}
