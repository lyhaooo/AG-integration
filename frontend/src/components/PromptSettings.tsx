import { useEffect, useState } from "react";
import type { PromptAgentName, Prompts } from "../types";
import { fetchPrompts, savePrompts } from "../api";

const AGENTS: PromptAgentName[] = ["generator", "reviser", "questioner", "describer"];
const FIELD_LABELS: Record<string, string> = {
  system_role: "智能体角色",
  task_description: "任务描述",
  global_strategy: "全局生成策略 Gen(G)",
  machine_strategy: "机器分配策略 Gen(M)",
  operation_strategy: "工序排序策略 Gen(O)",
  local_strategy: "建议驱动策略 Gen(L)",
  elite_strategy: "精英变异策略 Gen(E)",
  code_error_goal: "代码错误修订目标",
  schedule_error_goal: "调度错误修订目标",
  performance_goal: "性能修订目标",
  output_constraints: "输出约束",
  output_requirements: "输出要求",
};

export default function PromptSettings() {
  const [prompts, setPrompts] = useState<Prompts | null>(null);
  const [tab, setTab] = useState<PromptAgentName>("generator");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => { fetchPrompts().then(setPrompts).catch(() => setMessage("提示词加载失败")); }, []);
  const section = prompts?.[tab];

  const updateInstruction = (key: string, value: string) => {
    if (!prompts) return;
    setPrompts({
      ...prompts,
      [tab]: { ...prompts[tab], instructions: { ...prompts[tab].instructions, [key]: value } },
    });
  };

  const handleSave = async () => {
    if (!prompts) return;
    setSaving(true);
    setMessage("");
    try {
      setPrompts(await savePrompts(prompts));
      setMessage("四类智能体提示词已保存");
    } catch {
      setMessage("保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (!prompts || !section) return <div className="card">{message || "加载中..."}</div>;

  return (
    <div className="card">
      <h3 className="card-title">智能体提示词</h3>
      <p className="task-subtitle">Checker 与 Evaluator 使用确定性程序校验，不调用 LLM，因此不包含提示词。</p>
      <div className="tabs prompt-tabs">
        {AGENTS.map((agent) => (
          <button key={agent} className={`tab ${tab === agent ? "active" : ""}`} onClick={() => setTab(agent)}>
            {prompts[agent].title.split(" ")[0]}
          </button>
        ))}
      </div>
      <h4 className="section-label">{section.title}</h4>
      <p className="task-subtitle">{section.description}</p>
      {Object.entries(section.instructions).map(([key, value]) => (
        <div className="form-field" key={key} style={{ marginBottom: 14 }}>
          <label>{FIELD_LABELS[key] ?? key}</label>
          <textarea rows={key.includes("constraints") || key.includes("requirements") ? 5 : 4} value={value} onChange={(event) => updateInstruction(key, event.target.value)} style={{ width: "100%" }} />
        </div>
      ))}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? "保存中..." : "保存全部提示词"}</button>
        {message && <span style={{ color: message.includes("失败") ? "var(--danger)" : "var(--success)", fontSize: 13 }}>{message}</span>}
      </div>
    </div>
  );
}
