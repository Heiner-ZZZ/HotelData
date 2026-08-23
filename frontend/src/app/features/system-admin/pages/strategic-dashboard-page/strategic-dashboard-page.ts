import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { filter } from 'rxjs';

import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';

import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { csvEscape } from '../../../../shared/utils/csv-export.util';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type {
  Quadrant,
  SeriesData,
  StrategicHotel,
  StrategicKpi,
  StrategicMarkets,
  StrategicPortfolio,
} from '../../models/strategic-dashboard.model';
import { CompetitiveMapComponent } from './components/competitive-map';
import { QUADRANT_META } from '../../models/strategic-dashboard.model';
import {
  mapStrategicHotel,
  mapStrategicMarkets,
  mapStrategicPortfolio,
} from '../../mappers/strategic-dashboard.mapper';

type Horizon = 'mensual' | 'trimestral' | 'semestral' | 'anual';

const HORIZONS: { id: Horizon; label: string; months: number }[] = [
  { id: 'mensual', label: 'Mensual', months: 1 },
  { id: 'trimestral', label: 'Trimestral', months: 3 },
  { id: 'semestral', label: 'Semestral', months: 6 },
  { id: 'anual', label: 'Anual', months: 12 },
];

/** Sección de un CSV multi-bloque (título + cabeceras + filas). */
interface CsvSection {
  title: string;
  headers: string[];
  rows: (string | number)[][];
}

