export interface DashboardApiResponseDto {
  counts: Record<string, number>;
  quality: {
    total_records: number;
    accepted_records: number;
    rejected_records: number;
    completeness_score: number;
  };
  overview: DashboardOverviewDto;
}

export interface DashboardOverviewDto {
  headline: {
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
  };
  kpis: DashboardKpiDto[];
  latest_execution: {
    execution_id?: string;
    status?: string;
    executed_at?: string;
  } | null;
}

export interface DashboardKpiDto {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}
