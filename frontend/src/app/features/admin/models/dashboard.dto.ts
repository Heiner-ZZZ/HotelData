export interface DashboardOverviewDto {
  headline: DashboardHeadlineDto;
  kpis: DashboardKpiDto[];
  latest_execution: {
    execution_id?: string;
    status?: string;
    executed_at?: string;
  } | null;
  latest_quality: {
    levels: {
      valid: number;
      rejected: number;
      source_rows: number;
    };
    completeness_score: number;
    completion_rate: number;
    source_rows: number;
    valid_records: number;
    rejected_records: number;
  } | null;
}

export interface DashboardApiResponseDto {
  counts: Record<string, number>;
  quality: Record<string, unknown>;
  overview: DashboardOverviewDto;
}

export interface DashboardHeadlineDto {
  total_events: number;
  bookings: number;
  total_reservations?: number;
  total_clicks?: number;
  booking_rate: number;
  conversion_rate?: number;
  click_rate?: number;
  promotions: number;
  promotion_rate: number;
  avg_price: number;
  gross_revenue: number;
  distinct_hotels: number;
  distinct_destinations: number;
  distinct_countries: number;
  rejected_records: number;
  completion_rate: number;
  configured_room_types?: number;
  physical_rooms?: number;
  inventory_days?: number;
  rate_plans?: number;
  rate_calendar?: number;
  configured_policies?: number;
  content_pages?: number;
  images?: number;
  campaigns?: number;
  coupons?: number;
}

export interface DashboardKpiDto {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}

export interface DashboardKpisResponseDto {
  cached_at: string;
  payload: DashboardApiResponseDto;
}
