export interface Ga03ConfigDto {
  task_number: string;
  target_records: number;
  pocketbase_collection: string;
  source_csv_exists: boolean;
  source_csv: string;
  source_csv_resolved: string;
}

export interface PocketbaseStatusDto {
  available: boolean;
  collection: string;
  count: number | null;
  target_records?: number;
  state: string;
  message: string;
  technical_detail?: string;
}

export interface MongodbStatusDto {
  available: boolean;
  database: string;
  fact_exists: boolean;
  fact_count: number | null;
  ga03_fact_count: number | null;
  message: string;
  technical_detail?: string;
}

export interface ArtifactInfoDto {
  exists: boolean;
  path: string;
}

export interface ArtifactsDto {
  jsonl: ArtifactInfoDto;
  parquet: ArtifactInfoDto;
}

export interface ServicesResponseDto {
  config: Ga03ConfigDto;
  pocketbase: PocketbaseStatusDto;
  mongodb: MongodbStatusDto;
  artifacts: ArtifactsDto;
}

export interface ReportFileDto {
  exists: boolean;
  path: string;
  payload: Record<string, unknown>;
}

export type ReportsResponseDto = Record<string, ReportFileDto>;

export interface PipelineProgressDto {
  exists: boolean;
  status: string;
  section: string;
  percent: number;
  elapsed_ms: number;
  message: string;
  sections: Record<string, { label: string; complete: boolean }>;
  is_running: boolean;
}

export interface PreparationProgressDto {
  exists: boolean;
  status: string;
  loaded_records: number;
  target_records: number;
  remaining_records: number;
  percent: number;
  message: string;
  is_running: boolean;
}

export interface Ga03ProgressResponseDto {
  preparation: PreparationProgressDto;
  pipeline: PipelineProgressDto;
}

export interface ActionResponseDto {
  ok: boolean;
  display_message: string;
  summary_output: string;
  pid?: number;
  deleted_count?: number;
}

export interface ExecutionStatusResponseDto {
  available: boolean;
  source: string;
  legacy?: boolean;
  summary?: {
    execution_id?: string;
    executed_at?: string;
    status?: string;
    valid_fact_records?: number;
    rejected_records?: number;
    source_rows?: number;
  };
  message?: string;
}
