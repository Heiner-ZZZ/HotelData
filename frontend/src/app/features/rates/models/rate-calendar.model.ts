/** Fila del calendario de tarifas R2.2 (día × plan tarifario). */
export interface RateCalendarRow {
  date: string;
  propId: number;
  ratePlanId: string;
  planName: string;
  rateAmount: number;
  minStayNights: number;
  isClosed: boolean;
  currency: string;
}

/** Desglose por plan del calendario R2.2. */
export interface RateCalendarByPlan {
  ratePlanId: string;
  planName: string;
  entries: number;
  closed: number;
  open: number;
  minRate: number;
  maxRate: number;
  avgRate: number;
  currency: string;
}

/** View model de GET /api/management/rates/analytics/rate-calendar — R2.2 dashboard. */
export interface RateCalendarDashboard {
  available: boolean;
  source: string;
  dateFrom: string;
  dateTo: string;
  propId: number | null;
  summary: {
    totalEntries: number;
    plans: number;
    activePlans: number;
    avgRate: number;
    minRate: number;
    maxRate: number;
    closedDays: number;
    openDays: number;
    distinctDates: number;
    gapDays: number;
    rangeDays: number;
    hasData: boolean;
  };
  byPlan: RateCalendarByPlan[];
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: RateCalendarRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
  message?: string;
}
