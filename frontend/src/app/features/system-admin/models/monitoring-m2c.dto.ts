/** DTOs del pipeline MongoDB → ClickHouse (contrato /etl-status/m2c/*).
 *  KEEP IN SYNC con server/src/app/features/etl_status_m2c/routes.py.
 */

export interface M2cTableStatusDto {
  name: string;
  exists: boolean;
}

export interface M2cClickhouseStatusDto {
  available: boolean;
  database: string;
  tables: M2cTableStatusDto[];
  message: string;
  technical_detail?: string;
}

export interface M2cScheduleDto {
  id?: string;
  pipeline: string;
  schedule_cron: string;
  enabled: boolean;
  configured: boolean;
  updated_at: string;
  updated_by: string;
}

export interface M2cSectionDto {
  label: string;
  complete: boolean;
}

export interface M2cProgressDto {
  exists: boolean;
  path: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  section: string;
  percent: number;
  elapsed_ms: number;
  message: string;
  detail: Record<string, unknown>;
  updated_at: string;
  sections: Record<string, M2cSectionDto>;
  is_running: boolean;
  clickhouse_database: string;
  tables: string[];
  stale?: boolean;
  stale_after_minutes?: number;
}

export interface M2cExecutionDto {
  exists: boolean;
  path: string;
  payload: Record<string, unknown>;
}

export interface M2cConsolidatedDto {
  services: {
    clickhouse: M2cClickhouseStatusDto;
  };
  schedule: M2cScheduleDto;
  progress: M2cProgressDto;
  execution: M2cExecutionDto;
}

export interface M2cActionResponseDto {
  ok: boolean;
  pid?: number | null;
  display_message: string;
  summary_output: string;
  schedule?: M2cScheduleDto;
}

export interface M2cScheduleUpdateDto {
  schedule_cron: string;
  enabled: boolean;
}
