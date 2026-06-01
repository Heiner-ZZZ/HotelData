export interface RoomsPropertyOptionDto {
  prop_id: number;
  label: string;
}

export interface RoomsOptionsResponseDto {
  property_options: RoomsPropertyOptionDto[];
  selected_prop_id: number | null;
}

export interface RoomTypeDto {
  room_type_id: string;
  name: string;
  description: string;
  capacity_label: string;
  max_adults: number | null;
  max_children: number | null;
  base_capacity: number | null;
  is_active: boolean;
}

export interface RoomsSnapshotResponseDto {
  property: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
  };
  room_types: RoomTypeDto[];
  summary: {
    total_room_types: number;
    active_room_types: number;
    inactive_room_types: number;
  };
}

export interface CreateRoomTypeRequestDto {
  prop_id: number;
  name: string;
  description: string;
  max_adults: number;
  max_children: number;
  base_capacity: number;
  is_active: boolean;
}
