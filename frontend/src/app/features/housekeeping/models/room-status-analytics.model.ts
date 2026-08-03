/** Fila de la matriz de estado de habitaciones (O1.2). */
export interface RoomStatusAnalyticsRow {
  id: string;
  propId: number;
  roomTypeId: string;
  roomLabel: string;
  roomNumber: string;
  hotelRoomId: string;
  status: string;
  note: string;
  floor?: string | null;
  createdAt: string;
  updatedAt: string | null;
}

/** View model de GET /api/housekeeping/room-status/analytics — O1.2 dashboard simple. */
export interface RoomStatusAnalytics {
  available: boolean;
  source: string;
  propId: number | null;
  summary: {
    total: number;
    occupied: number;
    vacant: number;
    cleaning: number;
    inspected: number;
    maintenance: number;
    out_of_service: number;
    pending_dirty: number;
    clean_ready: number;
    occupancy_rate: number;
  };
  distribution: { status: string; label: string; count: number; color: string }[];
  status_counts: Record<string, number>;
  status_labels: Record<string, string>;
  status_colors: Record<string, string>;
  rows: RoomStatusAnalyticsRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
