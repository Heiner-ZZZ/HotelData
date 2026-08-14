import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DecimalPipe, DatePipe } from '@angular/common';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { exportCsv } from '../../../../shared/utils/csv-export.util';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { InStayApiService } from '../../services/in-stay-api.service';
import type { ServiceRequestsAnalytics } from '../../models/service-requests-analytics.model';

const REQUEST_TYPE_LABELS: Record<string, string> = {
  housekeeping: 'Limpieza',
  towels: 'Toallas',
  amenities: 'Amenities',
  maintenance: 'Mantenimiento',
  room_service: 'Room service',
  minibar: 'Minibar',
  laundry: 'Lavandería',
  wake_up_call: 'Despertador',
  late_checkout: 'Late checkout',
  extra_bed: 'Cama extra',
  spa: 'Spa',
  restaurant: 'Restaurante',
  extend_stay: 'Extender estancia',
  early_checkout: 'Salida anticipada',
  other: 'Otro',
};

@Component({
  selector: 'app-service-requests-dashboard-page',
  imports: [
    RouterLink,
    DecimalPipe,
    DatePipe,
    PropertySelectorComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
    HorizontalSubNavComponent,
  ],
  templateUrl: './service-requests-dashboard-page.html',
  styleUrl: './service-requests-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServiceRequestsDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly instayApi = inject(InStayApiService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly auth = inject(AuthService);

  /** Descarga del informe gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly typeFilter = computed(() => this.qp()?.get('request_type') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  // ── Dashboard resource (Mongo — informe simple) ──
  readonly dashboardResource = rxResource<ServiceRequestsAnalytics, unknown>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        status: this.statusFilter() || undefined,
        requestType: this.typeFilter() || undefined,
        dateFrom: this.dateFrom() || undefined,
        dateTo: this.dateTo() || undefined,
      };
    },
    stream: ({ params }) => this.instayApi.getRequestsAnalytics({
      prop_id: (params as any).propId,
      page: (params as any).page,
      status: (params as any).status,
      request_type: (params as any).requestType,
      date_from: (params as any).dateFrom,
      date_to: (params as any).dateTo,
    }),
  });

  readonly data = computed(() => this.dashboardResource.value() ?? null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly series = computed(() => this.data()?.series ?? { labels: [], keys: [], datasets: [], dailyLabels: [], dailyStatuses: [] });
  readonly rows = computed(() => this.data()?.rows ?? []);

  /** Gráfico central: volumen por tipo de solicitud (bar). */
  readonly chartDatasets = computed(() => {
    const ds = this.series().datasets;
    return ds.length ? [{ label: ds[0].label, data: ds[0].data, color: '#1463ff' }] : [];
  });

  /** Tendencia diaria por estado (line). */
  readonly dailyDatasets = computed(() => {
    const colors = ['#f59e0b', '#3b82f6', '#22c55e', '#ef4444'];
    return this.series().dailyStatuses.map((s, i) => ({
      label: s.label,
      data: s.data,
      color: colors[i % colors.length],
    }));
  });

  /** Opciones de tipo: clave cruda como valor + etiqueta como texto. */
  readonly typeOptions = computed(() => {
    const labels = this.series().labels ?? [];
    const keys = this.series().keys ?? [];
    if (keys.length) {
      return keys.map((key, i) => ({ key, label: labels[i] ?? this.typeLabel(key) }));
    }
    if (labels.length) {
      // Fallback: series sin keys (backend antiguo) — intenta mapear por label.
      return labels.map((label) => {
        const entry = Object.entries(REQUEST_TYPE_LABELS).find(([, l]) => l === label);
        return { key: entry?.[0] ?? label, label };
      });
    }
    return Object.keys(REQUEST_TYPE_LABELS).map((key) => ({ key, label: REQUEST_TYPE_LABELS[key] }));
  });

  readonly statusOptions = [
    { value: 'pending', label: 'Pendiente' },
    { value: 'in_progress', label: 'En proceso' },
    { value: 'completed', label: 'Completado' },
    { value: 'cancelled', label: 'Cancelado' },
  ];

  readonly hasFilters = computed(() => Boolean(this.statusFilter() || this.typeFilter() || this.dateFrom() || this.dateTo()));

  readonly viewState = computed<ViewState>(() => {
    const r = this.dashboardResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()) return 'empty';
    return 'success';
  });

  // ── Helpers ──

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  private navigate(params: Record<string, string | null>): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: null, ...params },
      queryParamsHandling: 'merge',
    });
  }

  toggleStatus(value: string): void {
    const next = value === this.statusFilter() ? '' : value;
    this.navigate({ status: next || null });
  }

  toggleType(value: string): void {
    const next = value === this.typeFilter() ? '' : value;
    this.navigate({ request_type: next || null });
  }

  isTypeActive(key: string): boolean {
    return this.typeFilter() === key;
  }

  onDateFromChange(value: string): void {
    this.navigate({ date_from: value || null });
  }

  onDateToChange(value: string): void {
    this.navigate({ date_to: value || null });
  }

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: null, request_type: null, date_from: null, date_to: null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  typeLabel(type: string): string {
    return REQUEST_TYPE_LABELS[type] ?? type;
  }

  statusClass(status: string): string {
    return status || 'neutral';
  }

  formatDate(val: string): string {
    if (!val) return '—';
    return val.slice(0, 10);
  }

  /** Formatea fecha+hora igual que la grilla (dd/MM/yyyy HH:mm). */
  formatDateTime(val: string): string {
    if (!val) return '—';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val;
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${dd}/${mm}/${d.getFullYear()} ${hh}:${min}`;
  }

  /** Exporta la grilla actual de solicitudes a CSV con BOM UTF-8. */
  exportGridCsv(): void {
    const rows = this.rows();
    const propLabel = (this.selectedLabel() || `Propiedad #${this.selectedPropId()}`).replace(/\s+/g, '_');
    exportCsv(
      `solicitudes-servicio_${propLabel}_${this.dateFrom() || 'all'}_${this.dateTo() || 'all'}`.toLowerCase(),
      ['Fecha', 'Habitación', 'Tipo', 'Estado', 'Descripción', 'Resuelta'],
      rows.map((r) => [
        this.formatDateTime(r.createdAt),
        r.roomLabel,
        r.requestTypeLabel || this.typeLabel(r.requestType),
        r.statusLabel || r.status,
        r.description,
        r.resolvedAt ? this.formatDateTime(r.resolvedAt) : '',
      ]),
    );
  }
}
