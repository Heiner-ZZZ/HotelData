/** Fila del calendario de tarifas R2.2 (día × plan tarifario). */
export interface RateCalendarRowDto {
  date: string;
  prop_id: number;
  rate_plan_id: string;
  plan_name: string;
  rate_amount: number;
  min_stay_nights: number;
  is_closed: boolean;
  currency: string;
}

/** Desglose por plan del calendario R2.2. */
export interface RateCalendarByPlanDto {
  rate_plan_id: string;
  plan_name: string;
  entries: number;
  closed: number;
  open: number;
  min_rate: number;
  max_rate: number;
  avg_rate: number;
  currency: string;
}

/** Respuesta de GET /api/management/rates/analytics/rate-calendar — R2.2 dashboard. */
export interface RateCalendarDashboardDto {
  available: boolean;
  source: string;
  date_from: string;
  date_to: string;
  prop_id: number | null;
  summary: {
    total_entries: number;
    plans: number;
    active_plans: number;
    avg_rate: number;
    min_rate: number;
    max_rate: number;
    closed_days: number;
    open_days: number;
    distinct_dates: number;
    gap_days: number;
    range_days: number;
    has_data: boolean;
  };
  by_plan: RateCalendarByPlanDto[];
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: RateCalendarRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  message?: string;
}
