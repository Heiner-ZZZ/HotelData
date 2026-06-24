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
  location: string;
  prop_starrating: number | null;
  review_score_label: string;
  performance: PropertyPerformanceDto;
  yield_score: number;
  status: string;
  sync_status: string;
  sync_latency_ms: number;
  unit_count: number;
  manual_override?: boolean;
  profile_badge?: string;
  operational?: {
    policies_configured: boolean;
    rooms_configured: boolean;
    rates_configured: boolean;
    inventory_configured: boolean;
    content_configured: boolean;
    images_configured: boolean;
    promotions_active: boolean;
    operational_score: number;
    counts: Record<string, number>;
  };
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
    hotel_name?: string | null;
    country_display_name: string;
    prop_starrating: number | null;
    review_score_label: string;
    prop_brand_bool?: boolean;
    prop_location_score1?: number | null;
    description?: string | null;
    manual_override?: boolean;
    name_source?: string;
    original_generated_name?: string | null;
    profile_badge?: string;
    operational?: {
      policies_configured: boolean;
      rooms_configured: boolean;
      rates_configured: boolean;
      inventory_configured: boolean;
      content_configured: boolean;
      images_configured: boolean;
      promotions_active: boolean;
      operational_score: number;
      counts: Record<string, number>;
    };
  };
  performance: PropertyPerformanceDto;
  master_hotel: {
    hotel_code?: string | null;
    hotel_name?: string | null;
    description?: string | null;
    rating?: number | null;
  };
}

export interface DashboardQuickStatsDto {
  occupancy_rate: number;
  occupancy_trend: number | null;
  total_revenue_mtd: number;
  revenue_trend: number;
  pending_checkins: number;
  data_health_score: number | null;
}

export interface DashboardRevenuePointDto {
  period: string;
  revenue: number;
}

export interface DashboardArrivalDto {
  guest_name: string;
  initials: string;
  room_type: string;
  nights: number;
  arrival_time: string;
  status_tag: string;
}

export interface PropertiesDashboardResponseDto {
  quick_stats: DashboardQuickStatsDto;
  revenue_chart: DashboardRevenuePointDto[];
  arrivals_today: DashboardArrivalDto[];
  properties: PropertiesListResponseDto;
}

export interface EditPropertyResponseDto {
  hotel: {
    prop_id: number;
    display_name: string;
    hotel_name?: string | null;
    country_display_name: string;
    prop_starrating: number | null;
    review_score_label: string;
    prop_brand_bool?: boolean;
    prop_location_score1?: number | null;
    description?: string | null;
    manual_override?: boolean;
    name_source?: string;
    original_generated_name?: string | null;
    profile_badge?: string;
  };
  profile?: {
    prop_id: number;
    hotel_name: string;
    display_name: string;
    display_country_label: string;
    description: string;
    original_generated_name?: string | null;
    manual_override?: boolean;
    name_source?: string;
    profile_badge?: string;
    updated_by?: string | null;
    updated_at?: string | null;
  };
  content_page: {
    prop_id: number;
    description: string;
    highlights: string;
    amenities_text: string;
    source: string;
    updated_at: string | null;
  };
  policies: {
    check_in_time?: string;
    check_out_time?: string;
    cancellation_policy?: string;
    pet_policy?: string;
    children_policy?: string;
    extra_bed_policy?: string;
    payment_policy?: string;
    house_rules?: string;
  };
  images: Array<{
    prop_id: number;
    image_url: string;
    title: string;
    source: string;
    created_at_label?: string;
  }>;
  images_count: number;
  amenities: {
    active_amenities: string[];
    catalog: Array<{ category: string; items: Array<{ label: string; active: boolean }> }>;
  };
}

export interface ChangeRecordDto {
  id: string;
  field: string;
  old_value: string;
  new_value: string;
  changed_by: string;
  changed_at: string;
  source?: string;
  reason?: string;
}

export interface PropertyHistoryResponseDto {
  data: ChangeRecordDto[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
  filters: {
    fields: string[];
    users: string[];
  };
}

export interface ChangeDetailDto extends ChangeRecordDto {
  prop_id?: number;
  entity_type?: string;
}

export interface PropertyProfileResponseDto {
  hotel: {
    prop_id: number;
    display_name: string;
    hotel_name?: string | null;
    country_display_name?: string;
    manual_override?: boolean;
    name_source?: string;
    original_generated_name?: string | null;
    profile_badge?: string;
  };
  profile: {
    prop_id: number;
    display_name: string;
    hotel_name: string;
    description: string;
    display_country_label: string;
    manual_override?: boolean;
    name_source?: string;
    original_generated_name?: string | null;
    profile_badge?: string;
    updated_by?: string | null;
    updated_at?: string | null;
  };
}
