import type { AuditActivityDto, EtlExecutionDto, SearchLogDto } from '../models/audit.dto';
import type { AuditViewModel, EtlExecutionItem, SearchLogItem } from '../models/audit.model';

function formatDate(value: string): string {
  if (!value) return 'N/D';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('es-EC', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function mapEtlExecution(item: EtlExecutionDto): EtlExecutionItem {
  return {
    executionId: item.execution_id,
    executedAtLabel: formatDate(item.executed_at),
    status: item.status,
  };
}

function mapSearchLog(item: SearchLogDto): SearchLogItem {
  return {
    query: item.query || 'Sin texto',
    destination: item.destination || 'Sin destino',
    country: item.country || 'Sin país',
    searchedAtLabel: formatDate(item.searched_at),
  };
}

export function mapAuditActivity(dto: AuditActivityDto): AuditViewModel {
  return {
    totalExecutions: dto.etl_executions.length,
    totalSearches: dto.search_logs.length,
    etlExecutions: dto.etl_executions.map(mapEtlExecution),
    searchLogs: dto.search_logs.map(mapSearchLog),
  };
}
