import { formatCurrency } from '../../../shared/utils/currency-format.util';
import type { ManagementReportsDto } from '../models/management-reports.dto';
import type { ManagementReportsViewModel } from '../models/management-reports.model';

export function mapManagementReports(dto: ManagementReportsDto): ManagementReportsViewModel {
  return {
    sourceCollection: dto.source_collection,
    totalEvents: dto.total_events,
    reservationsDetected: dto.reservations_detected,
    grossRevenueLabel: formatCurrency(dto.gross_revenue || 0),
    series: dto.series,
    rows: (dto.rows ?? []).map((row) => ({
      month: row.month,
      events: row.events,
      reservations: row.reservations,
      grossRevenue: row.gross_revenue,
      grossRevenueLabel: formatCurrency(row.gross_revenue || 0)
    })),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 10,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
    topHotels: dto.top_hotels_by_revenue.map((item) => ({
      propId: item.prop_id,
      displayName: item.display_name,
      profileBadge: item.profile_badge || (item.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
      grossRevenueLabel: formatCurrency(item.gross_revenue || 0),
      events: item.events
    })),
    topDestinations: dto.top_destinations.map((item) => ({
      label: item.label,
      events: item.events,
      grossRevenueLabel: formatCurrency(item.gross_revenue || 0)
    })),
    topVisitorCountries: dto.top_visitor_countries.map((item) => ({
      label: item.label,
      events: item.events,
      reservations: item.reservations
    })),
    operationalCounts: dto.operational_counts
  };
}
