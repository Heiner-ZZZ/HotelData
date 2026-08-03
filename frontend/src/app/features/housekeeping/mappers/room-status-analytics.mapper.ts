import type { RoomStatusAnalytics, RoomStatusAnalyticsRow } from '../models/room-status-analytics.model';
import type { RoomStatusAnalyticsDto, RoomStatusAnalyticsRowDto } from '../models/room-status-analytics.dto';

function mapRow(dto: RoomStatusAnalyticsRowDto): RoomStatusAnalyticsRow {
  return {
    id: dto.id,
    propId: dto.propId ?? dto.prop_id ?? 0,
    roomTypeId: dto.roomTypeId ?? dto.room_type_id ?? '',
    roomLabel: dto.roomLabel ?? dto.room_label ?? '',
    roomNumber: dto.roomNumber ?? dto.room_number ?? dto.room_label ?? '',
    hotelRoomId: dto.hotelRoomId ?? dto.hotel_room_id ?? '',
    status: dto.status,
    note: dto.note ?? '',
    floor: dto.floor ?? null,
    createdAt: dto.createdAt ?? dto.created_at ?? '',
    updatedAt: dto.updatedAt ?? dto.updated_at ?? null,
  };
}

export function mapRoomStatusAnalytics(dto: RoomStatusAnalyticsDto): RoomStatusAnalytics {
  return {
    available: dto.available,
    source: dto.source,
    propId: dto.prop_id,
    summary: {
      total: dto.summary?.total ?? 0,
      occupied: dto.summary?.occupied ?? 0,
      vacant: dto.summary?.vacant ?? 0,
      cleaning: dto.summary?.cleaning ?? 0,
      inspected: dto.summary?.inspected ?? 0,
      maintenance: dto.summary?.maintenance ?? 0,
      out_of_service: dto.summary?.out_of_service ?? 0,
      pending_dirty: dto.summary?.pending_dirty ?? 0,
      clean_ready: dto.summary?.clean_ready ?? 0,
      occupancy_rate: dto.summary?.occupancy_rate ?? 0,
    },
    distribution: (dto.distribution ?? []).map((x) => ({
      status: x.status,
      label: x.label,
      count: x.count,
      color: x.color,
    })),
    status_counts: dto.status_counts ?? {},
    status_labels: dto.status_labels ?? {},
    status_colors: dto.status_colors ?? {},
    rows: (dto.rows ?? []).map(mapRow),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 50,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
  };
}
