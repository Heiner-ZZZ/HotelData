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
  room_types: Array<{
    room_type_id: string;
    name: string;
    base_capacity: number | null;
    max_adults: number | null;
    max_children: number | null;
    is_active: boolean;
  }>;
  hotel_policies: {
    check_in_time?: string | null;
    check_out_time?: string | null;
    pet_policy?: string | null;
    children_policy?: string | null;
    cancellation_policy?: string | null;
  } | null;
}
