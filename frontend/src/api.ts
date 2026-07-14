import axios from "axios";
import type {
  ComparisonData,
  ExperimentCsvData,
  MethodName,
  MethodsOverview,
  Prompts,
  ResultFile,
  TasksOverview,
} from "./types";
import type { Settings } from "./types";

const api = axios.create({ baseURL: "/api" });

export async function fetchSettings(): Promise<Settings> {
  const { data } = await api.get<Settings>("/config/settings");
  return data;
}

export async function saveSettings(settings: Settings): Promise<Settings> {
  const { data } = await api.put<Settings>("/config/settings", settings);
  return data;
}

export async function fetchPrompts(): Promise<Prompts> {
  const { data } = await api.get<Prompts>("/config/prompts");
  return data;
}

export async function savePrompts(prompts: Prompts): Promise<Prompts> {
  const { data } = await api.put<Prompts>("/config/prompts", prompts);
  return data;
}

export async function fetchTasksStatus(): Promise<TasksOverview> {
  const { data } = await api.get<TasksOverview>("/tasks/status");
  return data;
}

export async function startEvolution(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/evolution/start");
  return data;
}

export async function stopEvolution(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/evolution/stop");
  return data;
}

export async function resetEvolution(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/evolution/reset");
  return data;
}

export async function restartEvolution(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/evolution/restart");
  return data;
}

export async function startExperiment(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/experiment/start");
  return data;
}

export async function stopExperiment(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/experiment/stop");
  return data;
}

export async function resetExperiment(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/experiment/reset");
  return data;
}

export async function restartExperiment(): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post("/tasks/experiment/restart");
  return data;
}

export async function fetchResultFiles(): Promise<ResultFile[]> {
  const { data } = await api.get<{ files: ResultFile[] }>("/results/files");
  return data.files;
}

export function downloadUrl(filename: string): string {
  return `/api/results/download/${encodeURIComponent(filename)}`;
}

export async function fetchBestCode() {
  const { data } = await api.get("/results/best-code");
  return data;
}

export async function fetchExperimentCsv(dataset: string): Promise<ExperimentCsvData> {
  const { data } = await api.get<ExperimentCsvData>(`/results/experiment/${dataset}`);
  return data;
}

export function extractErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    if (detail) return detail;
  }
  return "操作失败";
}

export async function fetchMethodsStatus(): Promise<MethodsOverview> {
  const { data } = await api.get<MethodsOverview>("/methods/status");
  return data;
}

export async function runMethod(method: MethodName): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post(`/methods/${method}/run`);
  return data;
}

export async function evolveMethod(method: MethodName): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post(`/methods/${method}/evolve`);
  return data;
}

export async function testMethod(method: MethodName): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post(`/methods/${method}/test`);
  return data;
}

export async function stopMethod(method: MethodName): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post(`/methods/${method}/stop`);
  return data;
}

export async function fetchComparison(): Promise<ComparisonData> {
  const { data } = await api.get<ComparisonData>("/results/comparison");
  return data;
}

export async function fetchGeneratedCode(method: MethodName): Promise<string> {
  const { data } = await api.get<{ code: string }>(`/results/generated/${method}`);
  return data.code;
}
