import type { RateCalendarByPlan, RateCalendarDashboard, RateCalendarRow } from '../models/rate-calendar.model';
import type { RateCalendarByPlanDto, RateCalendarDashboardDto, RateCalendarRowDto } from '../models/rate-calendar.dto';

function mapRow(dto: RateCalendarRowDto): RateCalendarRow {
  return {
    date: dto.date,
    propId: dto.prop_id,
    ratePlanId: dto.rate_plan_id,
    planName: dto.plan_name,
    rateAmount: dto.rate_amount,
    minStayNights: dto.min_stay_nights,
    isClosed: dto.is_closed,
    currency: dto.currency,
  };
}

function mapByPlan(dto: RateCalendarByPlanDto): RateCalendarByPlan {
  return {
    ratePlanId: dto.rate_plan_id,
    planName: dto.plan_name,
    entries: dto.entries,
    closed: dto.closed,
    open: dto.open,
    minRate: dto.min_rate,
    maxRate: dto.max_rate,
    avgRate: dto.avg_rate,
    currency: dto.currency,
  };
}

export function mapRateCalendarDashboard(dto: RateCalendarDashboardDto): RateCalendarDashboard {
  return {
    available: dto.available,
    source: dto.source,
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    propId: dto.prop_id,
    summary: {
      totalEntries: dto.summary?.total_entries ?? 0,
      plans: dto.summary?.plans ?? 0,
      activePlans: dto.summary?.active_plans ?? 0,
      avgRate: dto.summary?.avg_rate ?? 0,
      minRate: dto.summary?.min_rate ?? 0,
      maxRate: dto.summary?.max_rate ?? 0,
      closedDays: dto.summary?.closed_days ?? 0,
      openDays: dto.summary?.open_days ?? 0,
      distinctDates: dto.summary?.distinct_dates ?? 0,
      gapDays: dto.summary?.gap_days ?? 0,
      rangeDays: dto.summary?.range_days ?? 1,
      hasData: dto.summary?.has_data ?? false,
    },
    byPlan: (dto.by_plan ?? []).map(mapByPlan),
    series: dto.series ?? { labels: [], datasets: [] },
    rows: (dto.rows ?? []).map(mapRow),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 20,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
    message: dto.message,
  };
}
