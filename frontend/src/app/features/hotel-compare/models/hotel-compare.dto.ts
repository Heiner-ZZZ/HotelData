export interface HotelCompareDto {
  items: HotelCompareItemDto[];
}

export interface HotelCompareItemDto {
  prop_id: number;
  hotel_name: string;
  display_name: string;
  prop_starrating: number | null;
  prop_review_score: number | null;
  image_url: string | null;
  amenities_text: string;
  room_types: HotelCompareRoomTypeDto[];
  policies: Record<string, unknown>;
  destination_labels: string[];
  min_nightly_rate?: number;
  min_nightly_rate_label?: string;
  total_estimated?: number;
  total_estimated_label?: string;
}

export interface HotelCompareRoomTypeDto {
  room_type_id: string;
  name: string;
  max_adults: number;
  max_children: number;
  base_capacity: number;
  description?: string;
}
