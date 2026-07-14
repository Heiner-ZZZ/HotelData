import type { RoomStatusHistoryEntry } from '../../services/housekeeping-api.service';

export interface RoomHistoryViewModel {
  items: RoomStatusHistoryEntry[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface RoomHistoryDto {
  items: RoomStatusHistoryEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export function mapRoomHistoryResponse(dto: RoomHistoryDto): RoomHistoryViewModel {
  return {
    items: dto.items,
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasNext: dto.has_next,
    hasPrev: dto.has_prev,
  };
}
