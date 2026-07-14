import { useState } from "react";
import type { EvolutionStatus, Individual } from "../types";
import { downloadUrl } from "../api";

interface Props {
  evolution: EvolutionStatus;
  bestCode: { operation?: string; machine?: string };
}

export default function BestCodePanel({ evolution, bestCode }: Props) {
  const [tab, setTab] = useState<"operation" | "machine">("operation");

  const currentCode = tab === "operation" ? bestCode.operation : bestCode.machine;
  const bestIndiv: Individual | null =
    tab === "operation" ? evolution.best_operation : evolution.best_machine;

  return (
    <div className="card">
      <h3 className="card-title">最优算子代码</h3>
      <p className="task-subtitle" style={{ marginTop: -8, marginBottom: 16 }}>
        由算子进化产出，供批量测试加载（best_operation_operator.py + best_machine_operator.py）
      </p>
      <div className="tabs">
        <button className={`tab ${tab === "operation" ? "active" : ""}`} onClick={() => setTab("operation")}>
          工序选择算子
        </button>
        <button className={`tab ${tab === "machine" ? "active" : ""}`} onClick={() => setTab("machine")}>
          机器选择算子
        </button>
      </div>
      {bestIndiv?.description && <p className="desc-line">{bestIndiv.description}</p>}
      {bestIndiv?.objective != null && (
        <p className="metric-line">
          Objective: {bestIndiv.objective}
          {bestIndiv.partner && ` · Partner: ${bestIndiv.partner}`}
        </p>
      )}
      <pre className="code-block">
        {currentCode || "暂无最优代码，请先运行算子进化"}
      </pre>
      <a
        className="btn btn-ghost"
        href={downloadUrl(tab === "operation" ? "best_operation_operator.py" : "best_machine_operator.py")}
        download
        style={{ textDecoration: "none", marginTop: 12, display: "inline-flex" }}
      >
        下载 {tab === "operation" ? "工序" : "机器"}算子
      </a>
    </div>
  );
}
