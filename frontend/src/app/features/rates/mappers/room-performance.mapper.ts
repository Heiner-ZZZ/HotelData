import type { RoomPerformanceDashboard, RoomPerformanceRow } from '../models/room-performance.model';
import type { RoomPerformanceDashboardDto, RoomPerformanceRowDto } from '../models/room-performance.dto';

function mapRow(dto: RoomPerformanceRowDto): RoomPerformanceRow {
  return {
    date: dto.date,
    propId: dto.prop_id,
    hotelLabel: dto.hotel_label,
    roomTypeId: dto.room_type_id,
    roomTypeLabel: dto.room_type_label,
    currency: dto.currency,
    bookingSource: dto.booking_source,
    roomsSold: dto.rooms_sold,
    roomNights: dto.room_nights,
    revenue: dto.revenue,
    cancelledRooms: dto.cancelled_rooms,
    availableRooms: dto.available_rooms,
    blockedRooms: dto.blocked_rooms,
    totalRooms: dto.total_rooms,
    publishedRate: dto.published_rate,
    rateVariance: dto.rate_variance,
  };
}

export function mapRoomPerformanceDashboard(dto: RoomPerformanceDashboardDto): RoomPerformanceDashboard {
  return {
    available: dto.available,
    source: dto.source,
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    propId: dto.prop_id,
    summary: {
      adr: dto.summary?.adr ?? 0,
      revpar: dto.summary?.revpar ?? 0,
      occupancy: dto.summary?.occupancy ?? 0,
      revenue: dto.summary?.revenue ?? 0,
      roomNights: dto.summary?.room_nights ?? 0,
      roomsSold: dto.summary?.rooms_sold ?? 0,
      cancelledRooms: dto.summary?.cancelled_rooms ?? 0,
      capacityNights: dto.summary?.capacity_nights ?? 0,
      rangeDays: dto.summary?.range_days ?? 1,
      hasRevenue: dto.summary?.has_revenue ?? false,
      hasInventory: dto.summary?.has_inventory ?? false,
      byRoomType: (dto.summary?.by_room_type ?? []).map(item => ({
        roomTypeId: item.room_type_id,
        roomTypeLabel: item.room_type_label,
        roomNights: item.room_nights,
        revenue: item.revenue,
        cancelledRooms: item.cancelled_rooms,
        adr: item.adr,
      })),
      byChannel: (dto.summary?.by_channel ?? []).map(item => ({
        channel: item.channel,
        label: item.label,
        roomNights: item.room_nights,
        revenue: item.revenue,
        adr: item.adr,
      })),
      byHotel: (dto.summary?.by_hotel ?? []).map(item => ({
        propId: item.prop_id,
        hotelLabel: item.hotel_label,
        roomNights: item.room_nights,
        revenue: item.revenue,
        adr: item.adr,
      })),
    },
    series: dto.series ?? { labels: [], datasets: [] },
    rows: (dto.rows ?? []).map(mapRow),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 20,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
    message: dto.message,
  };
}
