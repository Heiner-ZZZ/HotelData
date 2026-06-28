export interface RoomsDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    review_score_label: string;
    manual_override?: boolean;
    profile_badge?: string;
  };
  performance: {
    avg_price_label: string;
    source_collection: string;
  };
  /** Feature item from the API: either a string (legacy) or an object with label & unit_price. */
  room_types: Array<{
    room_type_id: string;
    name: string;
    description: string;
    capacity_label: string;
    is_active: boolean;
    room_number?: string;
    floor?: string;
    features?: string[] | Array<{ label: string; unit_price: number }>;
    base_rate?: number;
  }>;
  hotel_rooms?: Array<{
    hotel_room_id: string;
    room_type_id: string;
    room_type_name?: string;
    room_label: string;
    is_active: boolean;
    room_number?: string;
    floor?: string;
  }>;
  room_type_count: number;
  hotel_room_count?: number;
}

export interface RoomsOptionsDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
}

export interface RoomCreateDto {
  room_type_id?: string;
  prop_id: number;
  name: string;
  description: string;
  max_adults: number;
  max_children: number;
  base_capacity: number;
  base_rate?: number;
  is_active: boolean;
  room_number?: string;
  floor?: string;
}
