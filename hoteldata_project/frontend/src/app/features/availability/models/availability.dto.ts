export interface AvailabilityDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    review_score_label: string;
  };
  performance: {
    avg_price_label: string;
    source_collection: string;
  };
  room_types: Array<{
    room_type_id: string;
    name: string;
    capacity_label: string;
    is_active: boolean;
  }>;
  inventory_items: Array<{
    date: string;
    room_type_id: string;
    room_type_name: string;
    total_rooms: number;
    available_rooms: number;
    blocked_rooms: number;
    occupancy_label: string;
  }>;
  blackout_items: Array<{
    room_type_id: string;
    start_date: string;
    end_date: string;
    range_label: string;
    blocked_rooms: number;
    reason: string;
  }>;
}

export interface AvailabilitySaveInventoryDto {
  prop_id: number;
  room_type_id: string;
  date: string;
  total_rooms: number;
  available_rooms: number;
  blocked_rooms: number;
}

export interface AvailabilitySaveBlackoutDto {
  prop_id: number;
  room_type_id: string;
  start_date: string;
  end_date: string;
  blocked_rooms: number;
  reason: string;
}

export interface ManagementPropertiesDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
  room_types?: Array<{
    room_type_id: string;
    name: string;
    capacity_label: string;
    is_active: boolean;
  }>;
}
