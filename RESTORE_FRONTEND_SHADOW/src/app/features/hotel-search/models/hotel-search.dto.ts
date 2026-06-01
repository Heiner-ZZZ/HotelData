export interface HotelSearchFiltersDto {
  destination: string;
  min_price: string;
  max_price: string;
  min_stars: string;
  promotion: string;
  adults: string;
  children: string;
  rooms: string;
}

export interface HotelSearchItemDto {
  prop_id: number;
  hotel_label: string;
  country_display_name: string;
  prop_starrating: number | null;
  review_label: string;
  has_promotion: boolean;
  avg_price_label: string;
  reservations: number;
  clicks: number;
  conversion_rate: number;
  destination_labels: string[];
}

export interface HotelSearchResponseDto {
  items: HotelSearchItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  source_collection: string;
  filters: HotelSearchFiltersDto;
  start_index: number;
  end_index: number;
}