@Component({
  selector: 'app-strategic-dashboard-page',
  imports: [
    DecimalPipe,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
    PropertySelectorComponent,
    HorizontalSubNavComponent,
    CompetitiveMapComponent,
  ],
  templateUrl: './strategic-dashboard-page.html',
  styleUrl: './strategic-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StrategicDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);

  readonly horizons = HORIZONS;
  readonly QUADRANT_META = QUADRANT_META;

  /** Exportación CSV de los informes estratégicos gateada por ``reports.download``
   * (mismo contrato que los dashboards tácticos: exportas lo que ya puedes leer). */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => {
    // Vista A: prop_id llega por query param (?prop_id=1) — lo inyecta el
    // property-context (single/multi) o el drill-down de cartera.
    const fromQuery = Number(this.qp()?.get('prop_id') ?? '0');
    return fromQuery;
  });
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly marketsPage = computed(() => Math.max(1, Number(this.qp()?.get('mpage') ?? '1')));
  readonly planesPage = computed(() => Math.max(1, Number(this.qp()?.get('ppage') ?? '1')));
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  /**
   * Vista B (cartera del sistema) SOLO en la ruta /informes-estrategicos
   * (botón SISTEMA, exclusiva de dirección); la ruta /management/informes-
   * estrategicos (botón GESTIÓN) renderiza SIEMPRE la Vista A del hotel,
   * incluso para dirección (drill-down de cartera). Decisión por ruta, no
   * por rol: así cada botón abre SU vista y el clic siempre re-navega.
   */
  private readonly currentUrl = signal(this.router.url);

  readonly isPortfolioView = computed(() => this.currentUrl().startsWith('/informes-estrategicos'));

  /** Informe activo del menú horizontal: último segmento de la ruta (g01..g05
   * en Vista B; h01/h02 en Vista A), con fallback al primero de cada vista.
   * Se deriva de ``currentUrl`` (signal reactiva a NavigationEnd) en vez del
   * paramMap para que también funcione al montar el componente fuera del
   * RouterOutlet (tests) y tras navegaciones SPA. */
  readonly report = computed(() => {
    const raw = this.currentUrl().split('?')[0].split('/').pop() ?? '';
    const valid = this.isPortfolioView()
      ? ['g01', 'g02', 'g03', 'g04', 'g05']
      : ['h01', 'h02'];
    return valid.includes(raw) ? raw : (this.isPortfolioView() ? 'g01' : 'h01');
  });

  /** Slug del informe activo para el horizontal-sub-nav (mismo árbol que el
   * sidebar: gestion.informes-estrategicos.h0x / sistema.informes-estrategicos.g0x). */
  readonly activeReportSlug = computed(() =>
    this.isPortfolioView()
      ? `sistema.informes-estrategicos.${this.report()}`
      : `gestion.informes-estrategicos.${this.report()}`);

  constructor() {
    // Mantiene la señal de URL al día para navegaciones SPA (ej. drill-down).
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => this.currentUrl.set(this.router.url));

    // Sincroniza selectedLabel con ?prop_label de la URL o con el label del
    // PropertyContext (para deep-links /management?prop_id=1 sin prop_label,
    // o navegación vía sidebar que solo inyecta prop_id). Así el header y el
    // export CSV muestran el nombre real (Hotel Lima Centro) en vez de Hotel #1.
    // También asegura que la URL final contenga prop_label para bookmark/share.
    effect(
      () => {
        const fromQuery = this.qp()?.get('prop_label');
        if (fromQuery) {
          if (this.selectedLabel() !== fromQuery) this.selectedLabel.set(fromQuery);
          return;
        }
        const pid = this.selectedPropId();
        if (!pid) return;
        const fromCtx =
          this.propCtx.currentPropLabel() ||
          this.propCtx.assignedProperties().find((p) => p.propId === pid)?.label ||
          '';
        if (fromCtx && this.selectedLabel() !== fromCtx) this.selectedLabel.set(fromCtx);
        // Si tenemos label pero la URL aún no lo tiene, inyectarlo para que el
        // bookmark refleje ...?prop_id=1&prop_label=Hotel%20Lima%20Centro
        if (fromCtx && !fromQuery && pid) {
          const currentLabelInUrl = this.qp()?.get('prop_label');
          if (!currentLabelInUrl) {
            // replaceUrl para no crear entrada extra en el historial
            void this.router.navigate([], {
              relativeTo: this.activatedRoute,
              queryParams: { prop_label: fromCtx },
              queryParamsHandling: 'merge',
              replaceUrl: true,
            });
          }
        }
      },
      { allowSignalWrites: true },
    );
  }

  readonly activeHorizon = computed<Horizon | null>(() => {
    const from = this.dateFrom();
    const to = this.dateTo();
    if (!from || !to) return null;
    return HORIZONS.find((h) => {
      const r = this.rangeFor(h.months);
      return r.from === from && r.to === to;
    })?.id ?? null;
  });

  private rangeFor(months: number): { from: string; to: string } {
    const end = new Date();
    const start = new Date(end.getFullYear(), end.getMonth() - (months - 1), 1);
    const pad = (n: number) => String(n).padStart(2, '0');
    return {
      from: `${start.getFullYear()}-${pad(start.getMonth() + 1)}-01`,
      to: end.toISOString().slice(0, 10),
    };
  }

  private buildUrl(endpoint: string): string | undefined {
    if (!this.isPortfolioView()) return undefined;
    const params = new URLSearchParams();
    if (this.dateFrom()) params.set('date_from', this.dateFrom());
    if (this.dateTo()) params.set('date_to', this.dateTo());
    if (this.selectedPropId()) params.set('prop_id', String(this.selectedPropId()));
    if (endpoint === 'portfolio') params.set('page', String(this.currentPage()));
    if (endpoint === 'markets') params.set('page', String(this.marketsPage()));
    params.set('page_size', '20');
    return `/api/strategic/${endpoint}?${params.toString()}`;
  }

  /** URL del dashboard de UN hotel (Vista A) — solo para no-dirección.
   * ``page`` pagina la tabla de registros mensuales; ``ppage`` los planes. */
  private buildHotelUrl(): string | undefined {
    if (this.isPortfolioView()) return undefined;
    const pid = this.selectedPropId();
    if (!pid) return undefined;
    const params = new URLSearchParams();
    if (this.dateFrom()) params.set('date_from', this.dateFrom());
    if (this.dateTo()) params.set('date_to', this.dateTo());
    params.set('page', String(this.currentPage()));
    params.set('ppage', String(this.planesPage()));
    params.set('page_size', '20');
    return `/api/strategic/hotel/${pid}?${params.toString()}`;
  }

  // ── Recursos (solo lectura ClickHouse) ──
  readonly portfolioResource = httpResource<StrategicPortfolio>(
    () => this.buildUrl('portfolio'),
    { parse: (dto) => mapStrategicPortfolio(dto as never) },
  );

  readonly marketsResource = httpResource<StrategicMarkets>(
    () => this.buildUrl('markets'),
    { parse: (dto) => mapStrategicMarkets(dto as never) },
  );

  readonly hotelResource = httpResource<StrategicHotel>(
    () => this.buildHotelUrl(),
    { parse: (dto) => mapStrategicHotel(dto as never) },
  );

  readonly portfolio = computed(() => this.portfolioResource.value() ?? null);
  readonly markets = computed(() => this.marketsResource.value() ?? null);
  readonly hotel = computed(() => this.hotelResource.value() ?? null);

  readonly viewState = computed<ViewState>(() => {
    if (this.isPortfolioView()) {
      if (this.portfolioResource.isLoading()) return 'loading';
      if (this.portfolioResource.error() && !this.portfolioResource.value()) return 'error';
      if (!this.portfolioResource.value()) return 'empty';
      return 'success';
    }
    if (this.hotelResource.isLoading()) return 'loading';
    if (this.hotelResource.error() && !this.hotelResource.value()) return 'error';
    if (!this.hotelResource.value()) return 'empty';
    return 'success';
  });

  readonly errorMessage = computed(() => {
    const err = this.isPortfolioView() ? this.portfolioResource.error() : this.hotelResource.error();
    return (err as { message?: string } | null)?.message ?? 'No se pudieron cargar los informes estratégicos.';
  });

  readonly unavailable = computed(() => {
    if (this.isPortfolioView()) return Boolean(this.portfolio() && !this.portfolio()!.available);
    return Boolean(this.hotel() && !this.hotel()!.available);
  });

  // ── Cabecera según vista (decidida por la ruta) ──
  readonly headerEyebrow = computed(() =>
    this.isPortfolioView() ? 'INFORMES ESTRATÉGICOS · VISTA B' : 'INFORMES ESTRATÉGICOS · VISTA A');
  readonly headerTitle = computed(() =>
    this.isPortfolioView() ? 'Control global de la cartera' : 'Cómo crecer este hotel');
  readonly headerDescription = computed(() =>
    this.isPortfolioView()
      ? 'KPIs de la cartera, mercados y rentabilidad por hotel. Datos mensuales desde ClickHouse (TAF14).'
      : 'Desempeño económico-comercial y posicionamiento de tu propiedad — IE-H01 / IE-H02 (TAF14).');

  /** KPIs estratégicos de la cartera (Vista B) — patrón Z: KPIs arriba,
   * derivados directamente de las tablas strat_* (sin BSC). */
  readonly portfolioKpis = computed(() => this.portfolio()?.summary.kpis ?? []);

  /** IE-G02 — rankings estratégicos (R-G01..R-G06, TAF14 §5). */
  readonly rankingsKpis = computed(() => this.portfolio()?.rankings.kpis ?? []);
  readonly rankingGroups = computed(() => this.portfolio()?.rankings.groups ?? []);
  readonly rankingsChartDatasets = computed(() => {
    const series = this.portfolio()?.rankings.series;
    if (!series) return [];
    return series.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      type: 'bar' as const,
      axis: 'y' as 'y' | 'y1',
      formatValue: (d.label.includes('Revenue') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });

  /** IE-H02 — posicionamiento como patrón Z (serie mensual rating/ADR). */
  readonly posicionamientoSerieDatasets = computed(() => {
    const serie = this.hotel()?.posicionamientoSerie;
    if (!serie) return [];
    return serie.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      type: 'line' as const,
      axis: 'y' as 'y' | 'y1',
      formatValue: (d.label.includes('ADR') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });
  readonly posicionamientoRows = computed(() => this.hotel()?.posicionamientoRows ?? []);

  // ── Mapa competitivo (IE-H02) ──
  readonly mapOpen = signal(false);

  /** Label del hotel propio para el marcador del mapa. */
  readonly ownHotelLabel = computed(
    () => this.selectedLabel() || `Hotel #${this.hotel()?.propId ?? ''}`,
  );

  toggleMap(): void {
    this.mapOpen.update((open) => !open);
  }

  /** El mapa solo tiene sentido con coordenadas propias (centro + radio). */
  hasMapCoords(pos: { ownLat: number | null; ownLng: number | null }): boolean {
    return pos.ownLat !== null && pos.ownLng !== null;
  }

  /** KPIs del bloque IE-H02 (patrón Z): rating, ADR y respuesta del último mes. */
  readonly posicionamientoKpis = computed(() => {
    const h = this.hotel();
    const pos = h?.summary.posicionamiento;
    if (!h || !pos) return [];
    const latest = h.posicionamientoRows[0];
    const trendOf = (v: number) => (v > 0.5 ? ('up' as const) : v < -0.5 ? ('down' as const) : ('flat' as const));
    const semaforoOf = (v: number, ok: boolean) => (ok ? ('green' as const) : ('yellow' as const));
    return [
      {
        id: 'pos_rating',
        label: 'Rating promedio',
        value: pos.rating,
        unit: '★',
        target: 4.2,
        pctChange: pos.ratingVariacion,
        trend: trendOf(pos.ratingVariacion),
        semaforo: semaforoOf(pos.ratingVariacion, pos.rating >= 4.2),
        detail: 'Reseñas aprobadas',
      },
      {
        id: 'pos_adr',
        label: 'ADR',
        value: pos.adr,
        unit: 'USD',
        target: null,
        pctChange: pos.adrVariacion,
        trend: trendOf(pos.adrVariacion),
        semaforo: semaforoOf(pos.adrVariacion, pos.adr > 0),
        detail: 'Tarifa media por noche',
      },
      ...(latest
        ? [{
            id: 'pos_respuesta',
            label: 'Respuesta a reseñas',
            value: latest.respuesta,
            unit: '%',
            target: 80,
            pctChange: 0,
            trend: 'flat' as const,
            semaforo: (latest.respuesta >= 80 ? 'green' : 'yellow') as 'green' | 'yellow',
            detail: 'Último mes',
          }]
        : []),
      ...(pos.competitors > 0
        ? [
            {
              id: 'pos_competidores',
              label: 'Competidores',
              value: pos.competitors,
              unit: 'hoteles',
              target: null,
              pctChange: 0,
              trend: 'flat' as const,
              semaforo: 'yellow' as const,
              detail: pos.city ? `Misma ciudad: ${pos.city}` : 'Misma ciudad',
            },
            {
              id: 'pos_banda_p50',
              label: 'Banda mediana',
              value: pos.bandaPrecio?.p50 ?? 0,
              unit: 'USD',
              target: null,
              pctChange: 0,
              trend: 'flat' as const,
              semaforo: 'yellow' as const,
              detail: pos.bandaPrecio
                ? `P25 ${pos.bandaPrecio.p25} · P75 ${pos.bandaPrecio.p75}`
                : 'Sin banda',
            },
            {
              id: 'pos_percentil_adr',
              label: 'Percentil ADR',
              value: pos.adrPercentile ?? 0,
              unit: '%',
              target: null,
              pctChange: 0,
              trend: trendOf(pos.adrPercentile ?? 0),
              semaforo: 'yellow' as const,
              detail: 'Posición frente a la competencia',
            },
            {
              id: 'pos_precio_relativo',
              label: 'Precio vs mediana',
              value: pos.precioRelativoPct ?? 0,
              unit: '%',
              target: null,
              pctChange: pos.precioRelativoPct ?? 0,
              trend: trendOf(pos.precioRelativoPct ?? 0),
              semaforo: 'yellow' as const,
              detail: 'Sobre la mediana de la ciudad',
            },
          ]
        : []),
    ];
  });

  // ── Charts Vista A ──
  readonly hotelSerieDatasets = computed(() => {
    const serie = this.hotel()?.serie;
    if (!serie) return [];
    return serie.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      type: 'line' as const,
      axis: (d.label.includes('Ocupación') ? 'y1' : 'y') as 'y' | 'y1',
      formatValue: (d.label.includes('Revenue') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });

  readonly hotelPlanesLabels = computed(() => (this.hotel()?.planes.rows ?? []).map((p) => p.label));
  readonly hotelPlanesData = computed(() => (this.hotel()?.planes.rows ?? []).map((p) => p.revenueNeto));

  // ── Charts ──
  readonly carteraChartDatasets = computed(() => {
    const series = this.portfolio()?.series;
    if (!series) return [];
    return series.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      type: 'line' as const,
      axis: (d.label.includes('Ocupación') ? 'y1' : 'y') as 'y' | 'y1',
      formatValue: (d.label.includes('Revenue') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });

  readonly planesChartDatasets = computed(() => {
    const planes = this.portfolio()?.planes.rows ?? [];
    return planes.map((p) => p.revenueNeto);
  });

  readonly planesChartLabels = computed(() => (this.portfolio()?.planes.rows ?? []).map((p) => p.label));

  readonly marketsChartDatasets = computed(() => {
    const series = this.markets()?.series;
    if (!series) return [];
    return series.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      type: 'line' as const,
      axis: 'y' as 'y' | 'y1',
      formatValue: (d.label.includes('Revenue') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });

  // ── Navegación / filtros ──
  private navigate(params: Record<string, string | null>): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: params,
      queryParamsHandling: 'merge',
    });
  }

  setHorizon(id: Horizon): void {
    const h = HORIZONS.find((x) => x.id === id)!;
    const r = this.rangeFor(h.months);
    this.navigate({ date_from: r.from, date_to: r.to, page: null, mpage: null, ppage: null });
  }

  onDateFromChange(value: string): void {
    this.navigate({ date_from: value || null, page: null, mpage: null, ppage: null });
  }

  onDateToChange(value: string): void {
    this.navigate({ date_to: value || null, page: null, mpage: null, ppage: null });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    this.navigate({ prop_id: event.propId ? String(event.propId) : null, prop_label: label || null, page: null, mpage: null, ppage: null });
  }

  /** Drill-down de cartera → Vista A del hotel: navega a la ruta GESTIÓN
   * ``/management/informes-estrategicos/h01?prop_id=X`` (primer informe IE-H01)
   * conservando fechas. Así el clic en un hotel de IE-G03 abre la vista
   * individual (no la cartera). */
  goToHotel(propId: number, label?: string): void {
    void this.router.navigate(['/management/informes-estrategicos', 'h01'], {
      queryParams: { prop_id: String(propId), prop_label: label ?? null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number): void {
    this.navigate({ page: page > 1 ? String(page) : null });
  }

  goToMarketsPage(page: number): void {
    this.navigate({ mpage: page > 1 ? String(page) : null });
  }

  goToPlanesPage(page: number): void {
    this.navigate({ ppage: page > 1 ? String(page) : null });
  }

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { date_from: null, date_to: null, prop_id: null, prop_label: null, page: null, mpage: null, ppage: null },
      queryParamsHandling: 'merge',
    });
  }

  onRetry(): void {
    this.portfolioResource.reload();
    this.marketsResource.reload();
    this.hotelResource.reload();
  }

  // ── Exportación CSV por informe (gateada por reports.download) ──────────
  // Patrón de los tácticos compuestos: exportas lo que ya puedes leer. El
  // botón descarga SOLO el informe activo del menú horizontal (h01/h02,
  // g01..g05); los PNG se exportan por gráfico (app-kpi-chart showExport).

  /** Etiqueta del informe activo (título/filename de la exportación). */
  readonly reportExportLabel = computed<string>(() => {
    const labels: Record<string, string> = {
      h01: 'IE-H01 · Desempeño y planes',
      h02: 'IE-H02 · Posicionamiento local',
      g01: 'IE-G01 · KPIs de cartera',
      g02: 'IE-G02 · Rankings estratégicos',
      g03: 'IE-G03 · Rentabilidad de la cartera',
      g04: 'IE-G04 · Mapa de mercados',
      g05: 'IE-G05 · Forecasting',
    };
    return labels[this.report()] ?? 'Informe estratégico';
  });

  /** Deshabilita el CSV cuando el informe activo no tiene datos exportables.
   * IE-G05 es placeholder (TAF14 §9: diseño definido, modelos pendientes). */
  readonly exportDisabled = computed<boolean>(() => {
    if (!this.canExport()) return true;
    const h = this.hotel();
    const p = this.portfolio();
    const m = this.markets();
    switch (this.report()) {
      case 'h01': return !(h && h.summary.kpis.length > 0);
      case 'h02': return !(h && h.posicionamientoRows.length > 0);
      case 'g01': return !(p && p.summary.kpis.length > 0);
      case 'g02': return !(p && p.rankings.groups.length > 0);
      case 'g03': return !(p && p.rows.rows.length > 0);
      case 'g04': return !(m && m.rows.rows.length > 0);
      default: return true; // g05 placeholder
    }
  });

  /** Despacha la exportación según el informe activo del menú horizontal. */
  exportCsv(): void {
    switch (this.report()) {
      case 'h01': this.exportH01Csv(); break;
      case 'h02': this.exportH02Csv(); break;
      case 'g01': this.exportG01Csv(); break;
      case 'g02': this.exportG02Csv(); break;
      case 'g03': this.exportG03Csv(); break;
      case 'g04': this.exportG04Csv(); break;
      default: break; // g05 placeholder: sin datos que exportar
    }
  }

  /** Concatena secciones (título + cabeceras + filas) en un solo CSV con BOM. */
  private downloadSectionsCsv(filename: string, sections: CsvSection[]): void {
    const lines: string[] = [];
    for (const section of sections) {
      lines.push(section.title);
      lines.push(section.headers.map((h) => csvEscape(h)).join(','));
      for (const row of section.rows) {
        lines.push(row.map((cell) => csvEscape(cell)).join(','));
      }
      lines.push('');
    }
    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /** Sección KPI (misma forma en todos los informes: cajas → filas CSV). */
  private kpiSection(title: string, kpis: StrategicKpi[]): CsvSection {
    return {
      title,
      headers: ['Indicador', 'Valor', 'Unidad', 'Variación', 'Estado', 'Detalle'],
      rows: kpis.map((k) => [k.label, k.value, k.unit, `${k.pctChange}%`, k.semaforo.toUpperCase(), k.detail]),
    };
  }

  /** Sección de serie mensual (labels × datasets), si hay datos. */
  private seriesSection(title: string, s: SeriesData | null): CsvSection | null {
    if (!s || !s.labels.length || !s.datasets.length) return null;
    return {
      title,
      headers: ['Mes', ...s.datasets.map((d) => d.label)],
      rows: s.labels.map((label, i) => [label, ...s.datasets.map((d) => d.data[i] ?? 0)]),
    };
  }

  /** IE-H01 · Desempeño económico-comercial y rentabilidad por plan. */
  private exportH01Csv(): void {
    const h = this.hotel();
    if (!h) return;
    const date = new Date().toISOString().slice(0, 10);
    const name = this.selectedLabel() || `Hotel #${h.propId}`;
    const sections: CsvSection[] = [
      this.kpiSection(`IE-H01 · KPIs del hotel — ${name} (${this.formatDate(h.dateFrom)} → ${this.formatDate(h.dateTo)})`, h.summary.kpis),
    ];
    if (h.rows.rows.length) {
      sections.push({
        title: 'Registros mensuales del hotel (IE-H01)',
        headers: ['Mes', 'Reservas', 'Noches', 'Revenue bruto', 'Descuento', 'Revenue neto', 'ADR', 'Ocupación', 'RevPAR', 'Cancelación'],
        rows: h.rows.rows.map((r) => [
          r.month, r.bookings, r.roomNights, r.revenueBruto, r.descuento, r.revenueNeto, r.adr, `${r.ocupacionPct}%`, r.revpar, `${r.cancelacionPct}%`,
        ]),
      });
    }
    if (h.planes.rows.length) {
      sections.push({
        title: 'Rentabilidad por plan (IE-H01)',
        headers: ['Tipo', 'Reservas', 'Noches', 'Revenue bruto', 'Descuento', 'Revenue neto', 'ADR'],
        rows: h.planes.rows.map((p) => [p.label, p.bookings, p.roomNights, p.revenueBruto, p.descuento, p.revenueNeto, p.adr]),
      });
    }
    this.downloadSectionsCsv(`informe-estrategico-h01-hotel-${h.propId}-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  /** IE-H02 · Posicionamiento competitivo local (~5 km). */
  private exportH02Csv(): void {
    const h = this.hotel();
    if (!h) return;
    const date = new Date().toISOString().slice(0, 10);
    const name = this.selectedLabel() || `Hotel #${h.propId}`;
    const pos = h.summary.posicionamiento;
    const sections: CsvSection[] = [
      this.kpiSection(`IE-H02 · Posicionamiento — ${name} (${this.formatDate(h.dateFrom)} → ${this.formatDate(h.dateTo)})`, this.posicionamientoKpis()),
    ];
    if (pos?.diagnosis) {
      sections.push({
        title: 'Diagnóstico (IE-H02)',
        headers: ['Diagnóstico', 'Decisión recomendada'],
        rows: [[pos.diagnosis, pos.decision]],
      });
    }
    if (h.posicionamientoRows.length) {
      sections.push({
        title: 'Registros de posicionamiento (IE-H02)',
        headers: ['Mes', 'Rating', 'ADR (USD)', 'Respuesta a reseñas %'],
        rows: h.posicionamientoRows.map((r) => [r.month, r.rating, r.adr, `${r.respuesta}%`]),
      });
    }
    this.downloadSectionsCsv(`informe-estrategico-h02-posicionamiento-${h.propId}-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  /** IE-G01 · KPIs estratégicos de la cartera + serie mensual. */
  private exportG01Csv(): void {
    const p = this.portfolio();
    if (!p) return;
    const date = new Date().toISOString().slice(0, 10);
    const sections: CsvSection[] = [
      this.kpiSection(`IE-G01 · KPIs de la cartera (${this.formatDate(p.dateFrom)} → ${this.formatDate(p.dateTo)})`, p.summary.kpis),
    ];
    const serie = this.seriesSection('Evolución mensual de la cartera (IE-G01)', p.series);
    if (serie) sections.push(serie);
    this.downloadSectionsCsv(`informe-estrategico-g01-kpis-cartera-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  /** IE-G02 · Rankings estratégicos R-G01..R-G06. */
  private exportG02Csv(): void {
    const p = this.portfolio();
    if (!p) return;
    const date = new Date().toISOString().slice(0, 10);
    const sections: CsvSection[] = [
      this.kpiSection(`IE-G02 · Rankings — KPIs (${this.formatDate(p.dateFrom)} → ${this.formatDate(p.dateTo)})`, p.rankings.kpis),
    ];
    for (const g of p.rankings.groups) {
      sections.push({
        title: `${g.codigo} · ${g.titulo} — ${g.criterio}`,
        headers: ['Entidad', 'Valor', 'Unidad', 'Variación', 'Motivo', 'Decisión'],
        rows: g.rows.map((r) => [r.entidad, r.valor, r.unidad, `${r.variacion}%`, r.motivo, r.decision]),
      });
    }
    this.downloadSectionsCsv(`informe-estrategico-g02-rankings-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  /** IE-G03 · Rentabilidad y composición de la cartera (por hotel + por plan). */
  private exportG03Csv(): void {
    const p = this.portfolio();
    if (!p) return;
    const date = new Date().toISOString().slice(0, 10);
    const sections: CsvSection[] = [];
    if (p.rows.rows.length) {
      sections.push({
        title: `Rentabilidad por hotel (IE-G03) — ${this.formatDate(p.dateFrom)} → ${this.formatDate(p.dateTo)}`,
        headers: ['Hotel', 'Reservas', 'Noches', 'Revenue bruto', 'Descuento', 'Revenue neto', 'ADR', 'Ocupación', 'RevPAR', 'Var.'],
        rows: p.rows.rows.map((r) => [
          r.hotelLabel, r.bookings, r.roomNights, r.revenueBruto, r.descuento, r.revenueNeto, r.adr, `${r.ocupacionPct}%`, r.revpar, `${r.variacion}%`,
        ]),
      });
    }
    if (p.planes.rows.length) {
      sections.push({
        title: 'Rentabilidad por plan (IE-G03)',
        headers: ['Tipo', 'Reservas', 'Noches', 'Revenue bruto', 'Descuento', 'Revenue neto', 'ADR'],
        rows: p.planes.rows.map((r) => [r.label, r.bookings, r.roomNights, r.revenueBruto, r.descuento, r.revenueNeto, r.adr]),
      });
    }
    this.downloadSectionsCsv(`informe-estrategico-g03-rentabilidad-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  /** IE-G04 · Mapa de mercados y destinos. */
  private exportG04Csv(): void {
    const m = this.markets();
    if (!m) return;
    const date = new Date().toISOString().slice(0, 10);
    const sections: CsvSection[] = [
      this.kpiSection(`IE-G04 · Mercados — KPIs (${this.formatDate(m.dateFrom)} → ${this.formatDate(m.dateTo)})`, m.summary.kpis),
    ];
    if (m.rows.rows.length) {
      sections.push({
        title: 'Mapa de mercados (IE-G04)',
        headers: ['Destino', 'Búsquedas', 'Clics', 'Reservas', 'Conversión %', 'Crecimiento %', 'Posición %', 'Revenue', 'Cuadrante', 'Decisión'],
        rows: m.rows.rows.map((r) => [
          r.destination, r.searches, r.clicks, r.reservations, `${r.conversionPct}%`, `${r.growthPct}%`, `${r.positionPct}%`, r.revenue, r.quadrant, r.decision,
        ]),
      });
    }
    this.downloadSectionsCsv(`informe-estrategico-g04-mercados-${date}`, sections);
    this.toast.show(`Informe ${this.reportExportLabel()} exportado como CSV.`, 'info', 4000);
  }

  // ── Formato ──
  formatMonth(val: string): string {
    if (!val) return '—';
    const d = new Date(`${val}T00:00:00`);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { month: 'short', year: 'numeric' });
  }

  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(`${val}T00:00:00`);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  pct(v: number): string {
    return `${v.toFixed(1)}%`;
  }

  money(v: number): string {
    return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  num(v: number): string {
    return v.toLocaleString('en-US');
  }

  semaforoClass(s: string): string {
    return `semaforo-${s}`;
  }

  quadrantClass(q: Quadrant): string {
    return `quadrant-${q}`;
  }
}
