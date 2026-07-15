export interface Settings {
  pop_size: number;
  n_per_method: number;
  n_iter: number;
  llm_api_endpoint: string;
  llm_api_key: string;
  llm_model: string;
  llm_use_local: boolean;
  llm_local_url: string;
  llm_debug_mode: boolean;
  llm_max_workers: number;
}

export type PromptAgentName = "generator" | "reviser" | "questioner" | "describer";

export interface PromptAgent {
  title: string;
  description: string;
  instructions: Record<string, string>;
}

export type Prompts = Record<PromptAgentName, PromptAgent>;

export type JobStatus = "idle" | "running" | "completed" | "error" | "stopped";

export interface HistoryPoint {
  iteration: number;
  best_o: number | null;
  best_m: number | null;
  best_fitness: number | null;
  timestamp: string;
}

export interface Individual {
  id?: string;
  description?: string;
  code?: string;
  objective?: number | null;
  partner?: string | null;
}

export interface BaseTaskStatus {
  job_type: string;
  status: JobStatus;
  message: string;
  phase: string;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  progress_percent: number;
}

export interface EvolutionStatus extends BaseTaskStatus {
  current_iter: number;
  total_iter: number;
  best_fitness: number | null;
  history: HistoryPoint[];
  best_operation: Individual | null;
  best_machine: Individual | null;
}

export interface FolderSummary {
  name: string;
  csv_file: string;
  instance_count: number;
  valid_count: number;
  avg_gap: number | null;
}

export interface ExperimentStatus extends BaseTaskStatus {
  current_folder_index: number;
  total_folders: number;
  current_folder_name: string;
  current_instance: number;
  total_instances: number;
  completed_folders: string[];
  folder_summaries: FolderSummary[];
  folder_progress_percent: number;
  target_folders: string[];
}

export interface TasksOverview {
  active_job: "evolution" | "experiment" | null;
  evolution: EvolutionStatus;
  experiment: ExperimentStatus;
  experiment_ready: boolean;
  experiment_ready_message: string;
}

export interface ResultFile {
  name: string;
  size: number;
  modified: string | number;
}

export type MethodName = "eoh" | "funsearch" | "our";

export interface DatasetInfo {
  name: string;
  instance_count: number;
}

export interface DatasetSummary {
  dataset: string;
  instance_count: number;
  valid_count: number;
  avg_gap: number | null;
  avg_runtime_seconds: number | null;
}

export interface RunSummary {
  run_id: string;
  method: MethodName;
  created_at: string;
  datasets: DatasetSummary[];
  overall_avg_gap: number | null;
  overall_avg_runtime_seconds: number | null;
}

export interface MethodStatus {
  method: MethodName;
  status: JobStatus;
  action: "evolution" | "test" | null;
  message: string;
  error: string | null;
  progress_percent: number;
  current_dataset: string;
  current_instance: number;
  total_instances: number;
  completed_instances: number;
  evolution_iteration: number;
  total_evolution_iterations: number;
  best_fitness: number | null;
  evolution_history: MethodHistoryPoint[];
  generated_ready: boolean;
  started_at: string | null;
  finished_at: string | null;
  summary: RunSummary | null;
}

export interface MethodHistoryPoint {
  iteration: number;
  best_fitness: number | null;
  timestamp: string;
}

export interface MethodsOverview {
  methods: Record<MethodName, MethodStatus>;
  datasets: DatasetInfo[];
}

export interface ComparisonData {
  methods: Partial<Record<MethodName, RunSummary>>;
  runs: RunSummary[];
  compare_file: string;
}

export interface ExperimentCsvRow {
  测试数据名称?: string;
  makespan?: string;
  "(makespan-最优)/最优"?: string;
}

export interface ExperimentCsvData {
  name: string;
  file: string;
  rows: ExperimentCsvRow[];
}
