export interface AuditLogItemDto {
  timestamp: string;
  prop_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  summary: string;
  changed_by: string;
  diff?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface AuditLogResponseDto {
  items: AuditLogItemDto[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AuditLogStatsDto {
  total_entries: number;
  today_entries: number;
  by_entity: { entity_type: string; count: number; last_action: string }[];
}

export interface AuditLogFiltersDto {
  entity_types: string[];
  actions: string[];
}
