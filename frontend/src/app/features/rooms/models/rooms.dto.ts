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
  room_types: {
    room_type_id: string;
    name: string;
    description: string;
    capacity_label: string;
    is_active: boolean;
    room_number?: string;
    floor?: string;
    image_url?: string;
    features?: string[] | { label: string; unit_price: number }[];
    base_rate?: number;
    view?: string;
    smoking?: boolean;
    accessible?: boolean;
    is_roh?: boolean;
  }[];
  hotel_rooms?: {
    hotel_room_id: string;
    room_type_id: string;
    room_type_name?: string;
    room_label: string;
    is_active: boolean;
    room_number?: string;
    floor?: string;
    view?: string;
    smoking?: boolean;
    accessible?: boolean;
    is_roh?: boolean;
  }[];
  room_type_count: number;
  hotel_room_count?: number;
}

export interface RoomsOptionsDto {
  properties: {
    prop_id: number;
    display_name: string;
  }[];
}

export interface FeatureCatalogItemDto {
  label: string;
  category: string;
  icon: string;
  custom: boolean;
  source?: string;
}

export interface FeatureCatalogDto {
  features: {
    category: string;
    items: FeatureCatalogItemDto[];
  }[];
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
  image_url?: string;
  room_number?: string;
  floor?: string;
  view?: string;
  smoking?: boolean;
  accessible?: boolean;
  is_roh?: boolean;
}
