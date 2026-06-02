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
  booking_rate: number;
  promotions: number;
  promotion_rate: number;
  avg_price: number;
  gross_revenue: number;
  distinct_hotels: number;
  distinct_destinations: number;
  distinct_countries: number;
  rejected_records: number;
  completion_rate: number;
}

export interface DashboardKpiDto {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}
