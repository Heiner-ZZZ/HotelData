export interface HotelDetailDto {
  prop_id: number;
  hotel_label: string;
  country_display_name: string;
  prop_starrating: number | null;
  review_label: string;
  avg_price_label: string;
  reservations: number;
  clicks: number;
  events: number;
  promotions: number;
  conversion_rate: number;
  click_rate: number;
  source_collection: string;
  top_destinations: Array<{
    srch_destination_id: number;
    destination_label: string;
    events: number;
    avg_price_label: string;
  }>;
  top_visitor_countries: Array<{
    visitor_location_country_id: number;
    country_label: string;
    events: number;
    reservations: number;
  }>;
  top_sites: Array<{
    site_id: number;
    site_label: string;
    events: number;
    clicks: number;
    reservations: number;
  }>;
  hotel_rates: Array<{
    date: string;
    rate_plan_id: string;
    rate_amount_label: string;
    min_stay_nights: number | null;
  }>;
  hotel_rooms?: Array<{
    hotel_room_id: string;
    room_number?: string;
    room_label: string;
    room_type_id: string;
    floor?: string;
    is_active: boolean;
  }>;
  room_types: Array<{
    room_type_id: string;
    name: string;
    base_capacity: number | null;
    max_adults: number | null;
    max_children: number | null;
    is_active: boolean;
    description?: string;
    features?: string[];
    image_url?: string;
  }>;
  hotel_policies: {
    check_in_time?: string | null;
    check_out_time?: string | null;
    pet_policy?: string | null;
    children_policy?: string | null;
    cancellation_policy?: string | null;
  } | null;
  hotel_images: Array<{
    image_url: string;
  }>;
  hotel_content: {
    description?: string | null;
    highlights?: string | null;
    amenities_text?: string | null;
    facilities?: {
      meeting_rooms?: number;
      fiber_optic?: string;
      concierge_24h?: boolean;
      gym?: boolean;
      pool?: boolean;
      parking?: boolean;
      ev_charging?: boolean;
      restaurant?: boolean;
      business_center?: boolean;
    };
    latitude?: number;
    longitude?: number;
  } | null;
  review_count: number;
  reviews: Array<{
    review_id?: string;
    reviewer_name?: string;
    review_score?: number;
    review_text?: string;
    created_at?: string;
  }>;
}

export interface SimilarHotelDto {
  prop_id: number;
  hotel_label: string;
  prop_starrating: number | null;
  review_label: string;
  country_display_name: string;
  similarity_score: number;
  reason: string;
  image_url: string;
}

export interface SimilarHotelsResponseDto {
  items: SimilarHotelDto[];
}
