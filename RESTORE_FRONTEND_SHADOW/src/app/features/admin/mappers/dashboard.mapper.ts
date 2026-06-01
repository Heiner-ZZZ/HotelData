import { formatCurrency } from '../../../shared/utils/currency-format.util';
import type { DashboardApiResponseDto } from '../models/dashboard.dto';
import type { DashboardViewModel } from '../models/dashboard.model';

export function mapDashboardResponse(dto: DashboardApiResponseDto): DashboardViewModel {
  const counts = Object.entries(dto.counts).map(([label, value]) => ({
    label,
    value
  }));

  return {
    kpis: dto.overview.kpis.map((kpi) => ({
      label: kpi.label,
      value: kpi.value,
      detail: kpi.detail,
      trend: kpi.trend,
      direction: kpi.direction
    })),
    latestExecution: dto.overview.latest_execution
      ? {
          executionId: dto.overview.latest_execution.execution_id || 'Sin ejecucion',
          status: dto.overview.latest_execution.status || 'unknown',
          executedAt: dto.overview.latest_execution.executed_at || 'N/D'
        }
      : null,
    collectionCounts: counts,
    qualitySummary: [
      { label: 'Total registros', value: String(dto.quality.total_records) },
      { label: 'Aceptados', value: String(dto.quality.accepted_records) },
      { label: 'Rechazados', value: String(dto.quality.rejected_records) },
      {
        label: 'Completitud',
        value: `${Math.round((dto.quality.completeness_score || 0) * 100)}%`
      }
    ],
    occupancySummary: [
      { label: 'Eventos', value: String(dto.overview.headline.total_events) },
      { label: 'Reservas', value: String(dto.overview.headline.bookings) },
      { label: 'Conversion', value: `${dto.overview.headline.booking_rate}%` },
      {
        label: 'Precio medio',
        value: formatCurrency(dto.overview.headline.avg_price || 0)
      }
    ]
  };
}
