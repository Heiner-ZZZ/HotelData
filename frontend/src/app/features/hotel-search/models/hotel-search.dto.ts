export interface HotelSearchDto {
  items: HotelSearchItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  filters: Record<string, unknown>;
  alternative_destinations?: AlternativeDestinationDto[];
}

export interface AlternativeDestinationDto {
  id: number;
  display_name: string;
}

export interface HotelSearchItemDto {
  prop_id: number;
  hotel_name: string;
  display_name: string;
  prop_starrating: number | null;
  prop_review_score: number | null;
  image_url: string | null;
  destination_labels: string[];
  matched_room_type: {
    room_type_id: string;
    name: string;
    max_adults: number;
    max_children: number;
    base_capacity: number;
  } | null;
  min_nightly_rate: number | null;
  min_nightly_rate_label: string | null;
  total_estimated: number | null;
  total_estimated_label: string | null;
  available_room_types_count: number;
}
