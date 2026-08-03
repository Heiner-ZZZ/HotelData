/** Row of the tactical R1.2 room performance dashboard (day × hotel × type × currency × channel). */
export interface RoomPerformanceRowDto {
  date: string;
  prop_id: number;
  hotel_label: string;
  room_type_id: string;
  room_type_label: string;
  currency: string;
  booking_source: string;
  rooms_sold: number;
  room_nights: number;
  revenue: number;
  cancelled_rooms: number;
  available_rooms: number;
  blocked_rooms: number;
  total_rooms: number;
  published_rate: number | null;
  rate_variance: number | null;
}

/** Response from GET /api/management/rates/analytics/room-performance — R1.2 dashboard. */
export interface RoomPerformanceDashboardDto {
  available: boolean;
  source: string;
  date_from: string;
  date_to: string;
  prop_id: number | null;
  summary: {
    adr: number;
    revpar: number;
    occupancy: number;
    revenue: number;
    room_nights: number;
    rooms_sold: number;
    cancelled_rooms: number;
    capacity_nights: number;
    range_days: number;
    has_revenue: boolean;
    has_inventory: boolean;
    by_room_type: {
      room_type_id: string;
      room_type_label: string;
      room_nights: number;
      revenue: number;
      cancelled_rooms: number;
      adr: number;
    }[];
    by_channel: {
      channel: string;
      label: string;
      room_nights: number;
      revenue: number;
      adr: number;
    }[];
    by_hotel: {
      prop_id: number;
      hotel_label: string;
      room_nights: number;
      revenue: number;
      adr: number;
    }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: RoomPerformanceRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  message?: string;
}
