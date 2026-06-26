import type { RoomCreateDto, RoomsDto, RoomsOptionsDto } from '../models/rooms.dto';
import type { RoomFeatureItem, RoomPropertyOption, RoomsViewModel } from '../models/rooms.model';

function normalizeFeatures(features: unknown): RoomFeatureItem[] {
  if (!Array.isArray(features)) return [];
  return features.map((f) => {
    if (typeof f === 'string') return { label: f, unitPrice: 0 };
    return { label: String(f.label ?? ''), unitPrice: Number(f.unit_price ?? 0) };
  });
}

export function mapRoomsResponse(dto: RoomsDto): RoomsViewModel {
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    manualOverride: dto.hotel.manual_override ?? false,
    profileBadge: dto.hotel.profile_badge || (dto.hotel.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    totalRoomTypes: dto.room_type_count,
    totalHotelRooms: dto.hotel_room_count ?? dto.hotel_rooms?.length ?? 0,
    roomTypes: dto.room_types.map((room) => ({
      id: room.room_type_id,
      name: room.name,
      description: room.description || 'Sin descripción',
      capacityLabel: room.capacity_label,
      activeLabel: room.is_active ? 'Sí' : 'No',
      roomNumber: room.room_number || '',
      floor: room.floor || '',
      features: normalizeFeatures(room.features),
    })),
    hotelRooms: (dto.hotel_rooms ?? []).map((room) => ({
      id: room.hotel_room_id,
      roomTypeName: room.room_type_name || room.room_type_id,
      roomLabel: room.room_label,
      activeLabel: room.is_active ? 'Sí' : 'No',
      roomNumber: room.room_number || '',
      floor: room.floor || '',
      upcomingBookings: (room as any).upcoming_bookings,
      isOccupiedSoon: (room as any).is_occupied_soon ?? false,
      occupancyLabel: (room as any).occupancy_label || '',
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
  baseRate?: number;
  isActive: boolean;
  roomNumber?: string;
  floor?: string;
}): RoomCreateDto {
  return {
    prop_id: payload.propId,
    name: payload.name,
    description: payload.description,
    max_adults: payload.maxAdults,
    max_children: payload.maxChildren,
    base_capacity: payload.baseCapacity,
    base_rate: payload.baseRate,
    is_active: payload.isActive,
    room_number: payload.roomNumber || '',
    floor: payload.floor || '',
  };
}
