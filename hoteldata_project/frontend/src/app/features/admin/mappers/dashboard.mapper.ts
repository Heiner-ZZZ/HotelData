import { formatCurrency } from '../../../shared/utils/currency-format.util';
import type { DashboardApiResponseDto } from '../models/dashboard.dto';
import type { DashboardViewModel } from '../models/dashboard.model';

/** Map backend icon names to Material Symbols icon names. */
function mapIcon(icon: string): string {
  const iconMap: Record<string, string> = {
    'icon-records': 'database',
    'icon-booking': 'calendar_month',
    'icon-revenue': 'attach_money',
    'icon-quality': 'verified',
    'icon-alert': 'warning',
  };
  return iconMap[icon] || icon;
}

export function mapDashboardResponse(dto: DashboardApiResponseDto): DashboardViewModel {
  const overview = dto.overview;
  const headline = overview.headline;
  const quality = overview.latest_quality;

  const collectionCounts: Array<{ label: string; value: number }> = [
    { label: 'Hoteles distintos', value: headline.distinct_hotels },
    { label: 'Destinos distintos', value: headline.distinct_destinations },
    { label: 'Paises distintos', value: headline.distinct_countries },
    { label: 'Eventos totales', value: headline.total_events },
  ];

  return {
    kpis: overview.kpis.map((kpi) => ({
      label: kpi.label,
      value: kpi.value,
      detail: kpi.detail,
      trend: kpi.trend,
      direction: kpi.direction,
      icon: mapIcon(kpi.icon)
    })),
    latestExecution: overview.latest_execution
      ? {
          executionId: overview.latest_execution.execution_id || 'Sin ejecucion',
          status: overview.latest_execution.status || 'unknown',
          executedAt: overview.latest_execution.executed_at || 'N/D'
        }
      : null,
    collectionCounts,
    qualitySummary: [
      { label: 'Total registros', value: String(quality?.source_rows ?? headline.total_events) },
      { label: 'Aceptados', value: String(quality?.valid_records ?? 0) },
      { label: 'Rechazados', value: String(quality?.rejected_records ?? headline.rejected_records) },
      {
        label: 'Completitud',
        value: `${Math.round((quality?.completeness_score ?? headline.completion_rate / 100) * 100)}%`
      }
    ],
    occupancySummary: [
      { label: 'Eventos', value: String(headline.total_events), icon: 'bar_chart' },
      { label: 'Reservas', value: String(headline.bookings), icon: 'calendar_month' },
      { label: 'Conversion', value: `${headline.booking_rate}%`, icon: 'trending_up' },
      {
        label: 'Precio medio',
        value: formatCurrency(headline.avg_price || 0),
        icon: 'attach_money'
      }
    ]
  };
}
