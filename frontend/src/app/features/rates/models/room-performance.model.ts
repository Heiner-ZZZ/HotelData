/** Row of the tactical R1.2 room performance dashboard (day × hotel × type × currency × channel). */
export interface RoomPerformanceRow {
  date: string;
  propId: number;
  hotelLabel: string;
  roomTypeId: string;
  roomTypeLabel: string;
  currency: string;
  bookingSource: string;
  roomsSold: number;
  roomNights: number;
  revenue: number;
  cancelledRooms: number;
  availableRooms: number;
  blockedRooms: number;
  totalRooms: number;
  publishedRate: number | null;
  rateVariance: number | null;
}

/** View model for GET /api/management/rates/analytics/room-performance — R1.2 dashboard. */
export interface RoomPerformanceDashboard {
  available: boolean;
  source: string;
  dateFrom: string;
  dateTo: string;
  propId: number | null;
  summary: {
    adr: number;
    revpar: number;
    occupancy: number;
    revenue: number;
    roomNights: number;
    roomsSold: number;
    cancelledRooms: number;
    capacityNights: number;
    rangeDays: number;
    hasRevenue: boolean;
    hasInventory: boolean;
    byRoomType: {
      roomTypeId: string;
      roomTypeLabel: string;
      roomNights: number;
      revenue: number;
      cancelledRooms: number;
      adr: number;
    }[];
    byChannel: {
      channel: string;
      label: string;
      roomNights: number;
      revenue: number;
      adr: number;
    }[];
    byHotel: {
      propId: number;
      hotelLabel: string;
      roomNights: number;
      revenue: number;
      adr: number;
    }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: RoomPerformanceRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
  message?: string;
}
