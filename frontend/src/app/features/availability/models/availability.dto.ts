export interface AvailabilityDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    review_score_label: string;
  };
  performance: {
    avg_price_label: string;
    min_rate_label?: string;
    source_collection: string;
  };
  room_types: {
    room_type_id: string;
    name: string;
    capacity_label: string;
    is_active: boolean;
  }[];
  inventory_items: {
    date: string;
    room_type_id: string;
    room_type_name: string;
    total_rooms: number;
    available_rooms: number;
    blocked_rooms: number;
    occupancy_label: string;
    occupancy_pct?: number;
    /** La fecha tiene al menos una tarifa ABIERTA (is_closed != True).
     *  Sin ella la disponibilidad no es vendible en el search público. */
    has_rate?: boolean;
  }[];
  blackout_items: {
    blackout_id?: string;
    room_type_id: string;
    start_date: string;
    end_date: string;
    range_label: string;
    blocked_rooms: number;
    reason: string;
    room_numbers?: string[];
  }[];
  availability_blocks?: {
    block_id?: string;
    room_type_id: string;
    start_date: string;
    end_date: string;
    range_label: string;
    blocked_rooms: number;
    reason: string;
    room_numbers?: string[];
  }[];
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
  properties: {
    prop_id: number;
    display_name: string;
  }[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  room_types?: {
    room_type_id: string;
    name: string;
    capacity_label: string;
    is_active: boolean;
  }[];
}
