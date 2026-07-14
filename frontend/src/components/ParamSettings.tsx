import { useEffect, useState } from "react";
import type { Settings } from "../types";
import { fetchSettings, saveSettings } from "../api";

interface Props {
  onSaved?: () => void;
}

export default function ParamSettings({ onSaved }: Props) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchSettings().then(setSettings);
  }, []);

  const update = (key: keyof Settings, value: string | number | boolean) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage("");
    try {
      await saveSettings(settings);
      setMessage("参数已保存");
      onSaved?.();
    } catch {
      setMessage("保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (!settings) return <div className="card">加载中...</div>;

  return (
    <div className="card">
      <h3 className="card-title">实验参数</h3>
      <div className="form-grid">
        <div className="form-field">
          <label>种群大小 (POP_SIZE)</label>
          <input
            type="number"
            min={1}
            max={100}
            value={settings.pop_size}
            onChange={(e) => update("pop_size", Number(e.target.value))}
          />
        </div>
        <div className="form-field">
          <label>每方法生成数 (N_PER_METHOD)</label>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.n_per_method}
            onChange={(e) => update("n_per_method", Number(e.target.value))}
          />
        </div>
        <div className="form-field">
          <label>迭代次数 (N_ITER)</label>
          <input
            type="number"
            min={1}
            max={500}
            value={settings.n_iter}
            onChange={(e) => update("n_iter", Number(e.target.value))}
          />
        </div>
      </div>

      <h3 className="card-title" style={{ marginTop: 24 }}>LLM 配置</h3>
      <div className="form-grid">
        <div className="form-field">
          <label>API Endpoint</label>
          <input
            value={settings.llm_api_endpoint}
            onChange={(e) => update("llm_api_endpoint", e.target.value)}
          />
        </div>
        <div className="form-field">
          <label>API Key</label>
          <input
            type="password"
            value={settings.llm_api_key}
            onChange={(e) => update("llm_api_key", e.target.value)}
            placeholder="sk-..."
          />
        </div>
        <div className="form-field">
          <label>Model</label>
          <input
            value={settings.llm_model}
            onChange={(e) => update("llm_model", e.target.value)}
          />
        </div>
        <div className="form-field">
          <label>Max Workers</label>
          <input
            type="number"
            min={1}
            max={32}
            value={settings.llm_max_workers}
            onChange={(e) => update("llm_max_workers", Number(e.target.value))}
          />
        </div>
        <div className="form-field">
          <label>Local URL</label>
          <input
            value={settings.llm_local_url}
            onChange={(e) => update("llm_local_url", e.target.value)}
          />
        </div>
        <div className="form-field">
          <label>使用本地 LLM</label>
          <select
            value={settings.llm_use_local ? "1" : "0"}
            onChange={(e) => update("llm_use_local", e.target.value === "1")}
          >
            <option value="0">否</option>
            <option value="1">是</option>
          </select>
        </div>
        <div className="form-field">
          <label>Debug 模式</label>
          <select
            value={settings.llm_debug_mode ? "1" : "0"}
            onChange={(e) => update("llm_debug_mode", e.target.value === "1")}
          >
            <option value="0">否</option>
            <option value="1">是</option>
          </select>
        </div>
      </div>

      <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 12 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "保存参数"}
        </button>
        {message && <span style={{ color: "var(--success)", fontSize: 13 }}>{message}</span>}
      </div>
    </div>
  );
}
