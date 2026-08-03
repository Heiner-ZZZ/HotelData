/** Fila del dashboard I1.1 de solicitudes de servicio. */
export interface ServiceRequestAnalyticsRow {
  id: string;
  bookingId: string;
  propId: number;
  roomLabel: string;
  requestType: string;
  requestTypeLabel: string;
  description: string;
  status: string;
  statusLabel: string;
  createdAt: string;
  resolvedAt: string | null;
}

/** View model de GET /api/stay/requests/analytics — I1.1 dashboard. */
export interface ServiceRequestsAnalytics {
  available: boolean;
  source: string;
  propId: number | null;
  summary: {
    total: number;
    pending: number;
    inProgress: number;
    completed: number;
    cancelled: number;
    avgResolutionMinutes: number | null;
    resolvedCount: number;
  };
  series: {
    labels: string[];
    keys: string[];
    datasets: { label: string; data: number[] }[];
    dailyLabels: string[];
    dailyStatuses: { label: string; status: string; data: number[] }[];
  };
  rows: ServiceRequestAnalyticsRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
