import type {
  RoomsOptionsResponseDto,
  RoomsSnapshotResponseDto,
  CreateRoomTypeRequestDto
} from '../models/rooms.dto';
import type { RoomsPageViewModel } from '../models/rooms.model';

export function mapRoomsResponse(
  options: RoomsOptionsResponseDto,
  snapshot: RoomsSnapshotResponseDto
): RoomsPageViewModel {
  return {
    property: {
      propId: snapshot.property.prop_id,
      displayName: snapshot.property.display_name,
      countryDisplayName: snapshot.property.country_display_name
    },
    options: options.property_options.map((item) => ({
      propId: item.prop_id,
      label: item.label
    })),
    selectedPropId: snapshot.property.prop_id,
    roomTypes: snapshot.room_types.map((item) => ({
      roomTypeId: item.room_type_id,
      name: item.name,
      description: item.description || 'Sin descripcion',
      capacityLabel: item.capacity_label,
      maxAdults: item.max_adults,
      maxChildren: item.max_children,
      baseCapacity: item.base_capacity,
      isActive: item.is_active
    })),
    summary: {
      totalRoomTypes: snapshot.summary.total_room_types,
      activeRoomTypes: snapshot.summary.active_room_types,
      inactiveRoomTypes: snapshot.summary.inactive_room_types
    }
  };
}

export function buildCreateRoomTypeRequest(
  propId: number,
  value: {
    name: string;
    description: string;
    maxAdults: number;
    maxChildren: number;
    baseCapacity: number;
    isActive: boolean;
  }
): CreateRoomTypeRequestDto {
  return {
    prop_id: propId,
    name: value.name.trim(),
    description: value.description.trim(),
    max_adults: value.maxAdults,
    max_children: value.maxChildren,
    base_capacity: value.baseCapacity,
    is_active: value.isActive
  };
}
