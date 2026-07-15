import { useState } from "react";
import ParamSettings from "./components/ParamSettings";
import PromptSettings from "./components/PromptSettings";
import RunCenter from "./components/RunCenter";
import ComparisonPanel from "./components/ComparisonPanel";

type Page = "params" | "prompts" | "run" | "comparison";

const NAV: { id: Page; label: string }[] = [
  { id: "params", label: "参数设置" },
  { id: "prompts", label: "提示词设置" },
  { id: "run", label: "运行中心" },
  { id: "comparison", label: "方法比较" },
];

export default function App() {
  const [page, setPage] = useState<Page>("run");

  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-card)",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>基于多智能体协同演化的调度算子自动生成算法</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
           
          </p>
        </div>
        <nav style={{ display: "flex", gap: 4 }}>
          {NAV.map(({ id, label }) => (
            <button
              key={id}
              className={`tab ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
              style={{ borderBottom: page === id ? "2px solid var(--accent)" : "2px solid transparent" }}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 24px 48px" }}>
        {page === "params" && <ParamSettings />}
        {page === "prompts" && <PromptSettings />}
        {page === "run" && <RunCenter />}
        {page === "comparison" && <ComparisonPanel />}
      </main>
    </div>
  );
}
