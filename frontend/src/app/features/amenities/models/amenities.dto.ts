export interface AmenitiesDto {
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
  amenities: {
    active_amenities: string[];
    catalog: {
      category: string;
      items: {
        label: string;
        active: boolean;
        unit_price?: number;
      }[];
    }[];
  };
  content_page?: {
    description?: string;
    highlights?: string;
  };
  images?: {
    image_url: string;
    title: string;
  }[];
  facilities?: string[];
  room_types?: {
    room_type_id: string;
    name: string;
    max_adults: number;
    max_children: number;
    base_capacity: number;
    is_active: boolean;
    capacity_label: string;
  }[];
  room_amenities?: Record<string, {
    active_amenities: string[];
    amenities_text: string;
  }>;
  special_requests?: {
    label: string;
    unit_price: number;
    chargeable: boolean;
    pet_related: boolean;
    late_arrival: boolean;
  }[];
}

export interface SpecialRequestsSaveDto {
  prop_id: number;
  special_requests: { label: string; unit_price: number; flags: string[] }[];
}

export interface AmenitiesOptionsDto {
  properties: {
    prop_id: number;
    display_name: string;
  }[];
  catalog?: {
    category: string;
    items: {
      label: string;
      active: boolean;
    }[];
  }[];
  active_amenities?: string[];
}

export interface AmenitiesSaveDto {
  prop_id: number;
  active_amenities: string[];
  amenities_text: string;
  amenity_prices?: Record<string, number>;
  room_type_id?: string;
}
