export interface AuditLogItem {
  id: string;
  timestamp: Date;
  timestampLabel: string;
  propId: number;
  entityType: string;
  entityTypeLabel: string;
  entityId: string;
  action: string;
  actionLabel: string;
  summary: string;
  changedBy: string;
  diff: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  hasDetail: boolean;
}

export interface AuditLogViewModel {
  items: AuditLogItem[];
  total: number;
  page: number;
  perPage: number;
  pages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
