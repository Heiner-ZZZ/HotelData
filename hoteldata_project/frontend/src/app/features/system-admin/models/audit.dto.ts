export interface EtlExecutionDto {
  execution_id: string;
  executed_at: string;
  status: string;
}

export interface SearchLogDto {
  query: string;
  destination: string;
  country: string;
  searched_at: string;
}

export interface AuditActivityDto {
  etl_executions: EtlExecutionDto[];
  search_logs: SearchLogDto[];
}
