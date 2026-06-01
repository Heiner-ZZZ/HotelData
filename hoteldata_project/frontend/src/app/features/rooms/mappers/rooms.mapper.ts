import type { RoomCreateDto, RoomsDto, RoomsOptionsDto } from '../models/rooms.dto';
import type { RoomPropertyOption, RoomsViewModel } from '../models/rooms.model';

export function mapRoomsResponse(dto: RoomsDto): RoomsViewModel {
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    totalRoomTypes: dto.room_type_count,
    roomTypes: dto.room_types.map((room) => ({
      id: room.room_type_id,
      name: room.name,
      description: room.description || 'Sin descripción',
      capacityLabel: room.capacity_label,
      activeLabel: room.is_active ? 'Sí' : 'No'
    }))
  };
}

export function mapRoomsOptions(dto: RoomsOptionsDto): RoomPropertyOption[] {
  return dto.properties.map((item) => ({
    propId: item.prop_id,
    label: item.display_name || `Hotel ${item.prop_id}`
  }));
}

export function mapRoomCreatePayload(payload: {
  propId: number;
  name: string;
  description: string;
  maxAdults: number;
  maxChildren: number;
  baseCapacity: number;
  isActive: boolean;
}): RoomCreateDto {
  return {
    prop_id: payload.propId,
    name: payload.name,
    description: payload.description,
    max_adults: payload.maxAdults,
    max_children: payload.maxChildren,
    base_capacity: payload.baseCapacity,
    is_active: payload.isActive
  };
}
