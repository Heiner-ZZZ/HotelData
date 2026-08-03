import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { DecimalPipe } from '@angular/common';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { exportCsv } from '../../../../shared/utils/csv-export.util';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent, type KpiChartDataset } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService } from '../../services/housekeeping-api.service';
import type { RoomStatusAnalytics } from '../../models/room-status-analytics.model';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';

/** Mismo catálogo de estados que el ciclo housekeeping (schemas.py ROOM_STATUSES). */
const STATUS_DEFS: { value: string; label: string; icon: string }[] = [
  { value: 'vacant_dirty', label: 'Vacante Sucia', icon: 'report' },
  { value: 'vacant_clean', label: 'Vacante Limpia', icon: 'check_circle' },
  { value: 'occupied_clean', label: 'Ocupada Limpia', icon: 'bed' },
  { value: 'occupied_dirty', label: 'Ocupada Sucia', icon: 'bed' },
  { value: 'cleaning_in_progress', label: 'Limpieza en Progreso', icon: 'cleaning_services' },
  { value: 'cleaning_completed', label: 'Limpieza Completada', icon: 'cleaning_services' },
  { value: 'inspected', label: 'Inspeccionada', icon: 'fact_check' },
  { value: 'out_of_service', label: 'Fuera de Servicio', icon: 'block' },
  { value: 'out_of_order', label: 'Fuera de Orden', icon: 'dangerous' },
  { value: 'maintenance_requested', label: 'Mantenimiento Solicitado', icon: 'build' },
];

@Component({
  selector: 'app-room-status-dashboard-page',
  imports: [
    DecimalPipe,
    PropertySelectorComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
    HousekeepingSubNavComponent,
  ],
  templateUrl: './room-status-dashboard-page.html',
  styleUrl: './room-status-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomStatusDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');

  // ── Dashboard resource (Mongo — informe simple O1.2) ──
  readonly dashboardResource = rxResource<RoomStatusAnalytics, unknown>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        status: this.statusFilter() || undefined,
      };
    },
    stream: ({ params }) => this.api.getRoomStatusAnalytics(
      (params as any).propId,
      (params as any).status,
      (params as any).page,
    ),
  });

  readonly data = computed(() => this.dashboardResource.value() ?? null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly distribution = computed(() => this.data()?.distribution ?? []);
  readonly rows = computed(() => this.data()?.rows ?? []);

  readonly statusOptions = STATUS_DEFS;

  /** Catálogo de estados con su label/color desde el backend (con fallback local). */
  readonly statusLabels = computed<Record<string, string>>(() => {
    const backend = this.data()?.status_labels ?? {};
    return { ...Object.fromEntries(STATUS_DEFS.map((s) => [s.value, s.label])), ...backend };
  });

  readonly statusColors = computed<Record<string, string>>(() => this.data()?.status_colors ?? {});

  /** Gráfico central: distribución por estado (bar, colores por estado). */
  readonly chartDatasets = computed<KpiChartDataset[]>(() => {
    const dist = this.distribution();
    if (!dist.length) return [];
    return [{
      label: 'Habitaciones',
      data: dist.map((d) => d.count),
      color: dist[0]?.color ?? '#1463ff',
    }];
  });

  /** Sparkline del hero: tendencia de la distribución (ocupadas vs listas). */
  readonly sparkPoints = computed(() => {
    const s = this.summary();
    if (!s) return '';
    const values = [s.occupied, s.vacant, s.cleaning, s.inspected, s.maintenance, s.out_of_service].filter((v) => v > 0);
    if (values.length < 2) return '';
    const width = 120;
    const height = 30;
    const pad = 2;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    return values
      .map((v, i) => {
        const x = pad + (i / (values.length - 1)) * (width - pad * 2);
        const y = height - pad - ((v - min) / span) * (height - pad * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });

  readonly exportChartName = computed(() => {
    const propLabel = (this.selectedLabel() || `Propiedad #${this.selectedPropId()}`).replace(/\s+/g, '_');
    return `matriz-habitaciones_${propLabel}`.toLowerCase();
  });

  /** % de habitaciones listas para vender (vacante limpia + inspeccionada). */
  readonly readyPct = computed(() => {
    const s = this.summary();
    if (!s || !s.total) return 0;
    return Math.round(((s.clean_ready ?? 0) / s.total) * 100);
  });

  /** % de habitaciones con problema (mantenimiento + fuera de servicio/orden). */
  readonly blockedPct = computed(() => {
    const s = this.summary();
    if (!s || !s.total) return 0;
    return Math.round(((s.maintenance + s.out_of_service) / s.total) * 100);
  });

  readonly hasFilters = computed(() => Boolean(this.statusFilter()));

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

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: null, page: null },
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

  statusLabel(status: string): string {
    return this.statusLabels()[status] ?? status;
  }

  statusColor(status: string): string {
    return this.statusColors()[status] ?? '#6f797d';
  }

  statusIcon(status: string): string {
    return STATUS_DEFS.find((s) => s.value === status)?.icon ?? 'circle';
  }

  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  formatDateTime(val: string): string {
    if (!val) return '—';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' }) + ' ' +
      d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
  }

  /** Exporta la grilla actual de habitaciones a CSV con BOM UTF-8. */
  exportGridCsv(): void {
    const rows = this.rows();
    const propLabel = (this.selectedLabel() || `Propiedad #${this.selectedPropId()}`).replace(/\s+/g, '_');
    exportCsv(
      `matriz-habitaciones_${propLabel}_${this.statusFilter() || 'todas'}`.toLowerCase(),
      ['Habitación', 'Tipo', 'Estado', 'Piso', 'Nota', 'Actualizado'],
      rows.map((r) => [
        r.roomLabel,
        r.roomTypeId,
        this.statusLabel(r.status),
        r.floor ?? '',
        r.note,
        r.updatedAt ? this.formatDateTime(r.updatedAt) : this.formatDateTime(r.createdAt),
      ]),
    );
  }
}
