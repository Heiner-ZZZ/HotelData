/** Wire DTO (snake_case) de GET /api/housekeeping/room-status/analytics — O1.2. */
export interface RoomStatusAnalyticsRowDto {
  id: string;
  prop_id: number;
  room_type_id: string;
  room_label: string;
  room_number?: string;
  hotel_room_id: string;
  status: string;
  note?: string;
  floor?: string | null;
  created_at?: string;
  updated_at?: string | null;
  // Alias camelCase que ya emite _enrich_room_status (se normalizan en el mapper).
  roomLabel?: string;
  roomNumber?: string;
  roomTypeId?: string;
  propId?: number;
  hotelRoomId?: string;
  createdAt?: string;
  updatedAt?: string | null;
}

export interface RoomStatusAnalyticsDto {
  available: boolean;
  source: string;
  prop_id: number | null;
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
  rows: RoomStatusAnalyticsRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
