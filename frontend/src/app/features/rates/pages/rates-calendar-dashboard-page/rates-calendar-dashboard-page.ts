import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { exportCsv } from '../../../../shared/utils/csv-export.util';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent, type KpiChartDataset } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { RatesApiService } from '../../services/rates-api.service';
import type { RateCalendarDashboard } from '../../models/rate-calendar.model';

@Component({
  selector: 'app-rates-calendar-dashboard-page',
  imports: [
    RouterLink,
    DecimalPipe,
    PropertySelectorComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
    HorizontalSubNavComponent,
  ],
  templateUrl: './rates-calendar-dashboard-page.html',
  styleUrl: './rates-calendar-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RatesCalendarDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly ratesApi = inject(RatesApiService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly auth = inject(AuthService);

  /** Descarga del informe gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly planFilter = computed(() => this.qp()?.get('plan_id') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  // ── Dashboard resource (Mongo — informe simple) ──
  readonly dashboardResource = rxResource<RateCalendarDashboard, unknown>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        planId: this.planFilter() || undefined,
        dateFrom: this.dateFrom() || undefined,
        dateTo: this.dateTo() || undefined,
      };
    },
    stream: ({ params }) => this.ratesApi.getRateCalendarDashboard({
      prop_id: (params as any).propId,
      page: (params as any).page,
      plan_id: (params as any).planId,
      date_from: (params as any).dateFrom,
      date_to: (params as any).dateTo,
    }),
  });

  readonly data = computed(() => this.dashboardResource.value() ?? null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly series = computed(() => this.data()?.series ?? { labels: [], datasets: [] });
  readonly rows = computed(() => this.data()?.rows ?? []);

  /**
   * Gráfico central mixto: la tarifa media como línea (eje Y izquierdo, moneda)
   * y los días cerrados como barras (eje Y derecho, conteo) para no aplastar
   * la escala. Se resuelve por etiqueta para no depender del orden del backend.
   */
  readonly chartDatasets = computed<KpiChartDataset[]>(() => {
    const ds = this.series().datasets;
    if (!ds.length) return [];
    // El backend garantiza el orden [Tarifa media, Días cerrados]; se detecta
    // por etiqueta y se cae al índice 0 si algún día se renombra.
    const rateIdx = ds.findIndex((d) => d.label.toLowerCase().includes('tarifa'));
    const fallbackRate = rateIdx === -1 ? 0 : rateIdx;
    return ds.map((d, i): KpiChartDataset => {
      const isAvg = i === fallbackRate;
      return {
        label: d.label,
        data: d.data,
        color: isAvg ? '#1463ff' : '#ef4444',
        type: isAvg ? 'line' : 'bar',
        axis: isAvg ? 'y' : 'y1',
        formatValue: isAvg ? 'currency' : 'number',
      };
    });
  });

  readonly byPlan = computed(() => this.data()?.byPlan ?? []);

  /** Nombre base del PNG del gráfico central (coherente con el CSV de la grilla). */
  readonly exportChartName = computed(() => {
    const propLabel = (this.selectedLabel() || `Propiedad #${this.selectedPropId()}`).replace(/\s+/g, '_');
    return `calendario-tarifas_${propLabel}_${this.dateFrom() || 'all'}_${this.dateTo() || 'all'}`.toLowerCase();
  });

  /** Porcentaje de días del rango que tienen al menos una entrada de tarifa. */
  readonly coveragePct = computed(() => {
    const s = this.summary();
    if (!s || !s.rangeDays) return 0;
    return Math.round((s.distinctDates / s.rangeDays) * 100);
  });

  /**
   * Puntos SVG (polyline) del sparkline del hero, derivados de la serie de
   * tarifa media. Decisión de diseño: los días sin tarifa (valor 0) se filtran
   * para no pintar caídas engañosas a $0 en la tendencia — el sparkline muestra
   * la evolución de los días con tarifa publicada. Devuelve '' si hay menos de
   * 2 puntos para que el sparkline se oculte.
   */
  readonly sparkPoints = computed(() => {
    const ds = this.series().datasets;
    const rate = ds.find((d) => d.label.toLowerCase().includes('tarifa'));
    const values = (rate?.data ?? []).filter((v) => v > 0);
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

  readonly planOptions = computed(() => {
    const seen = new Set<string>();
    const options: { planId: string; name: string }[] = [];
    for (const row of this.rows()) {
      if (!seen.has(row.ratePlanId)) {
        seen.add(row.ratePlanId);
        options.push({ planId: row.ratePlanId, name: row.planName });
      }
    }
    return options;
  });

  /** Preset activo según el rango de fechas de la URL (30/90 días). */
  readonly activeRange = computed<'30' | '90' | null>(() => {
    const from = this.dateFrom();
    const to = this.dateTo();
    if (!from || !to) return null;
    const start = new Date(`${from}T00:00:00`);
    const end = new Date(`${to}T00:00:00`);
    const diff = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
    return diff === 30 ? '30' : diff === 90 ? '90' : null;
  });

  readonly hasFilters = computed(() => Boolean(this.planFilter() || this.dateFrom() || this.dateTo()));

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

  togglePlanFilter(value: string): void {
    const next = value === this.planFilter() ? '' : value;
    this.navigate({ plan_id: next || null });
  }

  /** Quick period presets: 30, 90 días terminando hoy. */
  setRange(days: number): void {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    this.navigate({ date_from: fmt(start), date_to: fmt(end) });
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
      queryParams: { plan_id: null, date_from: null, date_to: null, page: null },
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

  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(`${val}T00:00:00`);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  /** Exporta la grilla actual (día × plan) a CSV con BOM UTF-8. */
  exportGridCsv(): void {
    const rows = this.rows();
    const propLabel = (this.selectedLabel() || `Propiedad #${this.selectedPropId()}`).replace(/\s+/g, '_');
    exportCsv(
      `calendario-tarifas_${propLabel}_${this.dateFrom() || 'all'}_${this.dateTo() || 'all'}`.toLowerCase(),
      ['Fecha', 'Plan', 'Tarifa', 'Est. mín.', 'Divisa', 'Estado'],
      rows.map((r) => [
        r.date,
        r.planName,
        r.rateAmount,
        r.minStayNights,
        r.currency,
        r.isClosed ? 'Cerrado' : 'Abierto',
      ]),
    );
  }
}
