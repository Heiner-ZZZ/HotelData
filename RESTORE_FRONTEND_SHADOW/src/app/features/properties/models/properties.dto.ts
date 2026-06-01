export interface PropertyPerformanceDto {
  source_collection: string;
  searches: number;
  clicks: number;
  reservations: number;
  gross_revenue_label: string;
  avg_price_label: string;
  review_score_label: string;
  conversion_rate: number;
  click_rate: number;
}

export interface PropertyListItemDto {
  prop_id: number;
  display_name: string;
  country_display_name: string;
  prop_starrating: number | null;
  review_score_label: string;
  performance: PropertyPerformanceDto;
}

export interface PropertiesListResponseDto {
  items: PropertyListItemDto[];
  query: string;
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  start_index: number;
  end_index: number;
}

export interface PropertyDetailResponseDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    prop_starrating: number | null;
    review_score_label: string;
    prop_brand_bool?: boolean;
    prop_location_score1?: number | null;
    description?: string | null;
  };
  performance: PropertyPerformanceDto;
  master_hotel: {
    hotel_code?: string | null;
    hotel_name?: string | null;
    description?: string | null;
    rating?: number | null;
  };
}
