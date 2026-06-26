export interface DestinationDto {
  srch_destination_id: number;
  destination_display_name: string;
  destination_name: string;
  visible_name: string;
  country: string;
  city: string;
  description: string;
  latitude: number | null;
  longitude: number | null;
  destination_region_label: string;
  active: boolean;
}

export interface PaginatedDestinationsDto {
  items: DestinationDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface GeoDestinationDto {
  srch_destination_id: number;
  destination_display_name: string;
  visible_name: string;
  country: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
}

export interface GeoHotelDto {
  prop_id: number;
  hotel_name: string;
  display_name: string;
  stars: number | null;
  review_score: number | null;
  latitude: number | null;
  longitude: number | null;
  srch_destination_id: number | null;
  destination_display_name: string;
}
