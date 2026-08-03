/** Fila del dashboard I1.1 de solicitudes de servicio. */
export interface ServiceRequestAnalyticsRowDto {
  _id: string;
  booking_id: string;
  prop_id: number;
  room_label: string;
  request_type: string;
  request_type_label: string;
  description: string;
  status: string;
  status_label: string;
  created_at: string;
  resolved_at: string | null;
}

/** Respuesta de GET /api/stay/requests/analytics — I1.1 dashboard. */
export interface ServiceRequestsAnalyticsDto {
  available: boolean;
  source: string;
  prop_id: number | null;
  summary: {
    total: number;
    pending: number;
    in_progress: number;
    completed: number;
    cancelled: number;
    avg_resolution_minutes: number | null;
    resolved_count: number;
  };
  series: {
    labels: string[];
    keys: string[];
    datasets: { label: string; data: number[] }[];
    daily_labels: string[];
    daily_statuses: { label: string; status: string; data: number[] }[];
  };
  rows: ServiceRequestAnalyticsRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
